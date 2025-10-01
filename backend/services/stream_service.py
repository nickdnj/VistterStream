"""
Stream service for managing streaming operations
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import base64

from models.database import Stream, Camera
from models.schemas import StreamCreate, StreamUpdate, Stream as StreamSchema, StreamStatus
from services.ffmpeg_manager import FFmpegProcessManager

class StreamService:
    def __init__(self, db: Session):
        self.db = db
        self._ffmpeg_manager = None
    
    async def get_ffmpeg_manager(self):
        """Lazy-load and initialize FFmpeg manager"""
        if self._ffmpeg_manager is None:
            self._ffmpeg_manager = FFmpegProcessManager()
            await self._ffmpeg_manager.initialize()
        return self._ffmpeg_manager

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
            name=stream_data.name,
            camera_id=stream_data.camera_id,
            destination=stream_data.destination.value,  # Convert enum to string
            stream_key=stream_data.stream_key,
            rtmp_url=stream_data.rtmp_url,
            resolution=stream_data.resolution,
            bitrate=stream_data.bitrate,
            framerate=stream_data.framerate,
            status=StreamStatus.STOPPED.value  # Convert enum to string
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

    def _build_rtsp_url(self, camera: Camera) -> str:
        """Build RTSP URL from camera configuration"""
        password = None
        if camera.password_enc:
            password = base64.b64decode(camera.password_enc).decode()
        
        if camera.username and password:
            return f"rtsp://{camera.username}:{password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            return f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"

    async def start_stream(self, stream_id: int) -> bool:
        """Start a stream using FFmpeg"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False
        
        # Get the camera
        camera = self.db.query(Camera).filter(Camera.id == stream.camera_id).first()
        if not camera:
            stream.last_error = "Camera not found"
            stream.status = StreamStatus.ERROR.value
            self.db.commit()
            return False
        
        # Update stream status
        stream.status = StreamStatus.STARTING.value
        stream.started_at = datetime.utcnow()
        stream.last_error = None
        self.db.commit()
        
        try:
            # Build RTSP input URL
            rtsp_url = self._build_rtsp_url(camera)
            
            # Build RTMP output URL with stream key
            rtmp_output = f"{stream.rtmp_url}/{stream.stream_key}"
            
            # Parse resolution
            width, height = stream.resolution.split('x')
            
            # Get FFmpeg manager
            ffmpeg_manager = await self.get_ffmpeg_manager()
            
            # Build encoding profile
            encoding_profile = {
                'codec': ffmpeg_manager.hw_capabilities.encoder,
                'resolution': (int(width), int(height)),
                'framerate': stream.framerate,
                'bitrate': stream.bitrate,
                'keyframe_interval': 2,
                'buffer_size': f"{int(stream.bitrate.replace('k', '')) * 2}k",
                'preset': 'fast',
                'profile': 'main',
                'level': '4.1'
            }
            
            # Start the stream
            print(f"DEBUG: Starting stream {stream.id} from {rtsp_url} to {rtmp_output}")
            await ffmpeg_manager.start_stream(
                stream_id=stream.id,
                input_url=rtsp_url,
                output_url=rtmp_output,
                encoding_profile=encoding_profile
            )
            
            # Update stream status
            stream.status = StreamStatus.RUNNING.value
            self.db.commit()
            
            print(f"DEBUG: Stream {stream.id} started successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: Failed to start stream {stream.id}: {e}")
            stream.status = StreamStatus.ERROR.value
            stream.last_error = str(e)
            self.db.commit()
            return False

    async def stop_stream(self, stream_id: int) -> bool:
        """Stop a stream"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False
        
        try:
            # Get FFmpeg manager and stop process
            ffmpeg_manager = await self.get_ffmpeg_manager()
            await ffmpeg_manager.stop_stream(stream_id)
            
            # Update stream status
            stream.status = StreamStatus.STOPPED.value
            stream.stopped_at = datetime.utcnow()
            self.db.commit()
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Failed to stop stream {stream_id}: {e}")
            stream.last_error = str(e)
            self.db.commit()
            return False

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
