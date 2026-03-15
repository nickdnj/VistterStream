"""
Canvas Projects API Router - Manage Fabric.js canvas projects for the Asset Management Studio
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models.database import get_db
from models.schemas import (
    CanvasProjectCreate,
    CanvasProjectSave,
    CanvasProjectRead,
    CanvasProjectDetail,
    CanvasProjectExport,
    Asset as AssetSchema,
)
from routers.auth import get_current_user
from services import canvas_project_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/canvas-projects",
    tags=["canvas-projects"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[CanvasProjectRead])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all active canvas projects (without full canvas JSON)."""
    return canvas_project_service.get_projects(db, skip=skip, limit=limit)


@router.post("", response_model=CanvasProjectDetail)
def create_project(
    data: CanvasProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new canvas project."""
    project = canvas_project_service.create_project(
        db,
        name=data.name,
        description=data.description,
        canvas_json=data.canvas_json,
        width=data.width,
        height=data.height,
    )
    return project


@router.get("/{project_id}", response_model=CanvasProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a canvas project with full canvas JSON."""
    project = canvas_project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Canvas project not found")
    return project


@router.put("/{project_id}", response_model=CanvasProjectDetail)
def save_project(
    project_id: int,
    data: CanvasProjectSave,
    db: Session = Depends(get_db),
):
    """Save/update a canvas project's JSON and optional thumbnail."""
    project = canvas_project_service.save_project(
        db,
        project_id=project_id,
        canvas_json=data.canvas_json,
        thumbnail_data=data.thumbnail_data,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Canvas project not found")
    return project


@router.post("/{project_id}/export", response_model=AssetSchema)
def export_project(
    project_id: int,
    data: CanvasProjectExport,
    db: Session = Depends(get_db),
):
    """Export the canvas as a PNG asset for use in overlays."""
    try:
        asset = canvas_project_service.export_to_asset(
            db,
            project_id=project_id,
            asset_name=data.asset_name,
            png_data=data.png_data,
            position_x=data.position_x,
            position_y=data.position_y,
            width=data.width,
            height=data.height,
            opacity=data.opacity,
        )
        return asset
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/duplicate", response_model=CanvasProjectDetail)
def duplicate_project(project_id: int, db: Session = Depends(get_db)):
    """Duplicate a canvas project."""
    project = canvas_project_service.duplicate_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Canvas project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Soft-delete a canvas project."""
    deleted = canvas_project_service.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Canvas project not found")
    return {"message": "Canvas project deleted successfully", "id": project_id}
