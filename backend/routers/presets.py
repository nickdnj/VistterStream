"""
PTZ Preset API endpoints
"""

import base64
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import Camera, Preset, get_db
from models.schemas import Preset as PresetSchema
from models.schemas import PresetCreate, PresetUpdate
from services.ptz_service import get_ptz_service

router = APIRouter(prefix="/api/presets", tags=["presets"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[PresetSchema])
def get_presets(camera_id: int = None, db: Session = Depends(get_db)):
    """Get all presets, optionally filtered by camera"""
    query = db.query(Preset)
    if camera_id:
        query = query.filter(Preset.camera_id == camera_id)
    return query.all()


@router.get("/{preset_id}", response_model=PresetSchema)
def get_preset(preset_id: int, db: Session = Depends(get_db)):
    """Get a specific preset by ID"""
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.post("/", response_model=PresetSchema, status_code=201)
def create_preset(preset: PresetCreate, db: Session = Depends(get_db)):
    """Create a new preset"""
    # Verify camera exists
    camera = db.query(Camera).filter(Camera.id == preset.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Verify camera is PTZ
    if camera.type != "ptz":
        raise HTTPException(status_code=400, detail="Camera is not a PTZ camera")
    
    # Create preset
    db_preset = Preset(**preset.model_dump())
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    
    return db_preset


@router.put("/{preset_id}", response_model=PresetSchema)
def update_preset(preset_id: int, preset_update: PresetUpdate, db: Session = Depends(get_db)):
    """Update an existing preset"""
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    update_data = preset_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(preset, key, value)
    
    db.commit()
    db.refresh(preset)
    
    return preset


@router.delete("/{preset_id}", status_code=204)
def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    """Delete a preset"""
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    db.delete(preset)
    db.commit()
    return


@router.post("/{preset_id}/move")
async def move_to_preset(preset_id: int, db: Session = Depends(get_db)):
    """Move camera to preset position"""
    # Get preset
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # Get camera
    camera = db.query(Camera).filter(Camera.id == preset.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Get camera password
    password = None
    if camera.password_enc:
        password = base64.b64decode(camera.password_enc).decode()
    
    if not password:
        raise HTTPException(status_code=400, detail="Camera credentials not configured")
    
    # Move to preset using configured ONVIF port
    ptz_service = get_ptz_service()
    success = await ptz_service.move_to_preset(
        address=camera.address,
        port=camera.onvif_port,
        username=camera.username,
        password=password,
        preset_token=preset.camera_preset_token or str(preset.id)
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to move camera to preset")
    
    return {
        "message": f"Camera moved to preset '{preset.name}'",
        "preset_id": preset.id,
        "preset_name": preset.name,
        "camera_id": camera.id,
        "camera_name": camera.name
    }


@router.post("/capture")
async def capture_current_position(camera_id: int, preset_name: str, db: Session = Depends(get_db)):
    """Capture current camera position as a new preset"""
    # Get camera
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    if camera.type != "ptz":
        raise HTTPException(status_code=400, detail="Camera is not a PTZ camera")
    
    # Get camera password
    password = None
    if camera.password_enc:
        password = base64.b64decode(camera.password_enc).decode()
    
    if not password:
        raise HTTPException(status_code=400, detail="Camera credentials not configured")
    
    # Get current position using configured ONVIF port
    ptz_service = get_ptz_service()

    try:
        position = await ptz_service.get_current_position(
            address=camera.address,
            port=camera.onvif_port,
            username=camera.username,
            password=password
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to get PTZ status for camera %s: %s", camera.name, exc)
        position = None
    
    if position is None:
        # Fall back to defaults but continue so we can still attempt to save preset on camera
        logger.warning(
            "Proceeding without PTZ coordinates for camera %s; storing defaults",
            camera.name
        )
        pan, tilt, zoom = 0.0, 0.0, 1.0
    else:
        pan, tilt, zoom = position
    
    # Create preset
    preset = Preset(
        camera_id=camera_id,
        name=preset_name,
        pan=pan,
        tilt=tilt,
        zoom=zoom
    )
    
    db.add(preset)
    db.flush()  # Ensure preset.id is populated for ONVIF calls
    
    try:
        if not preset.camera_preset_token:
            # Use deterministic token per preset if camera won't return one
            preset.camera_preset_token = str(preset.id)

        camera_token = await ptz_service.set_preset(
            address=camera.address,
            port=camera.onvif_port,
            username=camera.username,
            password=password,
            preset_name=preset_name,
            preset_token=preset.camera_preset_token
        )
        preset.camera_preset_token = camera_token

        if position is None:
            # Try again now that the camera saved the preset
            try:
                refreshed_position = await ptz_service.get_current_position(
                    address=camera.address,
                    port=camera.onvif_port,
                    username=camera.username,
                    password=password
                )
                if refreshed_position:
                    preset.pan, preset.tilt, preset.zoom = refreshed_position
            except Exception as refresh_exc:  # pragma: no cover - defensive logging
                logger.debug(
                    "Unable to refresh PTZ coordinates for camera %s: %s",
                    camera.name,
                    refresh_exc
                )

        db.commit()
        db.refresh(preset)
    except Exception as exc:
        logger.error("Unable to save preset on camera %s: %s", camera.name, exc)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save preset on camera"
        ) from exc
    
    return {
        "message": f"Preset '{preset_name}' captured successfully",
        "preset": PresetSchema.from_orm(preset)
    }
