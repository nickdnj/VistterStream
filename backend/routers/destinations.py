"""
Streaming Destinations API - Configure YouTube, Facebook, Twitch, etc.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from models.database import get_db
from models.destination import StreamingDestination

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


# Pydantic schemas
class DestinationCreate(BaseModel):
    name: str
    platform: str  # "youtube", "facebook", "twitch", "custom"
    rtmp_url: str
    stream_key: str
    description: str = ""


class DestinationUpdate(BaseModel):
    name: str = None
    platform: str = None
    rtmp_url: str = None
    stream_key: str = None
    description: str = None
    is_active: bool = None


class DestinationResponse(BaseModel):
    id: int
    name: str
    platform: str
    rtmp_url: str
    stream_key: str  # Note: In production, you might want to mask this
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Platform presets for easy setup
PLATFORM_PRESETS = {
    "youtube": {
        "name": "YouTube Live",
        "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
        "description": "YouTube Live primary server"
    },
    "facebook": {
        "name": "Facebook Live",
        "rtmp_url": "rtmps://live-api-s.facebook.com:443/rtmp",
        "description": "Facebook Live streaming"
    },
    "twitch": {
        "name": "Twitch",
        "rtmp_url": "rtmp://live.twitch.tv/app",
        "description": "Twitch live streaming"
    },
    "custom": {
        "name": "Custom RTMP",
        "rtmp_url": "",
        "description": "Custom RTMP server"
    }
}


@router.get("/presets")
def get_platform_presets():
    """Get platform presets for easy setup"""
    return PLATFORM_PRESETS


@router.get("/", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db)):
    """Get all streaming destinations"""
    destinations = db.query(StreamingDestination).order_by(StreamingDestination.created_at.desc()).all()
    return destinations


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    """Get a specific destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    return destination


@router.post("/", response_model=DestinationResponse)
def create_destination(destination_data: DestinationCreate, db: Session = Depends(get_db)):
    """Create a new streaming destination"""
    try:
        destination = StreamingDestination(
            name=destination_data.name,
            platform=destination_data.platform,
            rtmp_url=destination_data.rtmp_url,
            stream_key=destination_data.stream_key,
            description=destination_data.description
        )
        db.add(destination)
        db.commit()
        db.refresh(destination)
        return destination
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create destination: {str(e)}")


@router.put("/{destination_id}", response_model=DestinationResponse)
def update_destination(
    destination_id: int,
    destination_data: DestinationUpdate,
    db: Session = Depends(get_db)
):
    """Update a streaming destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    # Update fields
    if destination_data.name is not None:
        destination.name = destination_data.name
    if destination_data.platform is not None:
        destination.platform = destination_data.platform
    if destination_data.rtmp_url is not None:
        destination.rtmp_url = destination_data.rtmp_url
    if destination_data.stream_key is not None:
        destination.stream_key = destination_data.stream_key
    if destination_data.description is not None:
        destination.description = destination_data.description
    if destination_data.is_active is not None:
        destination.is_active = destination_data.is_active
    
    destination.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(destination)
    return destination


@router.delete("/{destination_id}")
def delete_destination(destination_id: int, db: Session = Depends(get_db)):
    """Delete a streaming destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    db.delete(destination)
    db.commit()
    return {"message": "Destination deleted successfully"}


@router.post("/{destination_id}/mark-used")
def mark_destination_used(destination_id: int, db: Session = Depends(get_db)):
    """Mark a destination as recently used (updates last_used timestamp)"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    destination.last_used = datetime.utcnow()
    db.commit()
    
    return {"message": "Destination marked as used"}

