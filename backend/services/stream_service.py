"""
Stream service for managing streaming operations
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models.database import Stream
from models.schemas import StreamCreate, StreamUpdate, Stream as StreamSchema, StreamStatus

class StreamService:
    def __init__(self, db: Session):
        self.db = db

    async def get_all_streams(self) -> List[StreamSchema]:
        """Get all streams"""
        streams = self.db.query(Stream).all()
        return [StreamSchema.from_orm(stream) for stream in streams]

    async def get_stream(self, stream_id: int) -> Optional[StreamSchema]:
        """Get a specific stream by ID"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return None
        return StreamSchema.from_orm(stream)

    async def create_stream(self, stream_data: StreamCreate) -> StreamSchema:
        """Create a new stream"""
        stream = Stream(
            camera_id=stream_data.camera_id,
            destination=stream_data.destination,
            stream_key=stream_data.stream_key,
            rtmp_url=stream_data.rtmp_url,
            status=StreamStatus.STOPPED
        )
        
        self.db.add(stream)
        self.db.commit()
        self.db.refresh(stream)
        
        return StreamSchema.from_orm(stream)

    async def update_stream(self, stream_id: int, stream_update: StreamUpdate) -> Optional[StreamSchema]:
        """Update a stream"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return None
        
        update_data = stream_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stream, field, value)
        
        self.db.commit()
        self.db.refresh(stream)
        
        return StreamSchema.from_orm(stream)

    async def delete_stream(self, stream_id: int) -> bool:
        """Delete a stream"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False
        
        self.db.delete(stream)
        self.db.commit()
        return True

    async def start_stream(self, stream_id: int) -> bool:
        """Start a stream"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False
        
        # Update stream status
        stream.status = StreamStatus.STARTING
        stream.started_at = datetime.utcnow()
        self.db.commit()
        
        # TODO: Implement actual FFmpeg stream start
        # For now, just mark as running
        stream.status = StreamStatus.RUNNING
        self.db.commit()
        
        return True

    async def stop_stream(self, stream_id: int) -> bool:
        """Stop a stream"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False
        
        # Update stream status
        stream.status = StreamStatus.STOPPED
        stream.stopped_at = datetime.utcnow()
        self.db.commit()
        
        # TODO: Implement actual FFmpeg stream stop
        
        return True

    async def get_stream_status(self, stream_id: int) -> Optional[dict]:
        """Get stream status"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return None
        
        return {
            "stream_id": stream.id,
            "status": stream.status,
            "started_at": stream.started_at,
            "stopped_at": stream.stopped_at,
            "error_message": stream.error_message
        }
