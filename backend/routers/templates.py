"""
Templates API Router - Manage overlay templates and template instances
for the Asset Management Studio.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from models.database import get_db, Asset as AssetModel
from models.template import TemplateInstance
from models.schemas import (
    OverlayTemplateRead,
    TemplateInstanceCreate,
    TemplateInstanceUpdate,
    TemplateInstanceRead,
)
from routers.auth import get_current_user
from routers.assets import _validate_url
from services.template_service import (
    get_templates,
    get_template,
    instantiate_template,
    update_instance,
    delete_instance,
    get_instances,
    TemplateNotFoundError,
    InstanceNotFoundError,
    ConfigValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/templates",
    tags=["templates"],
    dependencies=[Depends(get_current_user)],
)


# ---------------------------------------------------------------------------
# Template instance endpoints (registered before /{template_id} to avoid
# path-parameter shadowing)
# ---------------------------------------------------------------------------

@router.get("/instances", response_model=List[TemplateInstanceRead])
def list_instances(db: Session = Depends(get_db)):
    """List all template instances."""
    return get_instances(db)


# ---------------------------------------------------------------------------
# Template catalog endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[OverlayTemplateRead])
def list_templates(
    category: Optional[str] = Query(None, description="Filter by category (e.g. weather, lower_third)"),
    db: Session = Depends(get_db),
):
    """List all active overlay templates, optionally filtered by category."""
    return get_templates(db, category=category)


@router.get("/{template_id}", response_model=OverlayTemplateRead)
def get_template_detail(template_id: int, db: Session = Depends(get_db)):
    """Get a single overlay template by ID."""
    try:
        return get_template(db, template_id)
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")


@router.post("/instances", response_model=TemplateInstanceRead)
def create_instance(
    data: TemplateInstanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Instantiate a template: validate config, create asset, return instance."""
    try:
        config_values = json.loads(data.config_values)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="config_values must be valid JSON")

    try:
        asset = instantiate_template(
            db=db,
            template_id=data.template_id,
            config_values=config_values,
            user_id=getattr(current_user, "id", None),
            position_x=data.position_x,
            position_y=data.position_y,
            width=data.width,
            height=data.height,
            opacity=data.opacity,
            name=data.name,
        )
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
    except ConfigValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Validate the generated API URL if the asset is api_image
    if asset.type == "api_image" and asset.api_url:
        if not _validate_url(asset.api_url, allow_internal=True):
            raise HTTPException(
                status_code=400,
                detail="Generated API URL is not allowed (blocked scheme or address)",
            )

    # Return the instance (the asset was already committed by the service)
    instance = db.query(TemplateInstance).filter_by(asset_id=asset.id).first()
    if not instance:
        raise HTTPException(status_code=500, detail="Instance created but could not be retrieved")

    return instance


@router.put("/instances/{instance_id}", response_model=TemplateInstanceRead)
def update_instance_endpoint(
    instance_id: int,
    data: TemplateInstanceUpdate,
    db: Session = Depends(get_db),
):
    """Update a template instance's config and/or display properties."""
    config_values = None
    if data.config_values is not None:
        try:
            config_values = json.loads(data.config_values)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="config_values must be valid JSON")

    try:
        instance = update_instance(
            db=db,
            instance_id=instance_id,
            config_values=config_values,
            position_x=data.position_x,
            position_y=data.position_y,
            width=data.width,
            height=data.height,
            opacity=data.opacity,
        )
    except InstanceNotFoundError:
        raise HTTPException(status_code=404, detail="Template instance not found")
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Associated template not found")
    except ConfigValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Validate the asset's API URL after update
    if instance.asset_id:
        asset = db.query(AssetModel).filter(AssetModel.id == instance.asset_id).first()
        if asset and asset.type == "api_image" and asset.api_url:
            if not _validate_url(asset.api_url, allow_internal=True):
                raise HTTPException(
                    status_code=400,
                    detail="Updated API URL is not allowed (blocked scheme or address)",
                )

    return instance


@router.delete("/instances/{instance_id}")
def delete_instance_endpoint(instance_id: int, db: Session = Depends(get_db)):
    """Delete a template instance and deactivate its linked asset."""
    try:
        return delete_instance(db, instance_id)
    except InstanceNotFoundError:
        raise HTTPException(status_code=404, detail="Template instance not found")
