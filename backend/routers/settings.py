"""
Settings API endpoints for general system configuration
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from models.database import get_db, Settings, Asset
from routers.auth import get_current_user
from services import email_service
from utils.crypto import encrypt

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


# Pydantic schemas
class SettingsResponse(BaseModel):
    id: int
    appliance_name: str
    timezone: str
    state_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # SMTP configuration (password is never returned — only whether one is set)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_from_address: Optional[str] = None
    smtp_use_tls: Optional[bool] = True
    smtp_password_set: bool = False
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
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    # Write-only: plaintext password. None = leave unchanged, "" = clear.
    smtp_password: Optional[str] = None
    smtp_from_address: Optional[str] = None
    smtp_use_tls: Optional[bool] = None


class TestEmailRequest(BaseModel):
    to_address: str


def _with_password_flag(settings: Settings) -> Settings:
    """Attach a transient smtp_password_set flag for serialization."""
    settings.smtp_password_set = bool(settings.smtp_password_encrypted)
    return settings


@router.get("", response_model=SettingsResponse)
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

    return _with_password_flag(settings)


@router.post("", response_model=SettingsResponse)
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

    # SMTP fields
    if settings_update.smtp_host is not None:
        settings.smtp_host = settings_update.smtp_host.strip() or None
    if settings_update.smtp_port is not None:
        settings.smtp_port = settings_update.smtp_port
    if settings_update.smtp_username is not None:
        settings.smtp_username = settings_update.smtp_username.strip() or None
    if settings_update.smtp_from_address is not None:
        settings.smtp_from_address = settings_update.smtp_from_address.strip() or None
    if settings_update.smtp_use_tls is not None:
        settings.smtp_use_tls = settings_update.smtp_use_tls
    if settings_update.smtp_password is not None:
        # "" clears the stored password; any other value is encrypted at rest.
        if settings_update.smtp_password == "":
            settings.smtp_password_encrypted = None
        else:
            settings.smtp_password_encrypted = encrypt(settings_update.smtp_password)

    settings.updated_at = datetime.now(timezone.utc)
    
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
            asset.last_updated = datetime.now(timezone.utc)
        
        if assets:
            db.commit()
            print(f"✅ Synced location to {len(assets)} asset(s)")

    return _with_password_flag(settings)


@router.post("/test-email")
def send_test_email(payload: TestEmailRequest, db: Session = Depends(get_db)):
    """Send a test email using the saved SMTP settings."""
    settings = db.query(Settings).first()
    try:
        email_service.send_email(
            settings,
            payload.to_address,
            "VistterStream SMTP test",
            "This is a test email from your VistterStream appliance. "
            "If you received this, password-reset emails will work.",
        )
    except email_service.EmailNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except email_service.EmailSendError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send: {exc}")
    return {"success": True, "message": f"Test email sent to {payload.to_address}"}

