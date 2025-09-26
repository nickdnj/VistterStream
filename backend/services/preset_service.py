"""
Preset service for managing PTZ presets
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models.database import Preset
from models.schemas import PresetCreate, PresetUpdate, Preset as PresetSchema

class PresetService:
    def __init__(self, db: Session):
        self.db = db

    async def get_all_presets(self) -> List[PresetSchema]:
        """Get all presets"""
        presets = self.db.query(Preset).all()
        return [PresetSchema.from_orm(preset) for preset in presets]

    async def get_preset(self, preset_id: int) -> Optional[PresetSchema]:
        """Get a specific preset by ID"""
        preset = self.db.query(Preset).filter(Preset.id == preset_id).first()
        if not preset:
            return None
        return PresetSchema.from_orm(preset)

    async def create_preset(self, preset_data: PresetCreate) -> PresetSchema:
        """Create a new preset"""
        preset = Preset(
            camera_id=preset_data.camera_id,
            name=preset_data.name,
            pan=preset_data.pan,
            tilt=preset_data.tilt,
            zoom=preset_data.zoom
        )
        
        self.db.add(preset)
        self.db.commit()
        self.db.refresh(preset)
        
        return PresetSchema.from_orm(preset)

    async def update_preset(self, preset_id: int, preset_update: PresetUpdate) -> Optional[PresetSchema]:
        """Update a preset"""
        preset = self.db.query(Preset).filter(Preset.id == preset_id).first()
        if not preset:
            return None
        
        update_data = preset_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preset, field, value)
        
        self.db.commit()
        self.db.refresh(preset)
        
        return PresetSchema.from_orm(preset)

    async def delete_preset(self, preset_id: int) -> bool:
        """Delete a preset"""
        preset = self.db.query(Preset).filter(Preset.id == preset_id).first()
        if not preset:
            return False
        
        self.db.delete(preset)
        self.db.commit()
        return True

    async def execute_preset(self, preset_id: int) -> bool:
        """Execute a PTZ preset"""
        preset = self.db.query(Preset).filter(Preset.id == preset_id).first()
        if not preset:
            return False
        
        # TODO: Implement actual PTZ control via ONVIF
        # For now, just return success
        return True
