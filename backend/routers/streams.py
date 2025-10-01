"""
Streams API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from models.database import get_db
from models.schemas import Stream, StreamCreate, StreamUpdate, EncodingProfileSchema
from services.stream_service import StreamService

router = APIRouter(tags=["streams"])


@router.get("/", response_model=List[Stream])
async def get_streams(db: Session = Depends(get_db)):
    """Get all streams"""
    service = StreamService(db)
    return await service.get_all_streams()


@router.get("/{stream_id}", response_model=Stream)
async def get_stream(stream_id: int, db: Session = Depends(get_db)):
    """Get a specific stream"""
    service = StreamService(db)
    stream = await service.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


@router.post("/", response_model=Stream)
async def create_stream(stream: StreamCreate, db: Session = Depends(get_db)):
    """Create a new stream"""
    service = StreamService(db)
    try:
        return await service.create_stream(stream)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{stream_id}", response_model=Stream)
async def update_stream(
    stream_id: int,
    stream_update: StreamUpdate,
    db: Session = Depends(get_db)
):
    """Update a stream"""
    service = StreamService(db)
    stream = await service.update_stream(stream_id, stream_update)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream


@router.delete("/{stream_id}")
async def delete_stream(stream_id: int, db: Session = Depends(get_db)):
    """Delete a stream"""
    service = StreamService(db)
    success = await service.delete_stream(stream_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"message": "Stream deleted successfully"}


@router.post("/{stream_id}/start")
async def start_stream(
    stream_id: int,
    encoding_profile: EncodingProfileSchema = None,
    db: Session = Depends(get_db)
):
    """Start a stream"""
    service = StreamService(db)
    result = await service.start_stream(stream_id, encoding_profile)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/{stream_id}/stop")
async def stop_stream(stream_id: int, db: Session = Depends(get_db)):
    """Stop a stream"""
    service = StreamService(db)
    result = await service.stop_stream(stream_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/{stream_id}/status")
async def get_stream_status(stream_id: int, db: Session = Depends(get_db)):
    """Get stream status and metrics"""
    service = StreamService(db)
    status = await service.get_stream_status(stream_id)
    if not status:
        raise HTTPException(status_code=404, detail="Stream not found")
    return status
