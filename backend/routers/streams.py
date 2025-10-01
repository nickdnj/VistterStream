"""
Streaming API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from models.database import get_db, Stream
from models.schemas import StreamCreate, StreamUpdate, Stream as StreamSchema, StreamStatus
from services.stream_service import StreamService

router = APIRouter()

@router.get("/", response_model=List[StreamSchema])
async def get_streams(db: Session = Depends(get_db)):
    """Get all streams"""
    stream_service = StreamService(db)
    return await stream_service.get_all_streams()

@router.get("/{stream_id}", response_model=StreamSchema)
async def get_stream(stream_id: int, db: Session = Depends(get_db)):
    """Get a specific stream by ID"""
    stream_service = StreamService(db)
    stream = await stream_service.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream

@router.post("/", response_model=StreamSchema)
async def create_stream(stream: StreamCreate, db: Session = Depends(get_db)):
    """Create a new stream"""
    try:
        stream_service = StreamService(db)
        result = await stream_service.create_stream(stream)
        print(f"DEBUG: Stream created successfully: {result}")
        return result
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
