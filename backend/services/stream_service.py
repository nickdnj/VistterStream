"""
Stream service for managing live streams to platforms (YouTube, Facebook, Twitch)
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import base64

from models.database import Stream as StreamDB, Camera
from models.schemas import (
    StreamCreate, StreamUpdate, Stream as StreamSchema,
    StreamStatus, EncodingProfileSchema
)
from services.ffmpeg_manager import FFmpegProcessManager
from services.hardware_detector import get_hardware_capabilities


class StreamService:
    def __init__(self, db: Session):
        self.db = db
        self.ffmpeg_manager = FFmpegProcessManager()
        
    async def get_all_streams(self) -> List[StreamSchema]:
        """Get all streams"""
        streams = self.db.query(StreamDB).all()
        return [StreamSchema.from_orm(stream) for stream in streams]
    
    async def get_stream(self, stream_id: int) -> Optional[StreamSchema]:
        """Get a specific stream"""
        stream = self.db.query(StreamDB).filter(StreamDB.id == stream_id).first()
        if not stream:
            return None
        return StreamSchema.from_orm(stream)
    
    async def create_stream(self, stream_data: StreamCreate) -> StreamSchema:
        """Create a new stream configuration"""
        # Verify camera exists
        camera = self.db.query(Camera).filter(Camera.id == stream_data.camera_id).first()
        if not camera:
            raise ValueError(f"Camera {stream_data.camera_id} not found")
        
        stream = StreamDB(
            camera_id=stream_data.camera_id,
            destination=stream_data.destination.value,
            stream_key=stream_data.stream_key,
            rtmp_url=stream_data.rtmp_url,
            status=StreamStatus.STOPPED.value
        )
        
        self.db.add(stream)
        self.db.commit()
        self.db.refresh(stream)
        
        return StreamSchema.from_orm(stream)
    
    async def update_stream(self, stream_id: int, stream_update: StreamUpdate) -> Optional[StreamSchema]:
        """Update stream configuration"""
        stream = self.db.query(StreamDB).filter(StreamDB.id == stream_id).first()
        if not stream:
            return None
        
        if stream_update.destination:
            stream.destination = stream_update.destination.value
        if stream_update.stream_key:
            stream.stream_key = stream_update.stream_key
        if stream_update.rtmp_url:
            stream.rtmp_url = stream_update.rtmp_url
        
        self.db.commit()
        self.db.refresh(stream)
        
        return StreamSchema.from_orm(stream)
    
    async def delete_stream(self, stream_id: int) -> bool:
        """Delete a stream (must be stopped first)"""
        stream = self.db.query(StreamDB).filter(StreamDB.id == stream_id).first()
        if not stream:
            return False
        
        # Stop stream if running
        if stream.status in [StreamStatus.STARTING.value, StreamStatus.RUNNING.value]:
            await self.stop_stream(stream_id)
        
        self.db.delete(stream)
        self.db.commit()
        
        return True
    
    async def start_stream(self, stream_id: int, encoding_profile: Optional[EncodingProfileSchema] = None) -> Dict:
        """Start a stream"""
        stream = self.db.query(StreamDB).filter(StreamDB.id == stream_id).first()
        if not stream:
            return {"success": False, "message": "Stream not found"}
        
        # Check if already running
        if stream.status == StreamStatus.RUNNING.value:
            return {"success": False, "message": "Stream already running"}
        
        # Get camera
        camera = stream.camera
        if not camera:
            return {"success": False, "message": "Camera not found"}
        
        # Build RTSP input URL
        password = None
        if camera.password_enc:
            password = base64.b64decode(camera.password_enc).decode()
        
        if camera.username and password:
            rtsp_url = f"rtsp://{camera.username}:{password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            rtsp_url = f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"
        
        # Use default encoding profile if not provided
        if not encoding_profile:
            encoding_profile = self._get_default_encoding_profile()
        
        # Build RTMP output URL
        rtmp_output = f"{stream.rtmp_url}/{stream.stream_key}"
        
        # Update stream status
        stream.status = StreamStatus.STARTING.value
        stream.started_at = datetime.utcnow()
        stream.error_message = None
        self.db.commit()
        
        try:
            # Start FFmpeg process
            success = await self.ffmpeg_manager.start_stream(
                stream_id=stream.id,
                input_url=rtsp_url,
                output_url=rtmp_output,
                profile=encoding_profile
            )
            
            if success:
                stream.status = StreamStatus.RUNNING.value
                self.db.commit()
                return {"success": True, "message": f"Stream started to {stream.destination}"}
            else:
                stream.status = StreamStatus.ERROR.value
                stream.error_message = "Failed to start FFmpeg process"
                self.db.commit()
                return {"success": False, "message": "Failed to start stream"}
        
        except Exception as e:
            stream.status = StreamStatus.ERROR.value
            stream.error_message = str(e)
            self.db.commit()
            return {"success": False, "message": f"Error starting stream: {str(e)}"}
    
    async def stop_stream(self, stream_id: int) -> Dict:
        """Stop a running stream"""
        stream = self.db.query(StreamDB).filter(StreamDB.id == stream_id).first()
        if not stream:
            return {"success": False, "message": "Stream not found"}
        
        # Check if stream is running
        if stream.status == StreamStatus.STOPPED.value:
            return {"success": False, "message": "Stream already stopped"}
        
        try:
            # Stop FFmpeg process
            await self.ffmpeg_manager.stop_stream(stream_id)
            
            # Update stream status
            stream.status = StreamStatus.STOPPED.value
            stream.stopped_at = datetime.utcnow()
            self.db.commit()
            
            return {"success": True, "message": "Stream stopped"}
        
        except Exception as e:
            return {"success": False, "message": f"Error stopping stream: {str(e)}"}
    
    async def get_stream_status(self, stream_id: int) -> Optional[Dict]:
        """Get real-time stream status and metrics"""
        stream = self.db.query(StreamDB).filter(StreamDB.id == stream_id).first()
        if not stream:
            return None
        
        # Get process status from FFmpeg manager
        process_status = self.ffmpeg_manager.get_process_status(stream_id)
        
        return {
            "id": stream.id,
            "camera_id": stream.camera_id,
            "destination": stream.destination,
            "status": stream.status,
            "started_at": stream.started_at.isoformat() if stream.started_at else None,
            "stopped_at": stream.stopped_at.isoformat() if stream.stopped_at else None,
            "error_message": stream.error_message,
            "metrics": process_status.metrics.dict() if process_status else None,
            "retry_count": process_status.retry_count if process_status else 0
        }
    
    def _get_default_encoding_profile(self) -> EncodingProfileSchema:
        """Get default encoding profile based on hardware capabilities"""
        hw_caps = get_hardware_capabilities()
        
        return EncodingProfileSchema(
            codec=hw_caps.encoder,
            resolution=(1920, 1080),
            framerate=30,
            bitrate="4500k",
            keyframe_interval=2,
            buffer_size="9000k",
            preset="fast",
            profile="main",
            level="4.1"
        )
    
    def _get_youtube_encoding_profile(self) -> EncodingProfileSchema:
        """Get YouTube-optimized encoding profile"""
        hw_caps = get_hardware_capabilities()
        
        # YouTube recommendations: 1080p @ 30fps = 4.5-9 Mbps
        return EncodingProfileSchema(
            codec=hw_caps.encoder,
            resolution=(1920, 1080),
            framerate=30,
            bitrate="6000k",  # 6 Mbps for good quality
            keyframe_interval=2,  # Keyframe every 2 seconds
            buffer_size="12000k",
            preset="fast",
            profile="high",  # YouTube supports high profile
            level="4.2"
        )
