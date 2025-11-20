"""
Settings API endpoints for general system configuration
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from models.database import get_db, Settings, Asset
from services.cloud_link_service import get_cloud_link_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Pydantic schemas
class SettingsResponse(BaseModel):
    id: int
    appliance_name: str
    timezone: str
    state_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    appliance_name: Optional[str] = None
    timezone: Optional[str] = None
    state_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.get("/", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Get current system settings"""
    settings = db.query(Settings).first()
    
    # If no settings exist, create default settings
    if not settings:
        settings = Settings(
            appliance_name="VistterStream Appliance",
            timezone="America/New_York"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return settings


@router.post("/", response_model=SettingsResponse)
def update_settings(settings_update: SettingsUpdate, db: Session = Depends(get_db)):
    """Update system settings and sync location to all assets"""
    settings = db.query(Settings).first()
    
    # If no settings exist, create them
    if not settings:
        settings = Settings()
        db.add(settings)
    
    # Update settings fields
    if settings_update.appliance_name is not None:
        settings.appliance_name = settings_update.appliance_name
    if settings_update.timezone is not None:
        settings.timezone = settings_update.timezone
    if settings_update.state_name is not None:
        settings.state_name = settings_update.state_name
    if settings_update.city is not None:
        settings.city = settings_update.city
    if settings_update.latitude is not None:
        settings.latitude = settings_update.latitude
    if settings_update.longitude is not None:
        settings.longitude = settings_update.longitude
    
    settings.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(settings)
    
    # Sync location information to all assets
    if any([
        settings_update.state_name is not None,
        settings_update.city is not None,
        settings_update.latitude is not None,
        settings_update.longitude is not None
    ]):
        assets = db.query(Asset).all()
        for asset in assets:
            if settings_update.state_name is not None:
                asset.state_name = settings.state_name
            if settings_update.city is not None:
                asset.city = settings.city
            if settings_update.latitude is not None:
                asset.latitude = settings.latitude
            if settings_update.longitude is not None:
                asset.longitude = settings.longitude
            asset.last_updated = datetime.utcnow()
        
        if assets:
            db.commit()
            print(f"✅ Synced location to {len(assets)} asset(s)")
    
    return settings


@router.post("/cloud/pair")
async def request_pairing():
    """Request a pairing code from the cloud"""
    service = get_cloud_link_service()
    success = await service.request_pairing()
    if not success:
        raise HTTPException(status_code=503, detail="Failed to request pairing. Check internet connection.")
    return {"status": "pairing_requested"}


@router.get("/cloud/status")
def get_cloud_status():
    """Get cloud connection status"""
    service = get_cloud_link_service()
    return service.get_status()

