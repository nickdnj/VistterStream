"""
PTZ Preset API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import base64

from models.database import get_db, Preset, Camera
from models.schemas import PresetCreate, PresetUpdate, Preset as PresetSchema
from services.ptz_service import get_ptz_service

router = APIRouter(prefix="/api/presets", tags=["presets"])


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
    
    # Move to preset
    # ONVIF typically runs on port 80, not the RTSP port
    onvif_port = 80 if camera.port == 554 else camera.port
    ptz_service = get_ptz_service()
    success = await ptz_service.move_to_preset(
        address=camera.address,
        port=onvif_port,
        username=camera.username,
        password=password,
        preset_token=str(preset.id)  # Use preset ID as token
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
    
    # Get current position
    # ONVIF typically runs on port 80, not the RTSP port
    onvif_port = 80 if camera.port == 554 else camera.port
    ptz_service = get_ptz_service()
    position = await ptz_service.get_current_position(
        address=camera.address,
        port=onvif_port,
        username=camera.username,
        password=password
    )
    
    if position is None:
        raise HTTPException(status_code=500, detail="Failed to get current camera position")
    
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
    db.commit()
    db.refresh(preset)
    
    # Save preset on camera (optional, some cameras support this)
    try:
        await ptz_service.set_preset(
            address=camera.address,
            port=onvif_port,
            username=camera.username,
            password=password,
            preset_token=str(preset.id),
            preset_name=preset_name
        )
    except Exception as e:
        print(f"Warning: Could not save preset on camera: {e}")
        # Continue anyway, we have it in our database
    
    return {
        "message": f"Preset '{preset_name}' captured successfully",
        "preset": PresetSchema.from_orm(preset)
    }
