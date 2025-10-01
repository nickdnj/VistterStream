"""
Timeline Executor - Executes composite streams with camera switching
Based on docs/StreamingPipeline-TechnicalSpec.md Timeline Orchestrator
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.timeline import Timeline, TimelineCue, TimelineExecution
from models.database import Camera
from services.ffmpeg_manager import FFmpegProcessManager, EncodingProfile
from models.schemas import StreamStatus

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable debug logging


class TimelineExecutor:
    """
    Executes timelines with camera switching for composite streams.
    
    Features:
    - Sequential cue execution (camera 1 → camera 2 → repeat)
    - FFmpeg process switching for each cue
    - Loop support for continuous streams
    - Graceful stop and cleanup
    """
    
    def __init__(self):
        self.active_timelines: Dict[int, asyncio.Task] = {}
        self.ffmpeg_managers: Dict[int, FFmpegProcessManager] = {}
        self._shutdown_event = asyncio.Event()
        
    async def start_timeline(
        self,
        timeline_id: int,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile] = None
    ) -> bool:
        """
        Start executing a timeline.
        
        Args:
            timeline_id: Timeline to execute
            output_urls: List of RTMP destinations
            encoding_profile: Encoding settings
            
        Returns:
            bool: Success status
        """
        if timeline_id in self.active_timelines:
            logger.warning(f"Timeline {timeline_id} is already running")
            return False
            
        # Create execution task
        task = asyncio.create_task(
            self._execute_timeline(timeline_id, output_urls, encoding_profile)
        )
        self.active_timelines[timeline_id] = task
        
        logger.info(f"Started timeline {timeline_id}")
        return True
        
    async def stop_timeline(self, timeline_id: int) -> bool:
        """Stop a running timeline"""
        if timeline_id not in self.active_timelines:
            logger.warning(f"Timeline {timeline_id} is not running")
            return False
            
        # Cancel the timeline task
        task = self.active_timelines[timeline_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        # Stop FFmpeg if running
        if timeline_id in self.ffmpeg_managers:
            ffmpeg_manager = self.ffmpeg_managers[timeline_id]
            try:
                await ffmpeg_manager.stop_stream(timeline_id)
            except Exception as e:
                logger.error(f"Error stopping FFmpeg for timeline {timeline_id}: {e}")
            del self.ffmpeg_managers[timeline_id]
            
        del self.active_timelines[timeline_id]
        logger.info(f"Stopped timeline {timeline_id}")
        return True
        
    async def _execute_timeline(
        self,
        timeline_id: int,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile]
    ):
        """
        Main timeline execution loop.
        
        This is the magic that switches between cameras!
        """
        db = SessionLocal()
        
        try:
            # Load timeline
            timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
            if not timeline:
                logger.error(f"Timeline {timeline_id} not found")
                return
                
            # Create execution record
            execution = TimelineExecution(
                timeline_id=timeline_id,
                started_at=datetime.utcnow(),
                status="running"
            )
            db.add(execution)
            db.commit()
            
            # Get video track cues (camera switching)
            video_track = next((t for t in timeline.tracks if t.track_type == "video"), None)
            if not video_track:
                logger.error(f"No video track found in timeline {timeline_id}")
                return
                
            cues = sorted(video_track.cues, key=lambda c: c.cue_order)
            if not cues:
                logger.error(f"No cues found in timeline {timeline_id}")
                return
                
            logger.info(f"Executing timeline {timeline.name} with {len(cues)} cues")
            
            # Initialize FFmpeg manager
            ffmpeg_manager = FFmpegProcessManager()
            await ffmpeg_manager.initialize()
            self.ffmpeg_managers[timeline_id] = ffmpeg_manager
            
            # Main execution loop
            loop_count = 0
            while not self._shutdown_event.is_set():
                loop_count += 1
                logger.info(f"Timeline {timeline.name} - Loop {loop_count}")
                
                # Execute each cue sequentially
                for idx, cue in enumerate(cues, 1):
                    if self._shutdown_event.is_set():
                        break
                    
                    logger.info(f"📋 Executing cue {idx}/{len(cues)} (ID: {cue.id})")
                    await self._execute_cue(
                        timeline_id,
                        cue,
                        ffmpeg_manager,
                        output_urls,
                        encoding_profile,
                        db
                    )
                    logger.info(f"✅ Cue {idx}/{len(cues)} completed\n")
                    
                # Check if we should loop
                if not timeline.loop:
                    logger.info(f"Timeline {timeline.name} completed (loop=False)")
                    break
                    
            # Mark execution as completed
            execution.completed_at = datetime.utcnow()
            execution.status = "completed"
            db.commit()
            
        except asyncio.CancelledError:
            logger.info(f"Timeline {timeline_id} execution cancelled")
            execution.status = "stopped"
            db.commit()
            raise
        except Exception as e:
            logger.error(f"Error executing timeline {timeline_id}: {e}")
            execution.status = "error"
            execution.error_message = str(e)
            db.commit()
        finally:
            db.close()
            
    async def _execute_cue(
        self,
        timeline_id: int,
        cue: TimelineCue,
        ffmpeg_manager: FFmpegProcessManager,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile],
        db: Session
    ):
        """Execute a single cue (camera switch)"""
        try:
            if cue.action_type == "show_camera":
                camera_id = cue.action_params.get("camera_id")
                if not camera_id:
                    logger.error(f"Cue {cue.id} has no camera_id")
                    return
                    
                # Get camera
                camera = db.query(Camera).filter(Camera.id == camera_id).first()
                if not camera:
                    logger.error(f"Camera {camera_id} not found")
                    return
                    
                # Build RTSP URL
                rtsp_url = self._build_rtsp_url(camera)
                logger.info(f"🎬 Switching to camera {camera.name} for {cue.duration}s")
                logger.debug(f"RTSP URL: {rtsp_url}")
                logger.debug(f"Output URLs: {output_urls}")
                
                # Stop existing stream if running
                try:
                    logger.debug(f"Stopping existing stream {timeline_id} if running...")
                    await ffmpeg_manager.stop_stream(timeline_id)
                except KeyError:
                    logger.debug(f"No existing stream to stop")
                    pass  # Not running yet
                except Exception as e:
                    logger.error(f"Error stopping stream: {e}")
                    traceback.print_exc()
                    
                # Start new stream with this camera
                logger.info(f"▶️  Starting FFmpeg stream {timeline_id} with camera {camera.name}")
                try:
                    await ffmpeg_manager.start_stream(
                        stream_id=timeline_id,
                        input_url=rtsp_url,
                        output_urls=output_urls,
                        profile=encoding_profile or EncodingProfile.reliability_profile(
                            ffmpeg_manager.hw_capabilities
                        )
                    )
                    logger.info(f"✅ FFmpeg stream {timeline_id} started successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to start FFmpeg stream {timeline_id}: {e}")
                    traceback.print_exc()
                    raise
                
                # Wait for cue duration
                logger.info(f"⏱️  Waiting {cue.duration}s for cue to complete...")
                await asyncio.sleep(cue.duration)
                logger.info(f"✅ Cue {cue.id} ({camera.name}) completed successfully")
                
            else:
                logger.warning(f"Unsupported action type: {cue.action_type}")
                
        except Exception as e:
            logger.error(f"❌ Error executing cue {cue.id}: {e}")
            traceback.print_exc()
            raise  # Re-raise the exception to stop timeline execution
            
    def _build_rtsp_url(self, camera: Camera) -> str:
        """Build RTSP URL for a camera"""
        import base64
        
        password = None
        if camera.password_enc:
            try:
                password = base64.b64decode(camera.password_enc).decode()
            except Exception:
                pass
                
        if camera.username and password:
            return f"rtsp://{camera.username}:{password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            return f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"


# Global instance
_timeline_executor: Optional[TimelineExecutor] = None


def get_timeline_executor() -> TimelineExecutor:
    """Get the global timeline executor instance"""
    global _timeline_executor
    if _timeline_executor is None:
        _timeline_executor = TimelineExecutor()
    return _timeline_executor

