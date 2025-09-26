"""
PTZ Preset API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.database import get_db, Preset
from models.schemas import PresetCreate, PresetUpdate, Preset as PresetSchema
from services.preset_service import PresetService

router = APIRouter()

@router.get("/", response_model=List[PresetSchema])
async def get_presets(db: Session = Depends(get_db)):
    """Get all presets"""
    preset_service = PresetService(db)
    return await preset_service.get_all_presets()

@router.get("/{preset_id}", response_model=PresetSchema)
async def get_preset(preset_id: int, db: Session = Depends(get_db)):
    """Get a specific preset by ID"""
    preset_service = PresetService(db)
    preset = await preset_service.get_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset

@router.post("/", response_model=PresetSchema)
async def create_preset(preset: PresetCreate, db: Session = Depends(get_db)):
    """Create a new preset"""
    preset_service = PresetService(db)
    return await preset_service.create_preset(preset)

@router.put("/{preset_id}", response_model=PresetSchema)
async def update_preset(preset_id: int, preset_update: PresetUpdate, db: Session = Depends(get_db)):
    """Update a preset"""
    preset_service = PresetService(db)
    preset = await preset_service.update_preset(preset_id, preset_update)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset

@router.delete("/{preset_id}")
async def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    """Delete a preset"""
    preset_service = PresetService(db)
    success = await preset_service.delete_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"message": "Preset deleted successfully"}

@router.post("/{preset_id}/execute")
async def execute_preset(preset_id: int, db: Session = Depends(get_db)):
    """Execute a PTZ preset"""
    preset_service = PresetService(db)
    success = await preset_service.execute_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"message": "Preset executed successfully"}
