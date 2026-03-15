"""
Template Service - Business logic for overlay templates and template instances.

Handles template listing, instance creation (with config validation and asset
generation), instance updates, and instance deletion.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.database import Asset
from models.template import OverlayTemplate, TemplateInstance
from models.canvas import CanvasProject

logger = logging.getLogger(__name__)


class TemplateServiceError(Exception):
    """Base exception for template service errors."""
    pass


class TemplateNotFoundError(TemplateServiceError):
    """Raised when a requested template does not exist."""
    pass


class InstanceNotFoundError(TemplateServiceError):
    """Raised when a requested template instance does not exist."""
    pass


class ConfigValidationError(TemplateServiceError):
    """Raised when config_values fail schema validation."""
    pass


def _load_definition_meta(template: OverlayTemplate) -> dict:
    """Load the full definition.json metadata for a template by matching its name
    to a catalog folder. Returns the parsed definition or an empty dict if not found."""
    from pathlib import Path
    catalog_dir = Path(__file__).parent.parent / "templates" / "catalog"
    if not catalog_dir.exists():
        return {}

    for entry in catalog_dir.iterdir():
        if not entry.is_dir():
            continue
        defn_path = entry / "definition.json"
        if not defn_path.exists():
            continue
        try:
            with open(defn_path, "r") as f:
                data = json.load(f)
            if data.get("name") == template.name:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return {}


def _validate_config(config_values: dict, config_schema: dict) -> None:
    """Validate that config_values satisfies the config_schema.

    Checks that all required fields are present and non-empty.
    """
    fields = config_schema.get("fields", [])
    for field in fields:
        key = field.get("key")
        required = field.get("required", False)
        if required:
            value = config_values.get(key)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                raise ConfigValidationError(
                    f"Required field '{field.get('label', key)}' ({key}) is missing or empty"
                )


def _merge_config(config_values: dict, default_config: dict) -> dict:
    """Merge user-provided config_values with default_config.

    User values take precedence; any key in defaults not provided by the user
    gets the default value.
    """
    merged = dict(default_config)
    merged.update(config_values)
    return merged


def _build_api_url(api_url_template: str, config: dict) -> str:
    """Construct the final API URL by substituting config values into the template."""
    url = api_url_template
    for key, value in config.items():
        url = url.replace(f"{{{key}}}", str(value))
    return url


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_templates(db: Session, category: Optional[str] = None) -> list[OverlayTemplate]:
    """List all active overlay templates, optionally filtered by category."""
    query = db.query(OverlayTemplate).filter(OverlayTemplate.is_active == True)
    if category:
        query = query.filter(OverlayTemplate.category == category)
    return query.order_by(OverlayTemplate.category, OverlayTemplate.name).all()


def get_template(db: Session, template_id: int) -> OverlayTemplate:
    """Get a single overlay template by ID."""
    template = db.query(OverlayTemplate).filter(
        OverlayTemplate.id == template_id,
        OverlayTemplate.is_active == True,
    ).first()
    if not template:
        raise TemplateNotFoundError(f"Template {template_id} not found")
    return template


def instantiate_template(
    db: Session,
    template_id: int,
    config_values: dict,
    user_id: Optional[int] = None,
    position_x: float = 0.0,
    position_y: float = 0.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    opacity: float = 1.0,
    name: Optional[str] = None,
) -> Asset:
    """Create a template instance and its associated asset.

    1. Loads the template and its catalog definition.
    2. Validates config_values against config_schema.
    3. Merges with default_config.
    4. Creates the appropriate asset type based on asset_type.
    5. Links everything via a TemplateInstance row.
    6. Returns the newly created Asset.
    """
    # 1. Load template
    template = get_template(db, template_id)
    config_schema = json.loads(template.config_schema)
    default_config = json.loads(template.default_config)

    # Load full definition metadata (for asset_type, api_url_template, etc.)
    defn = _load_definition_meta(template)
    asset_type = defn.get("asset_type", "static_image")

    # 2. Validate
    _validate_config(config_values, config_schema)

    # 3. Merge
    merged_config = _merge_config(config_values, default_config)

    # Determine asset name
    asset_name = name or template.name

    # 4. Create asset based on type
    asset = None
    canvas_project_id = None

    if asset_type == "api_image":
        api_url_template = defn.get("api_url_template", "")
        api_url = _build_api_url(api_url_template, merged_config)

        # Determine refresh interval from config or default
        refresh_interval = merged_config.get("refresh_interval", 60)
        if isinstance(refresh_interval, str):
            try:
                refresh_interval = int(refresh_interval)
            except ValueError:
                refresh_interval = 60

        asset = Asset(
            name=asset_name,
            type="api_image",
            api_url=api_url,
            api_refresh_interval=refresh_interval,
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height,
            opacity=opacity,
            description=f"Created from template: {template.name}",
            created_at=datetime.now(timezone.utc),
        )

    elif asset_type == "canvas_composite":
        default_canvas_json = defn.get("default_canvas_json", {"version": "6.0.0", "objects": []})

        # Create a canvas project from the template's default canvas JSON
        canvas_project = CanvasProject(
            name=asset_name,
            description=f"Created from template: {template.name}",
            canvas_json=json.dumps(default_canvas_json),
            width=1920,
            height=1080,
            user_id=user_id,
            is_active=True,
        )
        db.add(canvas_project)
        db.flush()  # Get the ID

        canvas_project_id = canvas_project.id

        asset = Asset(
            name=asset_name,
            type="canvas_composite",
            canvas_project_id=canvas_project.id,
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height,
            opacity=opacity,
            description=f"Created from template: {template.name}",
            created_at=datetime.now(timezone.utc),
        )

    elif asset_type == "static_image":
        asset = Asset(
            name=asset_name,
            type="static_image",
            position_x=position_x,
            position_y=position_y,
            width=width,
            height=height,
            opacity=opacity,
            description=f"Created from template: {template.name} (upload required)",
            created_at=datetime.now(timezone.utc),
        )

    else:
        raise TemplateServiceError(f"Unsupported asset_type: {asset_type}")

    db.add(asset)
    db.flush()  # Get the asset ID

    # 5. Create TemplateInstance linking template to asset
    instance = TemplateInstance(
        template_id=template.id,
        config_values=json.dumps(merged_config),
        asset_id=asset.id,
        user_id=user_id,
    )
    db.add(instance)
    db.flush()

    # Link the instance back to the asset
    asset.template_instance_id = instance.id

    db.commit()
    db.refresh(asset)

    logger.info(
        "Instantiated template %d (%s) -> asset %d, instance %d",
        template.id, template.name, asset.id, instance.id,
    )

    return asset


def update_instance(
    db: Session,
    instance_id: int,
    config_values: Optional[dict] = None,
    position_x: Optional[float] = None,
    position_y: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    opacity: Optional[float] = None,
) -> TemplateInstance:
    """Update a template instance's config and/or its asset's display properties.

    If config_values change and the asset is an api_image, the api_url is
    reconstructed from the template's api_url_template.
    """
    instance = db.query(TemplateInstance).filter(TemplateInstance.id == instance_id).first()
    if not instance:
        raise InstanceNotFoundError(f"Template instance {instance_id} not found")

    template = db.query(OverlayTemplate).filter(OverlayTemplate.id == instance.template_id).first()
    if not template:
        raise TemplateNotFoundError(f"Template {instance.template_id} not found")

    asset = db.query(Asset).filter(Asset.id == instance.asset_id).first() if instance.asset_id else None

    # Update config if provided
    if config_values is not None:
        config_schema = json.loads(template.config_schema)
        default_config = json.loads(template.default_config)

        _validate_config(config_values, config_schema)
        merged_config = _merge_config(config_values, default_config)
        instance.config_values = json.dumps(merged_config)

        # If the asset is api_image, reconstruct the URL
        if asset and asset.type == "api_image":
            defn = _load_definition_meta(template)
            api_url_template = defn.get("api_url_template", "")
            if api_url_template:
                asset.api_url = _build_api_url(api_url_template, merged_config)

            refresh_interval = merged_config.get("refresh_interval")
            if refresh_interval is not None:
                try:
                    asset.api_refresh_interval = int(refresh_interval)
                except (ValueError, TypeError):
                    pass

    # Update asset display properties
    if asset:
        if position_x is not None:
            asset.position_x = position_x
        if position_y is not None:
            asset.position_y = position_y
        if width is not None:
            asset.width = width
        if height is not None:
            asset.height = height
        if opacity is not None:
            asset.opacity = opacity
        asset.last_updated = datetime.now(timezone.utc)

    db.commit()
    db.refresh(instance)

    logger.info("Updated template instance %d", instance_id)
    return instance


def delete_instance(db: Session, instance_id: int) -> dict:
    """Soft-delete a template instance and deactivate its linked asset."""
    instance = db.query(TemplateInstance).filter(TemplateInstance.id == instance_id).first()
    if not instance:
        raise InstanceNotFoundError(f"Template instance {instance_id} not found")

    # Deactivate the linked asset
    if instance.asset_id:
        asset = db.query(Asset).filter(Asset.id == instance.asset_id).first()
        if asset:
            asset.is_active = False
            asset.last_updated = datetime.now(timezone.utc)

    # Remove the instance (hard delete since it's a linking table,
    # and the asset soft-delete preserves the audit trail)
    db.delete(instance)
    db.commit()

    logger.info("Deleted template instance %d", instance_id)
    return {"message": "Template instance deleted", "id": instance_id}


def get_instances(db: Session) -> list[TemplateInstance]:
    """List all template instances (including those with inactive assets for audit)."""
    return db.query(TemplateInstance).order_by(TemplateInstance.created_at.desc()).all()
