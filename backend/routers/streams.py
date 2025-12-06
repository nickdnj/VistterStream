"""
Streaming API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import datetime

from models.database import get_db, Stream, Camera
from models.destination import StreamingDestination
from models.schemas import StreamCreate, StreamUpdate, Stream as StreamSchema, StreamStatus
from services.stream_service import StreamService

router = APIRouter()

def enrich_stream(stream_db: Stream, db: Session) -> dict:
    """Enrich stream with destination and camera details"""
    stream_dict = {
        "id": stream_db.id,
        "name": stream_db.name,
        "camera_id": stream_db.camera_id,
        "preset_id": stream_db.preset_id,
        "destination_id": stream_db.destination_id,
        "resolution": stream_db.resolution,
        "bitrate": stream_db.bitrate,
        "framerate": stream_db.framerate,
        "status": stream_db.status,
        "is_active": stream_db.is_active,
        "created_at": stream_db.created_at,
        "started_at": stream_db.started_at,
        "stopped_at": stream_db.stopped_at,
        "last_error": stream_db.last_error,
    }
    
    # Add destination details
    destination = db.query(StreamingDestination).filter(
        StreamingDestination.id == stream_db.destination_id
    ).first()
    if destination:
        stream_dict["destination"] = {
            "id": destination.id,
            "name": destination.name,
            "platform": destination.platform
        }
    
    # Add camera details
    camera = db.query(Camera).filter(Camera.id == stream_db.camera_id).first()
    if camera:
        stream_dict["camera"] = {
            "id": camera.id,
            "name": camera.name,
            "type": camera.type
        }
    
    # Add preset details (if preset is selected)
    if stream_db.preset_id:
        from models.database import Preset
        preset = db.query(Preset).filter(Preset.id == stream_db.preset_id).first()
        if preset:
            stream_dict["preset"] = {
                "id": preset.id,
                "name": preset.name,
                "pan": preset.pan,
                "tilt": preset.tilt,
                "zoom": preset.zoom
            }
    
    return stream_dict

@router.get("")
async def get_streams(db: Session = Depends(get_db)):
    """Get all streams"""
    streams = db.query(Stream).all()
    return [enrich_stream(stream, db) for stream in streams]

@router.get("/{stream_id}", response_model=StreamSchema)
async def get_stream(stream_id: int, db: Session = Depends(get_db)):
    """Get a specific stream by ID"""
    stream_service = StreamService(db)
    stream = await stream_service.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@router.post("")
async def create_stream(stream_data: StreamCreate, db: Session = Depends(get_db)):
    """Create a new stream"""
    try:
        # Create the stream
        stream_db = Stream(
            name=stream_data.name,
            camera_id=stream_data.camera_id,
            preset_id=stream_data.preset_id,
            destination_id=stream_data.destination_id,
            resolution=stream_data.resolution,
            bitrate=stream_data.bitrate,
            framerate=stream_data.framerate,
            status="stopped"
        )
        
        db.add(stream_db)
        db.commit()
        db.refresh(stream_db)
        
        # Return enriched stream data
        return enrich_stream(stream_db, db)
    except Exception as e:
        print(f"DEBUG: Error creating stream: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{stream_id}", response_model=StreamSchema)
async def update_stream(stream_id: int, stream_update: StreamUpdate, db: Session = Depends(get_db)):
    """Update a stream"""
    stream_service = StreamService(db)
    stream = await stream_service.update_stream(stream_id, stream_update)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@router.delete("/{stream_id}")
async def delete_stream(stream_id: int, db: Session = Depends(get_db)):
    """Delete a stream"""
    stream_service = StreamService(db)
    success = await stream_service.delete_stream(stream_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"message": "Stream deleted successfully"}

@router.post("/{stream_id}/start")
async def start_stream(stream_id: int, db: Session = Depends(get_db)):
    """Start a stream"""
    stream_service = StreamService(db)
    success = await stream_service.start_stream(stream_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"message": "Stream started successfully"}

@router.post("/{stream_id}/stop")
async def stop_stream(stream_id: int, db: Session = Depends(get_db)):
    """Stop a stream"""
    stream_service = StreamService(db)
    success = await stream_service.stop_stream(stream_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"message": "Stream stopped successfully"}

@router.get("/{stream_id}/status")
async def get_stream_status(stream_id: int, db: Session = Depends(get_db)):
    """Get stream status"""
    stream_service = StreamService(db)
    status = await stream_service.get_stream_status(stream_id)
    if not status:
        raise HTTPException(status_code=404, detail="Stream not found")
    return status
