"""
Camera management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import httpx
import cv2
import asyncio
from datetime import datetime

from models.database import get_db, Camera, Preset
from models.schemas import (
    CameraCreate, CameraUpdate, Camera as CameraSchema, 
    CameraWithStatus, CameraTestResponse, PresetCreate, Preset
)
from services.camera_service import CameraService

router = APIRouter()

@router.get("/", response_model=List[CameraWithStatus])
async def get_cameras(db: Session = Depends(get_db)):
    """Get all cameras with their current status"""
    camera_service = CameraService(db)
    return await camera_service.get_all_cameras_with_status()

@router.get("/{camera_id}", response_model=CameraWithStatus)
async def get_camera(camera_id: int, db: Session = Depends(get_db)):
    """Get a specific camera by ID"""
    camera_service = CameraService(db)
    camera = await camera_service.get_camera_with_status(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.post("/", response_model=CameraSchema)
async def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    """Create a new camera"""
    camera_service = CameraService(db)
    return await camera_service.create_camera(camera)

@router.put("/{camera_id}", response_model=CameraSchema)
async def update_camera(camera_id: int, camera_update: CameraUpdate, db: Session = Depends(get_db)):
    """Update a camera"""
    camera_service = CameraService(db)
    camera = await camera_service.update_camera(camera_id, camera_update)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.delete("/{camera_id}")
async def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    """Delete a camera"""
    camera_service = CameraService(db)
    success = await camera_service.delete_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"message": "Camera deleted successfully"}

@router.post("/{camera_id}/test", response_model=CameraTestResponse)
async def test_camera_connection(camera_id: int, db: Session = Depends(get_db)):
    """Test camera connection and accessibility"""
    camera_service = CameraService(db)
    return await camera_service.test_camera_connection(camera_id)

@router.post("/test-connection", response_model=CameraTestResponse)
async def test_camera_connection_direct(camera: CameraCreate, db: Session = Depends(get_db)):
    """Test camera connection without saving to database"""
    camera_service = CameraService(db)
    return await camera_service.test_camera_connection_direct(camera)

@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: int, db: Session = Depends(get_db)):
    """Get a snapshot from the camera"""
    camera_service = CameraService(db)
    snapshot_data = await camera_service.get_camera_snapshot(camera_id)
    if not snapshot_data:
        raise HTTPException(status_code=404, detail="Camera not found or snapshot not available")
    return snapshot_data

@router.post("/{camera_id}/presets", response_model=Preset)
async def create_preset(camera_id: int, preset: PresetCreate, db: Session = Depends(get_db)):
    """Create a PTZ preset for a camera"""
    camera_service = CameraService(db)
    # Ensure the preset belongs to the correct camera
    preset.camera_id = camera_id
    return await camera_service.create_preset(preset)

@router.get("/{camera_id}/presets", response_model=List[Preset])
async def get_camera_presets(camera_id: int, db: Session = Depends(get_db)):
    """Get all presets for a camera"""
    camera_service = CameraService(db)
    return await camera_service.get_camera_presets(camera_id)

@router.post("/{camera_id}/presets/{preset_id}/execute")
async def execute_preset(camera_id: int, preset_id: int, db: Session = Depends(get_db)):
    """Execute a PTZ preset"""
    camera_service = CameraService(db)
    success = await camera_service.execute_preset(camera_id, preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera or preset not found")
    return {"message": "Preset executed successfully"}
