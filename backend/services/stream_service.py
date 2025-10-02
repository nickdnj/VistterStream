"""
Stream service for managing streaming operations
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import base64

from models.database import Stream, Camera
from models.destination import StreamingDestination
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
            destination_id=stream_data.destination_id,
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
        
        # Get the destination
        destination = self.db.query(StreamingDestination).filter(
            StreamingDestination.id == stream.destination_id
        ).first()
        if not destination:
            stream.last_error = "Destination not found"
            stream.status = StreamStatus.ERROR.value
            self.db.commit()
            return False
        
        # If stream has a preset, move camera to preset BEFORE streaming
        if stream.preset_id:
            from models.database import Preset
            from services.ptz_service import get_ptz_service
            import asyncio
            
            preset = self.db.query(Preset).filter(Preset.id == stream.preset_id).first()
            if preset:
                print(f"🎯 Moving camera {camera.name} to preset '{preset.name}' before streaming")
                
                # Get camera password
                password = None
                if camera.password_enc:
                    password = base64.b64decode(camera.password_enc).decode()
                
                if password:
                    # Use configured ONVIF port for PTZ control
                    ptz_service = get_ptz_service()
                    
                    try:
                        success = await ptz_service.move_to_preset(
                            address=camera.address,
                            port=camera.onvif_port,
                            username=camera.username,
                            password=password,
                            preset_token=str(stream.preset_id)
                        )
                        
                        if success:
                            print(f"✅ Camera moved to preset '{preset.name}', waiting 3 seconds for camera to settle...")
                            await asyncio.sleep(3)  # Wait for camera to settle
                        else:
                            print(f"⚠️  Failed to move camera to preset, streaming anyway")
                    except Exception as e:
                        print(f"❌ Error moving camera to preset: {e}")
                        # Continue anyway - don't fail the stream
                else:
                    print(f"⚠️  No camera credentials available for PTZ control")
            else:
                print(f"⚠️  Preset {stream.preset_id} not found")
        
        # Update stream status
        stream.status = StreamStatus.STARTING.value
        stream.started_at = datetime.utcnow()
        stream.last_error = None
        self.db.commit()
        
        try:
            # Build RTSP input URL
            rtsp_url = self._build_rtsp_url(camera)
            
            # Build RTMP output URL from destination
            rtmp_output = destination.get_full_rtmp_url()
            
            # Mark destination as used
            destination.last_used = datetime.utcnow()
            self.db.commit()
            
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
            from services.ffmpeg_manager import EncodingProfile
            profile = EncodingProfile(**encoding_profile)
            await ffmpeg_manager.start_stream(
                stream_id=stream.id,
                input_url=rtsp_url,
                output_urls=[rtmp_output],  # List of output URLs
                profile=profile
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
        import subprocess
        import signal
        
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False
        
        try:
            # Get FFmpeg manager and stop process
            ffmpeg_manager = await self.get_ffmpeg_manager()
            
            try:
                await ffmpeg_manager.stop_stream(stream_id)
                print(f"DEBUG: Stopped stream {stream_id} via FFmpeg manager")
            except KeyError:
                # Stream not tracked by FFmpeg manager (likely server was restarted)
                # Kill orphaned FFmpeg processes manually
                print(f"DEBUG: Stream {stream_id} not in FFmpeg manager, searching for orphaned processes...")
                
                # Get the destination to build the output URL
                destination = self.db.query(StreamingDestination).filter(
                    StreamingDestination.id == stream.destination_id
                ).first()
                if destination:
                    rtmp_output = destination.get_full_rtmp_url()
                else:
                    print(f"DEBUG: Destination not found for stream {stream_id}, cannot search for orphaned processes")
                    rtmp_output = None
                
                if rtmp_output:
                    # Find FFmpeg processes with this output URL
                    try:
                        result = subprocess.run(
                            ['pgrep', '-f', f'ffmpeg.*{rtmp_output}'],
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0 and result.stdout.strip():
                            pids = result.stdout.strip().split('\n')
                            print(f"DEBUG: Found {len(pids)} orphaned FFmpeg process(es) for stream {stream_id}: {pids}")
                            
                            # Kill each process
                            for pid in pids:
                                try:
                                    import os
                                    os.kill(int(pid), signal.SIGTERM)
                                    print(f"DEBUG: Killed orphaned FFmpeg process {pid}")
                                except ProcessLookupError:
                                    print(f"DEBUG: Process {pid} already terminated")
                                except Exception as e:
                                    print(f"DEBUG: Failed to kill process {pid}: {e}")
                        else:
                            print(f"DEBUG: No orphaned FFmpeg processes found for stream {stream_id}")
                            
                    except Exception as e:
                        print(f"DEBUG: Failed to search for orphaned processes: {e}")
            
            # Update stream status
            stream.status = StreamStatus.STOPPED.value
            stream.stopped_at = datetime.utcnow()
            self.db.commit()
            
            print(f"DEBUG: Stream {stream_id} stopped successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: Failed to stop stream {stream_id}: {e}")
            import traceback
            traceback.print_exc()
            stream.last_error = str(e)
            self.db.commit()
            return False

    async def get_stream_status(self, stream_id: int) -> Optional[dict]:
        """Get stream status"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return None

        now = datetime.utcnow()
        if stream.started_at:
            end_time = stream.stopped_at or now
            uptime_seconds = max(int((end_time - stream.started_at).total_seconds()), 0)
        else:
            uptime_seconds = 0

        # Get destination details
        destination = self.db.query(StreamingDestination).filter(
            StreamingDestination.id == stream.destination_id
        ).first()
        
        return {
            "id": stream.id,
            "name": stream.name,
            "camera_id": stream.camera_id,
            "destination_id": stream.destination_id,
            "destination": {
                "id": destination.id,
                "name": destination.name,
                "platform": destination.platform
            } if destination else None,
            "status": stream.status,
            "is_active": stream.is_active,
            "created_at": stream.created_at,
            "started_at": stream.started_at,
            "stopped_at": stream.stopped_at,
            "last_error": stream.last_error,
            "resolution": stream.resolution,
            "bitrate": stream.bitrate,
            "framerate": stream.framerate,
            "is_live": stream.status == StreamStatus.RUNNING.value,
            "uptime_seconds": uptime_seconds
        }
