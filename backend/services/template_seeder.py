"""
Template Catalog Seeder - Reads definition.json files from the catalog directory
and seeds/updates OverlayTemplate rows in the database at startup.
"""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from models.database import get_session
from models.template import OverlayTemplate

logger = logging.getLogger(__name__)

# Catalog directory containing template definition folders
CATALOG_DIR = Path(__file__).parent.parent / "templates" / "catalog"


def _load_definitions() -> list[dict]:
    """Scan the catalog directory and load all definition.json files."""
    definitions: list[dict] = []
    if not CATALOG_DIR.exists():
        logger.warning("Template catalog directory not found: %s", CATALOG_DIR)
        return definitions

    for entry in sorted(CATALOG_DIR.iterdir()):
        if not entry.is_dir():
            continue
        defn_path = entry / "definition.json"
        if not defn_path.exists():
            logger.debug("Skipping %s (no definition.json)", entry.name)
            continue
        try:
            with open(defn_path, "r") as f:
                data = json.load(f)
            # Attach the folder name for logging
            data["_folder"] = entry.name
            definitions.append(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", defn_path, exc)

    return definitions


def seed_templates() -> int:
    """Seed overlay templates from the catalog into the database.

    For each definition.json:
      - If no template with the same name exists, create it.
      - If a template exists and the definition version is higher, update it.
      - Otherwise, skip it.

    Returns the number of templates created or updated.
    """
    definitions = _load_definitions()
    if not definitions:
        logger.info("No template definitions found in catalog")
        return 0

    changed = 0

    with get_session() as db:
        for defn in definitions:
            name = defn.get("name")
            if not name:
                logger.warning("Skipping definition with no name in %s", defn.get("_folder", "?"))
                continue

            version = defn.get("version", 1)
            category = defn.get("category", "uncategorized")
            description = defn.get("description", "")
            config_schema = json.dumps(defn.get("config_schema", {}))
            default_config = json.dumps(defn.get("default_config", {}))

            existing = db.query(OverlayTemplate).filter(OverlayTemplate.name == name).first()

            if existing is None:
                # Create new template
                template = OverlayTemplate(
                    name=name,
                    category=category,
                    description=description,
                    config_schema=config_schema,
                    default_config=default_config,
                    version=version,
                    is_bundled=True,
                    is_active=True,
                )
                db.add(template)
                db.commit()
                logger.info("Seeded new template: %s (v%d)", name, version)
                changed += 1

            elif version > existing.version:
                # Update existing template with newer version
                existing.category = category
                existing.description = description
                existing.config_schema = config_schema
                existing.default_config = default_config
                existing.version = version
                db.commit()
                logger.info("Updated template: %s (v%d -> v%d)", name, existing.version, version)
                changed += 1

            else:
                logger.debug("Template %s already up to date (v%d)", name, existing.version)

    logger.info("Template seeder complete: %d/%d templates created/updated", changed, len(definitions))
    return changed
