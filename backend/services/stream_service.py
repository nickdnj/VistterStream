"""
Stream service for managing streaming operations
"""

import logging
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from urllib.parse import quote

from models.database import Stream, Camera
from utils.crypto import decrypt
from utils.log_utils import redact_url
from models.destination import StreamingDestination
from models.schemas import StreamCreate, StreamUpdate, Stream as StreamSchema, StreamStatus
from services.ffmpeg_manager import FFmpegProcessManager

logger = logging.getLogger(__name__)

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

        update_data = stream_update.model_dump(exclude_unset=True)
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
            password = decrypt(camera.password_enc)

        # URL-encode credentials to handle special characters like !, @, #
        if camera.username and password:
            encoded_username = quote(camera.username, safe='')
            encoded_password = quote(password, safe='')
            return f"rtsp://{encoded_username}:{encoded_password}@{camera.address}:{camera.port}{camera.stream_path}"
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
                logger.info("Moving camera %s to preset '%s' before streaming", camera.name, preset.name)

                # Get camera password
                password = None
                if camera.password_enc:
                    password = decrypt(camera.password_enc)

                if password:
                    # Use configured ONVIF port for PTZ control
                    ptz_service = get_ptz_service()
                    pan = preset.pan if preset.pan is not None else 0.0
                    tilt = preset.tilt if preset.tilt is not None else 0.0
                    zoom = preset.zoom if preset.zoom is not None else 1.0

                    try:
                        success = await ptz_service.move_to_preset(
                            address=camera.address,
                            port=camera.onvif_port,
                            username=camera.username,
                            password=password,
                            preset_token=preset.camera_preset_token or str(stream.preset_id),
                            pan=pan,
                            tilt=tilt,
                            zoom=zoom,
                        )

                        if success:
                            logger.info(
                                "Camera moved to preset '%s' (pan=%s, tilt=%s, zoom=%s), "
                                "waiting 3 seconds for camera to settle...",
                                preset.name, pan, tilt, zoom
                            )
                            await asyncio.sleep(3)  # Wait for camera to settle
                        else:
                            logger.warning("Failed to move camera to preset, streaming anyway")
                    except Exception as e:
                        logger.error("Error moving camera to preset: %s", e)
                        # Continue anyway - don't fail the stream
                else:
                    logger.warning("No camera credentials available for PTZ control")
            else:
                logger.warning("Preset %d not found", stream.preset_id)

        # Update stream status
        stream.status = StreamStatus.STARTING.value
        stream.started_at = datetime.now(timezone.utc)
        stream.last_error = None
        self.db.commit()

        try:
            # Build RTSP input URL
            rtsp_url = self._build_rtsp_url(camera)

            # Build RTMP output URL from destination
            rtmp_output = destination.get_full_rtmp_url()

            # Mark destination as used
            destination.last_used = datetime.now(timezone.utc)
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
            logger.info("Starting stream %d from %s to %s",
                        stream.id, redact_url(rtsp_url), redact_url(rtmp_output))
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

            logger.info("Stream %d started successfully", stream.id)
            return True

        except Exception as e:
            logger.error("Failed to start stream %d: %s", stream.id, e)
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
                logger.info("Stopped stream %d via FFmpeg manager", stream_id)
            except KeyError:
                # Stream not tracked by FFmpeg manager (likely server was restarted)
                # Kill orphaned FFmpeg processes manually
                logger.info("Stream %d not in FFmpeg manager, searching for orphaned processes...", stream_id)

                # Get the destination to build the output URL
                destination = self.db.query(StreamingDestination).filter(
                    StreamingDestination.id == stream.destination_id
                ).first()
                if destination:
                    rtmp_output = destination.get_full_rtmp_url()
                else:
                    logger.warning("Destination not found for stream %d, cannot search for orphaned processes", stream_id)
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
                            logger.info("Found %d orphaned FFmpeg process(es) for stream %d: %s",
                                        len(pids), stream_id, pids)

                            # Kill each process
                            for pid in pids:
                                try:
                                    import os
                                    os.kill(int(pid), signal.SIGTERM)
                                    logger.info("Killed orphaned FFmpeg process %s", pid)
                                except ProcessLookupError:
                                    logger.debug("Process %s already terminated", pid)
                                except Exception as e:
                                    logger.error("Failed to kill process %s: %s", pid, e)
                        else:
                            logger.debug("No orphaned FFmpeg processes found for stream %d", stream_id)

                    except Exception as e:
                        logger.error("Failed to search for orphaned processes: %s", e)

            # Update stream status
            stream.status = StreamStatus.STOPPED.value
            stream.stopped_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.info("Stream %d stopped successfully", stream_id)
            return True

        except Exception as e:
            logger.error("Failed to stop stream %d: %s", stream_id, e, exc_info=True)
            stream.last_error = str(e)
            self.db.commit()
            return False

    async def get_stream_status(self, stream_id: int) -> Optional[dict]:
        """Get stream status"""
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return None

        # Use naive UTC — SQLite strips timezone info from stored datetimes
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
