"""
Timeline Executor - Executes composite streams with camera switching
Based on docs/StreamingPipeline-TechnicalSpec.md Timeline Orchestrator
"""

import asyncio
import logging
import traceback
import tempfile
import os
import httpx
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

from models.database import SessionLocal, Asset
from models.timeline import Timeline, TimelineCue, TimelineExecution, TimelineTrack
from models.database import Camera, Preset
from services.ffmpeg_manager import FFmpegProcessManager, EncodingProfile
from services.ptz_service import get_ptz_service
from models.schemas import StreamStatus
import base64

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
        # Track current playback position for each timeline
        self.playback_positions: Dict[int, dict] = {}  # timeline_id -> {current_time, current_cue_id, loop_count}
        self._position_update_tasks: Dict[int, asyncio.Task] = {}  # Tasks for position updates
        
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
            
            # Main execution loop (segment-based: overlays can change mid-cue)
            loop_count = 0
            last_camera_id: Optional[int] = None
            last_preset_id: Optional[int] = None
            while not self._shutdown_event.is_set():
                loop_count += 1
                logger.info(f"Timeline {timeline.name} - Loop {loop_count}")

                # Compute segment boundaries as union of all cue boundaries across enabled tracks
                segments = self._compute_segments(timeline)
                logger.debug(f"Computed {len(segments)} segments from track boundaries")

                for seg_index, (seg_start, seg_end) in enumerate(segments):
                    if self._shutdown_event.is_set():
                        break

                    duration = max(0.0, seg_end - seg_start)
                    if duration <= 0.0:
                        continue

                    # Determine active video cue at segment start
                    active_video_cues = [
                        c for c in cues
                        if seg_start >= c.start_time and seg_start < (c.start_time + c.duration)
                    ]
                    if not active_video_cues:
                        logger.debug(f"No active video cue at t={seg_start:.2f}s, skipping segment")
                        continue

                    video_cue = active_video_cues[0]  # single video track expected
                    logger.info(f"📋 Segment {seg_index+1}/{len(segments)} at t={seg_start:.2f}s for {duration:.2f}s (video cue ID: {video_cue.id})")

                    # Start continuous position updates for this segment
                    update_task = asyncio.create_task(
                        self._update_position_during_segment(
                            timeline_id=timeline_id,
                            start_time=seg_start,
                            duration=duration,
                            current_cue_id=video_cue.id,
                            current_cue_index=video_cue.cue_order,
                            total_cues=len(cues),
                            loop_count=loop_count,
                        )
                    )
                    self._position_update_tasks[timeline_id] = update_task

                    # Execute this segment with current video and overlays
                    await self._execute_segment(
                        timeline_id=timeline_id,
                        seg_start=seg_start,
                        duration=duration,
                        video_cue=video_cue,
                        ffmpeg_manager=ffmpeg_manager,
                        output_urls=output_urls,
                        encoding_profile=encoding_profile,
                        db=db,
                        last_camera_preset=(last_camera_id, last_preset_id)
                    )

                    # Cancel position updates
                    if timeline_id in self._position_update_tasks:
                        self._position_update_tasks[timeline_id].cancel()
                        try:
                            await self._position_update_tasks[timeline_id]
                        except asyncio.CancelledError:
                            pass

                    # Track last camera/preset to avoid redundant PTZ moves
                    last_camera_id = video_cue.action_params.get("camera_id")
                    last_preset_id = video_cue.action_params.get("preset_id")

                if not timeline.loop:
                    logger.info(f"Timeline {timeline.name} completed (loop=False)")
                    break
                    
            # Mark execution as completed
            execution.completed_at = datetime.utcnow()
            execution.status = "completed"
            db.commit()
            
        except asyncio.CancelledError:
            logger.info(f"Timeline {timeline_id} execution cancelled")
            # Clear playback position
            if timeline_id in self.playback_positions:
                del self.playback_positions[timeline_id]
            try:
                # Try to update execution status, but don't fail if object is deleted
                db.refresh(execution)
                execution.status = "stopped"
                db.commit()
            except Exception as db_error:
                logger.warning(f"Could not update execution status (already deleted?): {db_error}")
                db.rollback()
            raise
        except Exception as e:
            logger.error(f"Error executing timeline {timeline_id}: {e}")
            # Clear playback position
            if timeline_id in self.playback_positions:
                del self.playback_positions[timeline_id]
            try:
                db.refresh(execution)
                execution.status = "error"
                execution.error_message = str(e)
                db.commit()
            except Exception as db_error:
                logger.warning(f"Could not update execution status: {db_error}")
                db.rollback()
        finally:
            db.close()
            
    def _get_active_cues_at_time(self, timeline: Timeline, current_time: float) -> Dict[str, List[TimelineCue]]:
        """Get all active cues at a specific time, grouped by track type"""
        active_cues = {'video': [], 'overlay': [], 'audio': []}
        
        for track in timeline.tracks:
            if not track.is_enabled:
                continue
                
            for cue in track.cues:
                cue_start = cue.start_time
                cue_end = cue.start_time + cue.duration
                
                if current_time >= cue_start and current_time < cue_end:
                    active_cues[track.track_type].append(cue)
        
        return active_cues

    def _compute_segments(self, timeline: Timeline) -> List[Tuple[float, float]]:
        """Compute contiguous time segments from union of all cue boundaries across enabled tracks."""
        boundaries: List[float] = [0.0, timeline.duration]
        for track in timeline.tracks:
            if not track.is_enabled:
                continue
            for cue in track.cues:
                boundaries.append(float(cue.start_time))
                boundaries.append(float(cue.start_time + cue.duration))
        # Unique and sort within [0, duration]
        uniq = sorted(set(t for t in boundaries if t >= 0.0 and t <= timeline.duration))
        segments: List[Tuple[float, float]] = []
        for i in range(len(uniq) - 1):
            start = uniq[i]
            end = uniq[i + 1]
            if end - start > 0.0:
                segments.append((start, end))
        return segments
    
    async def _download_asset_image(self, asset: Asset) -> Optional[str]:
        """Download an asset image to a temp file. Returns temp file path or None."""
        try:
            if asset.type == 'api_image' and asset.api_url:
                # Download from API
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(asset.api_url)
                    if response.status_code == 200:
                        # Create temp file
                        suffix = '.png' if 'png' in response.headers.get('content-type', '') else '.jpg'
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                            tmp.write(response.content)
                            logger.info(f"📥 Downloaded API image for asset '{asset.name}' to {tmp.name}")
                            return tmp.name
            elif asset.type == 'static_image' and asset.file_path:
                # Convert URL path to filesystem path if needed
                file_path = asset.file_path
                if file_path.startswith('/uploads/'):
                    # Convert URL path to filesystem path
                    from pathlib import Path
                    backend_dir = Path(__file__).parent.parent
                    file_path = str(backend_dir / file_path.lstrip('/'))
                
                if os.path.exists(file_path):
                    logger.info(f"📁 Using local image for asset '{asset.name}': {file_path}")
                    return file_path
                else:
                    logger.warning(f"⚠️  File not found for asset '{asset.name}': {file_path}")
        except Exception as e:
            logger.error(f"Failed to download asset {asset.id}: {e}")
        
        return None
    
    async def _execute_segment(
        self,
        timeline_id: int,
        seg_start: float,
        duration: float,
        video_cue: TimelineCue,
        ffmpeg_manager: FFmpegProcessManager,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile],
        db: Session,
        last_camera_preset: Tuple[Optional[int], Optional[int]]
    ):
        """Execute a single time segment with current video and overlays.

        Overlays are sampled at segment start and applied for the whole segment.
        """
        try:
            if video_cue.action_type == "show_camera":
                camera_id = video_cue.action_params.get("camera_id")
                preset_id = video_cue.action_params.get("preset_id")  # Optional
                
                if not camera_id:
                    logger.error(f"Cue {video_cue.id} has no camera_id")
                    return
                    
                # Get camera
                camera = db.query(Camera).filter(Camera.id == camera_id).first()
                if not camera:
                    logger.error(f"Camera {camera_id} not found")
                    return
                
                # If preset specified, move camera to preset BEFORE streaming
                if preset_id:
                    preset = db.query(Preset).filter(Preset.id == preset_id).first()
                    if preset:
                        # Avoid redundant PTZ if unchanged since last segment
                        if (last_camera_preset[0] != camera_id) or (last_camera_preset[1] != preset_id):
                            logger.info(f"🎯 Moving camera {camera.name} to preset '{preset.name}'")
                        
                        # Get camera credentials
                        password = None
                        if camera.password_enc:
                            try:
                                password = base64.b64decode(camera.password_enc).decode()
                            except Exception as e:
                                logger.error(f"Failed to decode camera password: {e}")
                        
                        if password and ((last_camera_preset[0] != camera_id) or (last_camera_preset[1] != preset_id)):
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
                                    preset_token=preset.camera_preset_token or str(preset_id),
                                    pan=pan,
                                    tilt=tilt,
                                    zoom=zoom,
                                )
                               
                                if success:
                                    logger.info(
                                        "✅ Camera moved to preset '%s' (pan=%s, tilt=%s, zoom=%s)",
                                        preset.name,
                                        pan,
                                        tilt,
                                        zoom,
                                    )
                                    # Wait a moment for camera to settle
                                    await asyncio.sleep(2)
                                else:
                                    logger.warning(f"⚠️  Failed to move camera to preset, continuing anyway")
                            except Exception as e:
                                logger.error(f"❌ Error moving camera to preset: {e}")
                                # Continue anyway - don't fail the whole timeline
                        else:
                            logger.warning(f"⚠️  No camera credentials available for PTZ control")
                    else:
                        logger.warning(f"⚠️  Preset {preset_id} not found, ignoring")
                    
                # Build RTSP URL
                rtsp_url = self._build_rtsp_url(camera)
                preset_info = f" at preset '{preset.name}'" if preset_id and preset else ""
                logger.info(f"🎬 Segment streaming from camera {camera.name}{preset_info} for {duration}s")
                logger.debug(f"RTSP URL: {rtsp_url}")
                logger.debug(f"Output URLs: {output_urls}")
                
                # Get the timeline to find overlay cues at this time
                timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
                active_cues = self._get_active_cues_at_time(timeline, seg_start)
                
                # Process overlay cues
                overlay_images = []
                temp_files = []
                
                if active_cues['overlay']:
                    logger.info(f"🎨 Found {len(active_cues['overlay'])} overlay cue(s) at time {seg_start}")
                    
                    for overlay_cue in active_cues['overlay']:
                        asset_id = overlay_cue.action_params.get('asset_id')
                        if not asset_id:
                            continue
                        
                        # Get asset from database
                        asset = db.query(Asset).filter(Asset.id == asset_id).first()
                        if not asset or not asset.is_active:
                            logger.warning(f"Asset {asset_id} not found or inactive")
                            continue
                        
                        # Download/get asset image
                        image_path = await self._download_asset_image(asset)
                        if not image_path:
                            logger.warning(f"Failed to get image for asset {asset.name}")
                            continue
                        
                        # Track temp files for cleanup
                        if image_path.startswith('/tmp/') or image_path.startswith(tempfile.gettempdir()):
                            temp_files.append(image_path)
                        
                        # Calculate pixel positions from normalized coordinates (0-1 range)
                        # Asset stores position as 0-1, FFmpeg needs pixels
                        # Assuming 1920x1080 output
                        x_pixels = int(asset.position_x * 1920)
                        y_pixels = int(asset.position_y * 1080)
                        
                        overlay_data = {
                            'path': image_path,
                            'x': x_pixels,
                            'y': y_pixels,
                            'opacity': asset.opacity
                        }
                        
                        # Add dimensions if specified
                        if asset.width:
                            overlay_data['width'] = asset.width
                        if asset.height:
                            overlay_data['height'] = asset.height
                        
                        overlay_images.append(overlay_data)
                        
                        size_info = ""
                        if asset.width or asset.height:
                            w = f"{asset.width}px" if asset.width else "auto"
                            h = f"{asset.height}px" if asset.height else "auto"
                            size_info = f" size={w}x{h}"
                        logger.info(f"  🖼️  {asset.name} at ({x_pixels}, {y_pixels}) opacity={asset.opacity}{size_info}")
                
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
                    
                # Start new stream with this camera and overlays
                overlay_info = f" with {len(overlay_images)} overlay(s)" if overlay_images else ""
                logger.info(f"▶️  Starting FFmpeg stream {timeline_id} with camera {camera.name}{overlay_info}")
                try:
                    await ffmpeg_manager.start_stream(
                        stream_id=timeline_id,
                        input_url=rtsp_url,
                        output_urls=output_urls,
                        profile=encoding_profile or EncodingProfile.reliability_profile(
                            ffmpeg_manager.hw_capabilities
                        ),
                        overlay_images=overlay_images if overlay_images else None
                    )
                    logger.info(f"✅ FFmpeg stream {timeline_id} started successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to start FFmpeg stream {timeline_id}: {e}")
                    traceback.print_exc()
                    # Clean up temp files
                    for temp_file in temp_files:
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                    raise
                
                # Wait for cue duration
                logger.info(f"⏱️  Waiting {duration}s for segment to complete...")
                await asyncio.sleep(duration)
                logger.info(f"✅ Segment at t={seg_start:.2f}s ({camera.name}) completed successfully")
                
                # Clean up temp files after cue completes
                for temp_file in temp_files:
                    try:
                        os.unlink(temp_file)
                        logger.debug(f"🗑️  Cleaned up temp file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
                
            else:
                logger.warning("Unsupported action type for video cue")
                
        except Exception as e:
            logger.error(f"❌ Error executing segment at t={seg_start:.2f}s: {e}")
            traceback.print_exc()
            raise  # Re-raise the exception to stop timeline execution
            
    async def _update_position_during_cue(
        self,
        timeline_id: int,
        cue: TimelineCue,
        cue_index: int,
        total_cues: int,
        loop_count: int,
        duration: float
    ):
        """Continuously update playback position during cue execution"""
        start_time = datetime.utcnow()
        
        try:
            while True:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                current_time = cue.start_time + min(elapsed, duration)
                
                self.playback_positions[timeline_id] = {
                    "current_time": current_time,
                    "current_cue_id": cue.id,
                    "current_cue_index": cue_index,
                    "loop_count": loop_count,
                    "total_cues": total_cues,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                await asyncio.sleep(0.5)  # Update every 500ms
                
        except asyncio.CancelledError:
            pass

    async def _update_position_during_segment(
        self,
        timeline_id: int,
        start_time: float,
        duration: float,
        current_cue_id: int,
        current_cue_index: int,
        total_cues: int,
        loop_count: int,
    ):
        """Continuously update playback position during a segment.

        Mirrors the cue-based updater but uses an explicit start_time/duration.
        """
        seg_start = datetime.utcnow()
        try:
            while True:
                elapsed = (datetime.utcnow() - seg_start).total_seconds()
                current_time = start_time + min(elapsed, duration)
                self.playback_positions[timeline_id] = {
                    "current_time": current_time,
                    "current_cue_id": current_cue_id,
                    "current_cue_index": current_cue_index,
                    "loop_count": loop_count,
                    "total_cues": total_cues,
                    "updated_at": datetime.utcnow().isoformat()
                }
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
    
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


def get_playback_position(timeline_id: int) -> Optional[dict]:
    """Get current playback position for a timeline"""
    executor = get_timeline_executor()
    return executor.playback_positions.get(timeline_id)
