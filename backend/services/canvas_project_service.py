"""
Canvas Project Service - Business logic for canvas project CRUD and export operations
"""

import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from models.database import Asset
from models.canvas import CanvasProject

logger = logging.getLogger(__name__)

# Resolve uploads directory from environment (same pattern as main.py)
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")


def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def create_project(
    db: Session,
    name: str,
    description: str | None,
    canvas_json: str,
    width: int,
    height: int,
    user_id: int | None = None,
) -> CanvasProject:
    """Create a new canvas project."""
    project = CanvasProject(
        name=name,
        description=description,
        canvas_json=canvas_json,
        width=width,
        height=height,
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Created canvas project id=%d name=%s", project.id, project.name)
    return project


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> list[CanvasProject]:
    """List active canvas projects (without full canvas_json for performance)."""
    return (
        db.query(CanvasProject)
        .filter(CanvasProject.is_active == True)
        .order_by(CanvasProject.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project(db: Session, project_id: int) -> CanvasProject | None:
    """Get a single canvas project by ID (includes canvas_json)."""
    return (
        db.query(CanvasProject)
        .filter(CanvasProject.id == project_id, CanvasProject.is_active == True)
        .first()
    )


def save_project(
    db: Session,
    project_id: int,
    canvas_json: str,
    thumbnail_data: str | None = None,
) -> CanvasProject | None:
    """Save/update a canvas project's JSON and optionally its thumbnail.

    Args:
        db: Database session
        project_id: Project to update
        canvas_json: Serialized Fabric.js JSON
        thumbnail_data: Optional base64-encoded PNG thumbnail
    """
    project = (
        db.query(CanvasProject)
        .filter(CanvasProject.id == project_id, CanvasProject.is_active == True)
        .first()
    )
    if not project:
        return None

    project.canvas_json = canvas_json
    project.updated_at = datetime.now(timezone.utc)

    # Save thumbnail if provided
    if thumbnail_data:
        try:
            # Strip data URL prefix if present (e.g. "data:image/png;base64,...")
            if "," in thumbnail_data:
                thumbnail_data = thumbnail_data.split(",", 1)[1]

            png_bytes = base64.b64decode(thumbnail_data)
            thumb_dir = os.path.join(UPLOADS_DIR, "canvas")
            _ensure_dir(thumb_dir)

            thumb_filename = f"{project_id}_thumb.png"
            thumb_path = os.path.join(thumb_dir, thumb_filename)
            with open(thumb_path, "wb") as f:
                f.write(png_bytes)

            project.thumbnail_path = f"/uploads/canvas/{thumb_filename}"
        except Exception as e:
            logger.warning("Failed to save thumbnail for project %d: %s", project_id, e)

    db.commit()
    db.refresh(project)
    logger.info("Saved canvas project id=%d", project.id)
    return project


def export_to_asset(
    db: Session,
    project_id: int,
    asset_name: str,
    png_data: str,
    position_x: float = 0.0,
    position_y: float = 0.0,
    width: int | None = None,
    height: int | None = None,
    opacity: float = 1.0,
) -> Asset:
    """Export a canvas project to a PNG asset.

    Decodes base64 PNG data, validates the PNG signature, saves the file,
    and creates an Asset record linked to the canvas project.
    """
    # Verify project exists
    project = (
        db.query(CanvasProject)
        .filter(CanvasProject.id == project_id, CanvasProject.is_active == True)
        .first()
    )
    if not project:
        raise ValueError(f"Canvas project {project_id} not found")

    # Strip data URL prefix if present
    raw_data = png_data
    if "," in raw_data:
        raw_data = raw_data.split(",", 1)[1]

    png_bytes = base64.b64decode(raw_data)

    # Validate PNG magic bytes
    PNG_MAGIC = b"\x89PNG"
    if not png_bytes[:4] == PNG_MAGIC:
        raise ValueError("Invalid PNG data: missing PNG signature")

    # Save file
    asset_dir = os.path.join(UPLOADS_DIR, "assets")
    _ensure_dir(asset_dir)

    file_uuid = str(uuid.uuid4())
    filename = f"{file_uuid}.png"
    file_path = os.path.join(asset_dir, filename)

    with open(file_path, "wb") as f:
        f.write(png_bytes)

    # Create Asset record
    asset = Asset(
        name=asset_name,
        type="canvas_composite",
        file_path=f"/uploads/assets/{filename}",
        width=width,
        height=height,
        position_x=position_x,
        position_y=position_y,
        opacity=opacity,
        canvas_project_id=project_id,
        description=f"Exported from canvas project: {project.name}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    logger.info(
        "Exported canvas project id=%d to asset id=%d file=%s",
        project_id,
        asset.id,
        filename,
    )
    return asset


def duplicate_project(db: Session, project_id: int) -> CanvasProject | None:
    """Duplicate a canvas project with ' (Copy)' appended to the name."""
    original = (
        db.query(CanvasProject)
        .filter(CanvasProject.id == project_id, CanvasProject.is_active == True)
        .first()
    )
    if not original:
        return None

    copy = CanvasProject(
        name=f"{original.name} (Copy)",
        description=original.description,
        canvas_json=original.canvas_json,
        width=original.width,
        height=original.height,
        user_id=original.user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    logger.info("Duplicated canvas project id=%d -> id=%d", project_id, copy.id)
    return copy


def delete_project(db: Session, project_id: int) -> bool:
    """Soft-delete a canvas project (set is_active=False)."""
    project = (
        db.query(CanvasProject)
        .filter(CanvasProject.id == project_id, CanvasProject.is_active == True)
        .first()
    )
    if not project:
        return False

    project.is_active = False
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Soft-deleted canvas project id=%d", project_id)
    return True
