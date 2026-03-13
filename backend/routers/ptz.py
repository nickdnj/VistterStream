"""
PTZ Camera Movement API endpoints
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from models.database import Camera, get_db
from services.ptz_service import get_ptz_service
from utils.crypto import decrypt
from routers.auth import get_current_user

router = APIRouter(
    prefix="/{camera_id}/ptz",
    tags=["ptz"],
    dependencies=[Depends(get_current_user)],
)
logger = logging.getLogger(__name__)


class ContinuousMoveRequest(BaseModel):
    pan_speed: float = Field(default=0.0, ge=-1.0, le=1.0)
    tilt_speed: float = Field(default=0.0, ge=-1.0, le=1.0)
    zoom_speed: float = Field(default=0.0, ge=-1.0, le=1.0)


class AbsoluteMoveRequest(BaseModel):
    pan: Optional[float] = None
    tilt: Optional[float] = None
    zoom: Optional[float] = None


def _get_ptz_camera(camera_id: int, db: Session):
    """Look up a PTZ camera and decrypt its credentials."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if camera.type != "ptz":
        raise HTTPException(status_code=400, detail="Camera is not a PTZ camera")

    password = None
    if camera.password_enc:
        password = decrypt(camera.password_enc)
    if not password:
        raise HTTPException(status_code=400, detail="Camera credentials not configured")

    return camera, password


@router.post("/continuous")
async def continuous_move(camera_id: int, body: ContinuousMoveRequest, db: Session = Depends(get_db)):
    """Start continuous PTZ movement."""
    camera, password = _get_ptz_camera(camera_id, db)
    ptz_service = get_ptz_service()
    success = await ptz_service.continuous_move(
        address=camera.address,
        port=camera.onvif_port,
        username=camera.username,
        password=password,
        pan_speed=body.pan_speed,
        tilt_speed=body.tilt_speed,
        zoom_speed=body.zoom_speed,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start continuous move")
    return {"message": "Continuous move started"}


@router.post("/stop")
async def stop_movement(camera_id: int, db: Session = Depends(get_db)):
    """Stop all PTZ movement."""
    camera, password = _get_ptz_camera(camera_id, db)
    ptz_service = get_ptz_service()
    success = await ptz_service.stop_movement(
        address=camera.address,
        port=camera.onvif_port,
        username=camera.username,
        password=password,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop movement")
    return {"message": "Movement stopped"}


@router.post("/absolute")
async def absolute_move(camera_id: int, body: AbsoluteMoveRequest, db: Session = Depends(get_db)):
    """Move to an absolute PTZ position."""
    camera, password = _get_ptz_camera(camera_id, db)
    ptz_service = get_ptz_service()
    success = await ptz_service.absolute_move(
        address=camera.address,
        port=camera.onvif_port,
        username=camera.username,
        password=password,
        pan=body.pan,
        tilt=body.tilt,
        zoom=body.zoom,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to execute absolute move")
    return {"message": "Absolute move completed"}


@router.get("/status")
async def get_status(camera_id: int, db: Session = Depends(get_db)):
    """Get current PTZ position."""
    camera, password = _get_ptz_camera(camera_id, db)
    ptz_service = get_ptz_service()
    position = await ptz_service.get_current_position(
        address=camera.address,
        port=camera.onvif_port,
        username=camera.username,
        password=password,
    )
    if not position:
        return {"camera_id": camera.id, "available": False}

    pan, tilt, zoom = position
    return {
        "camera_id": camera.id,
        "available": True,
        "pan": pan,
        "tilt": tilt,
        "zoom": zoom,
    }
