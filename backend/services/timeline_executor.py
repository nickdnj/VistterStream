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
from services.ffmpeg_manager import FFmpegProcessManager, EncodingProfile, StreamStatus
from services.ptz_service import get_ptz_service
from utils.google_drive import parse_google_drawing_url
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
        # Track destination names for each active timeline
        self.timeline_destinations: Dict[int, List[str]] = {}  # timeline_id -> [destination names]
        # Track destination IDs for each active timeline (for auto-selection in UI)
        self.timeline_destination_ids: Dict[int, List[int]] = {}  # timeline_id -> [destination IDs]
        # Track last segment completion time for stall detection
        self._last_segment_time: Dict[int, datetime] = {}  # timeline_id -> last segment completion time
        
    async def start_timeline(
        self,
        timeline_id: int,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile] = None,
        destination_names: Optional[List[str]] = None,
        destination_ids: Optional[List[int]] = None,
        start_position: Optional[float] = None
    ) -> bool:
        """
        Start executing a timeline.
        
        Args:
            timeline_id: Timeline to execute
            output_urls: List of RTMP destinations
            encoding_profile: Encoding settings
            destination_names: Names of the destinations for display
            destination_ids: IDs of the destinations for UI auto-selection
            start_position: Start from this time offset in seconds (for jump-to feature)
            
        Returns:
            bool: Success status
        """
        if timeline_id in self.active_timelines:
            logger.warning(f"Timeline {timeline_id} is already running")
            return False
            
        # Store destination names for status display
        if destination_names:
            self.timeline_destinations[timeline_id] = destination_names
        
        # Store destination IDs for UI auto-selection
        if destination_ids:
            self.timeline_destination_ids[timeline_id] = destination_ids
            
        # Initialize heartbeat for stall detection
        self._last_segment_time[timeline_id] = datetime.utcnow()
        
        # Create execution task
        task = asyncio.create_task(
            self._execute_timeline(timeline_id, output_urls, encoding_profile, start_position)
        )
        self.active_timelines[timeline_id] = task
        
        start_info = f" from {start_position}s" if start_position else ""
        logger.info(f"Started timeline {timeline_id}{start_info}")
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
            
        # Clean up destination names and IDs
        if timeline_id in self.timeline_destinations:
            del self.timeline_destinations[timeline_id]
        if timeline_id in self.timeline_destination_ids:
            del self.timeline_destination_ids[timeline_id]
        if timeline_id in self._last_segment_time:
            del self._last_segment_time[timeline_id]
            
        # Notify watchdog manager that stream is stopping
        try:
            from services.watchdog_manager import get_watchdog_manager
            watchdog_manager = get_watchdog_manager()
            await watchdog_manager.notify_stream_stopped(timeline_id)
            logger.info(f"🐕 Notified watchdog manager: stream {timeline_id} stopped")
        except Exception as e:
            logger.warning(f"Failed to notify watchdog manager: {e}")
        
        # Stop FFmpeg if running
        if timeline_id in self.ffmpeg_managers:
            ffmpeg_manager = self.ffmpeg_managers[timeline_id]
            try:
                # Unregister callback before stopping
                ffmpeg_manager.unregister_stream_died_callback(timeline_id)
                await ffmpeg_manager.stop_stream(timeline_id)
            except Exception as e:
                logger.error(f"Error stopping FFmpeg for timeline {timeline_id}: {e}")
            del self.ffmpeg_managers[timeline_id]
            
        del self.active_timelines[timeline_id]
        logger.info(f"Stopped timeline {timeline_id}")
        return True
    
    async def _on_ffmpeg_died(self, stream_id: int, error_msg: str):
        """
        Callback when FFmpeg process dies unexpectedly.
        This updates the timeline state so status endpoints reflect reality.
        """
        logger.error(f"💀 FFmpeg died for timeline {stream_id}: {error_msg}")
        
        # Update playback position to indicate error
        if stream_id in self.playback_positions:
            self.playback_positions[stream_id]["status"] = "error"
            self.playback_positions[stream_id]["error"] = error_msg
        
        # Note: We don't cancel the timeline task here because the watchdog
        # should handle recovery. If watchdog is disabled, the timeline
        # will eventually error out when it tries to use the dead FFmpeg.
        logger.warning(f"Timeline {stream_id} FFmpeg died - watchdog should attempt recovery")
        
    async def _execute_timeline(
        self,
        timeline_id: int,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile],
        start_position: Optional[float] = None
    ):
        """
        Main timeline execution loop.
        
        This is the magic that switches between cameras!
        
        Args:
            start_position: If provided, skip segments before this time and start from here
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
            
            # PRE-FETCH ALL OVERLAYS for time-based switching (no FFmpeg restarts!)
            logger.info(f"🎨 Pre-fetching overlays for dynamic switching...")
            timed_overlays, overlay_temp_files = await self._prefetch_all_overlays(timeline, db)
            
            # Main execution loop (segment-based: overlays handled by time-based enables in FFmpeg)
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

                    # Handle start_position: skip segments that end before start position
                    if start_position is not None and start_position > 0:
                        if seg_end <= start_position:
                            # This segment ends before our start position, skip it entirely
                            logger.debug(f"Skipping segment {seg_index+1} (ends at {seg_end:.2f}s, before start_position {start_position:.2f}s)")
                            continue
                        
                        if seg_start < start_position < seg_end:
                            # This segment contains our start position - adjust duration
                            time_to_skip = start_position - seg_start
                            duration = duration - time_to_skip
                            logger.info(f"Starting mid-segment at {start_position:.2f}s (skipping {time_to_skip:.2f}s of segment)")
                            # Clear start_position so we don't skip again on subsequent loops
                            start_position = None

                    # Determine active video cue at segment start
                    active_video_cues = [
                        c for c in cues
                        if seg_start >= c.start_time and seg_start < (c.start_time + c.duration)
                    ]
                    if not active_video_cues:
                        # No video cue at this time - check if FFmpeg is already running
                        stream_running = timeline_id in ffmpeg_manager.processes
                        if stream_running:
                            # FFmpeg is running from previous cue - continue streaming that content
                            logger.info(f"📋 Gap segment at t={seg_start:.2f}s for {duration:.2f}s - continuing last camera (FFmpeg running)")
                            await asyncio.sleep(duration)
                            self._last_segment_time[timeline_id] = datetime.utcnow()
                            continue
                        else:
                            # No FFmpeg running and no cue - this is a gap at timeline start
                            logger.warning(f"⚠️  No video cue at t={seg_start:.2f}s and no stream running - skipping gap")
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

                    # Get camera/preset for this segment BEFORE executing
                    # (so we can update tracking even if segment throws an error)
                    segment_camera_id = video_cue.action_params.get("camera_id")
                    segment_preset_id = video_cue.action_params.get("preset_id")

                    # Execute this segment (overlays handled by time-based enables in FFmpeg)
                    try:
                        await self._execute_segment(
                            timeline_id=timeline_id,
                            seg_start=seg_start,
                            duration=duration,
                            video_cue=video_cue,
                            ffmpeg_manager=ffmpeg_manager,
                            output_urls=output_urls,
                            encoding_profile=encoding_profile,
                            db=db,
                            last_camera_preset=(last_camera_id, last_preset_id),
                            timed_overlays=timed_overlays,
                            timeline_duration=timeline.duration,
                            timeline_loop=timeline.loop
                        )
                    except asyncio.CancelledError:
                        raise  # Re-raise cancellation
                    except Exception as seg_error:
                        logger.error(
                            f"Error executing segment {seg_index+1}/{len(segments)} at t={seg_start:.2f}s: {seg_error}",
                            exc_info=True
                        )
                        # Update heartbeat even on error so watchdog knows we're making progress
                        self._last_segment_time[timeline_id] = datetime.utcnow()
                        # Update camera tracking even on error to prevent false "camera changed" detection
                        last_camera_id = segment_camera_id
                        last_preset_id = segment_preset_id
                        # Continue to next segment instead of crashing the whole timeline
                        continue

                    # Cancel position updates
                    if timeline_id in self._position_update_tasks:
                        self._position_update_tasks[timeline_id].cancel()
                        try:
                            await self._position_update_tasks[timeline_id]
                        except asyncio.CancelledError:
                            pass

                    # Track last camera/preset for next segment
                    last_camera_id = segment_camera_id
                    last_preset_id = segment_preset_id

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
            # Clean up overlay temp files
            if overlay_temp_files:
                for temp_file in overlay_temp_files:
                    try:
                        if temp_file.startswith('/tmp/') or temp_file.startswith(tempfile.gettempdir()):
                            os.unlink(temp_file)
                            logger.debug(f"🗑️  Cleaned up temp overlay file: {temp_file}")
                    except Exception:
                        pass
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

    def _get_overlay_ids_at_time(self, timeline: Timeline, current_time: float) -> List[int]:
        """Get list of overlay asset IDs active at a specific time"""
        overlay_ids = []
        for track in timeline.tracks:
            if not track.is_enabled or track.track_type != 'overlay':
                continue
            for cue in track.cues:
                cue_start = cue.start_time
                cue_end = cue.start_time + cue.duration
                if current_time >= cue_start and current_time < cue_end:
                    asset_id = cue.action_params.get('asset_id')
                    if asset_id:
                        overlay_ids.append(asset_id)
        return sorted(overlay_ids)

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
            elif asset.type == 'google_drawing' and asset.file_path:
                # Parse Google Drive Drawing URL and download PNG
                export_url = parse_google_drawing_url(asset.file_path)
                if not export_url:
                    logger.warning(f"⚠️  Invalid Google Drive Drawing URL for asset '{asset.name}': {asset.file_path}")
                    return None
                
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(export_url)
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            tmp.write(response.content)
                            logger.info(f"📥 Downloaded Google Drawing PNG for asset '{asset.name}' to {tmp.name}")
                            return tmp.name
                    else:
                        logger.warning(f"⚠️  Failed to download Google Drawing for asset '{asset.name}': HTTP {response.status_code}")
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
    
    async def _prefetch_all_overlays(self, timeline: Timeline, db: Session) -> List[Dict]:
        """
        Download ALL overlay images before starting FFmpeg.
        
        Returns list of timed overlays with:
        - path: downloaded image path
        - x, y: pixel positions
        - opacity: 0-1
        - width, height: optional dimensions
        - start_time, end_time: when overlay should be visible
        - asset_id: for tracking
        
        These will be passed to FFmpeg with time-based enable expressions,
        so overlays can change without restarting FFmpeg.
        """
        timed_overlays = []
        temp_files = []
        
        logger.info(f"🎨 Pre-fetching all overlay images for timeline...")
        
        for track in timeline.tracks:
            if track.track_type != 'overlay' or not track.is_enabled:
                continue
            
            for cue in track.cues:
                asset_id = cue.action_params.get('asset_id')
                if not asset_id:
                    continue
                
                # Get asset from database
                asset = db.query(Asset).filter(Asset.id == asset_id).first()
                if not asset or not asset.is_active:
                    logger.warning(f"Asset {asset_id} not found or inactive, skipping")
                    continue
                
                # Download/get image path
                image_path = await self._download_asset_image(asset)
                if not image_path:
                    logger.warning(f"Failed to get image for asset '{asset.name}', skipping")
                    continue
                
                # Track temp files for cleanup later
                if image_path.startswith('/tmp/') or image_path.startswith(tempfile.gettempdir()):
                    temp_files.append(image_path)
                
                # Calculate pixel positions from normalized coordinates (0-1 range)
                x_pixels = int(asset.position_x * 1920)
                y_pixels = int(asset.position_y * 1080)
                
                timed_overlay = {
                    'path': image_path,
                    'x': x_pixels,
                    'y': y_pixels,
                    'opacity': asset.opacity,
                    'start_time': float(cue.start_time),
                    'end_time': float(cue.start_time + cue.duration),
                    'asset_id': asset_id,
                    'asset_name': asset.name
                }
                
                # Add dimensions if specified
                if asset.width:
                    timed_overlay['width'] = asset.width
                if asset.height:
                    timed_overlay['height'] = asset.height
                
                timed_overlays.append(timed_overlay)
                
                logger.info(
                    f"  🖼️  {asset.name}: t={cue.start_time:.1f}s-{cue.start_time + cue.duration:.1f}s "
                    f"at ({x_pixels}, {y_pixels})"
                )
        
        logger.info(f"🎨 Pre-fetched {len(timed_overlays)} overlay(s) for timeline")
        
        # Store temp files for cleanup (will be cleaned up when timeline stops)
        return timed_overlays, temp_files
    
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
        last_camera_preset: Tuple[Optional[int], Optional[int]],
        timed_overlays: Optional[List[Dict]] = None,
        timeline_duration: float = 0,
        timeline_loop: bool = False
    ):
        """Execute a single time segment with current video.

        Overlays are handled by time-based enable expressions in FFmpeg - 
        they were pre-fetched at timeline start and don't trigger restarts.
        
        For PTZ cameras: When only the preset changes (same camera), we keep
        the stream running and just move the camera. This shows smooth PTZ
        movement instead of stream interruption.
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
                
                # Check if this is the same camera as last segment
                same_camera = (last_camera_preset[0] == camera_id)
                preset_changed = (last_camera_preset[1] != preset_id)
                
                # Get preset info for logging
                preset = None
                if preset_id:
                    preset = db.query(Preset).filter(Preset.id == preset_id).first()
                
                # Determine if we need to restart FFmpeg
                # Only restart if: camera changed OR stream not running
                # NOTE: Overlays use time-based enables in FFmpeg - no restart needed!
                # Check BOTH presence AND status - stream may exist but be STOPPED (e.g., by watchdog)
                stream_proc = ffmpeg_manager.processes.get(timeline_id)
                stream_running = (stream_proc is not None and 
                                  stream_proc.status == StreamStatus.RUNNING)
                needs_restart = (not same_camera) or (not stream_running)
                
                # If preset specified and changed, move camera
                # Do this BEFORE restarting stream if camera changed, or DURING stream if same camera
                if preset_id and preset and preset_changed:
                    # Get camera credentials
                    password = None
                    if camera.password_enc:
                        try:
                            password = base64.b64decode(camera.password_enc).decode()
                        except Exception as e:
                            logger.error(f"Failed to decode camera password: {e}")
                    
                    if password:
                        if same_camera and stream_running:
                            # Same camera, stream running - move PTZ while streaming (shows movement!)
                            logger.info(f"🎬 Moving camera {camera.name} to preset '{preset.name}' (viewers will see movement)")
                        else:
                            logger.info(f"🎯 Moving camera {camera.name} to preset '{preset.name}'")
                        
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
                            else:
                                logger.warning(f"⚠️  Failed to move camera to preset, continuing anyway")
                        except Exception as e:
                            logger.error(f"❌ Error moving camera to preset: {e}")
                            # Continue anyway - don't fail the whole timeline
                    else:
                        logger.warning(f"⚠️  No camera credentials available for PTZ control")
                
                # Build RTSP URL
                rtsp_url = self._build_rtsp_url(camera)
                preset_info = f" at preset '{preset.name}'" if preset_id and preset else ""
                logger.info(f"🎬 Segment streaming from camera {camera.name}{preset_info} for {duration}s")
                logger.debug(f"RTSP URL: {rtsp_url}")
                logger.debug(f"Output URLs: {output_urls}")
                
                # Only restart FFmpeg if needed
                if needs_restart:
                    # SEAMLESS HANDOFF: Start new stream BEFORE stopping old
                    # This eliminates viewer buffering during camera switches
                    overlay_info = f" with {len(timed_overlays)} timed overlay(s)" if timed_overlays else ""
                    
                    if stream_running:
                        # Use a temporary stream ID for the new stream
                        temp_stream_id = timeline_id + 1000000
                        reason = "camera changed"
                        logger.info(f"🔄 Seamless handoff: {reason} - starting new stream before stopping old")
                        
                        try:
                            # Step 1: Start NEW stream with temporary ID
                            logger.info(f"▶️  Starting NEW FFmpeg stream (temp ID {temp_stream_id}) with camera {camera.name}{overlay_info}")
                            await asyncio.wait_for(
                                ffmpeg_manager.start_stream(
                                    stream_id=temp_stream_id,
                                    input_url=rtsp_url,
                                    output_urls=output_urls,
                                    profile=encoding_profile or EncodingProfile.reliability_profile(
                                        ffmpeg_manager.hw_capabilities
                                    ),
                                    timed_overlays=timed_overlays,
                                    timeline_duration=timeline_duration,
                                    timeline_loop=timeline_loop
                                ),
                                timeout=30.0  # Reduced timeout for faster handoff
                            )
                            logger.info(f"✅ New FFmpeg stream {temp_stream_id} started, now stopping old stream")
                            
                            # Step 2: Stop OLD stream (while new one is already running)
                            try:
                                logger.debug(f"Stopping old stream {timeline_id}...")
                                ffmpeg_manager.unregister_stream_died_callback(timeline_id)
                                await asyncio.wait_for(
                                    ffmpeg_manager.stop_stream(timeline_id),
                                    timeout=10.0  # Quick stop since new stream is already running
                                )
                                logger.info(f"✅ Old stream {timeline_id} stopped")
                            except asyncio.TimeoutError:
                                logger.warning(f"Timeout stopping old FFmpeg - forcing kill")
                                try:
                                    if timeline_id in ffmpeg_manager.processes:
                                        proc = ffmpeg_manager.processes[timeline_id].process
                                        if proc:
                                            proc.kill()
                                except Exception:
                                    pass
                            except KeyError:
                                pass  # Already stopped
                            except Exception as e:
                                logger.warning(f"Error stopping old stream: {e}")
                            
                            # Step 3: Re-map the new stream to use the timeline_id
                            # Move the process entry from temp_stream_id to timeline_id
                            if temp_stream_id in ffmpeg_manager.processes:
                                stream_proc = ffmpeg_manager.processes.pop(temp_stream_id)
                                stream_proc.stream_id = timeline_id  # Update the stream_id field
                                ffmpeg_manager.processes[timeline_id] = stream_proc
                                
                                # Also re-map the monitoring task
                                if temp_stream_id in ffmpeg_manager._monitoring_tasks:
                                    ffmpeg_manager._monitoring_tasks[timeline_id] = ffmpeg_manager._monitoring_tasks.pop(temp_stream_id)
                                
                                logger.debug(f"Re-mapped stream {temp_stream_id} → {timeline_id}")
                            
                            # Register callback for the (now remapped) stream
                            ffmpeg_manager.register_stream_died_callback(
                                timeline_id,
                                self._on_ffmpeg_died
                            )
                            
                            logger.info(f"✅ Seamless handoff complete - now streaming from {camera.name}")
                            
                        except asyncio.TimeoutError:
                            logger.error(f"❌ Timeout starting new FFmpeg stream - falling back to standard restart")
                            # Clean up temp stream if it partially started
                            try:
                                if temp_stream_id in ffmpeg_manager.processes:
                                    await ffmpeg_manager.stop_stream(temp_stream_id)
                            except:
                                pass
                            # Fall back to standard stop-then-start
                            await self._standard_ffmpeg_restart(
                                timeline_id, ffmpeg_manager, rtsp_url, output_urls,
                                encoding_profile, timed_overlays, timeline_duration, timeline_loop,
                                camera.name, overlay_info
                            )
                        except Exception as e:
                            logger.error(f"❌ Seamless handoff failed: {e} - falling back to standard restart")
                            # Clean up temp stream if it partially started
                            try:
                                if temp_stream_id in ffmpeg_manager.processes:
                                    await ffmpeg_manager.stop_stream(temp_stream_id)
                            except:
                                pass
                            # Fall back to standard stop-then-start
                            await self._standard_ffmpeg_restart(
                                timeline_id, ffmpeg_manager, rtsp_url, output_urls,
                                encoding_profile, timed_overlays, timeline_duration, timeline_loop,
                                camera.name, overlay_info
                            )
                    else:
                        # No existing stream - just start normally
                        logger.info(f"▶️  Starting FFmpeg stream {timeline_id} with camera {camera.name}{overlay_info}")
                        try:
                            await asyncio.wait_for(
                                ffmpeg_manager.start_stream(
                                    stream_id=timeline_id,
                                    input_url=rtsp_url,
                                    output_urls=output_urls,
                                    profile=encoding_profile or EncodingProfile.reliability_profile(
                                        ffmpeg_manager.hw_capabilities
                                    ),
                                    timed_overlays=timed_overlays,
                                    timeline_duration=timeline_duration,
                                    timeline_loop=timeline_loop
                                ),
                                timeout=60.0
                            )
                            logger.info(f"✅ FFmpeg stream {timeline_id} started successfully")
                            
                            # Register callback to detect when FFmpeg dies
                            ffmpeg_manager.register_stream_died_callback(
                                timeline_id,
                                self._on_ffmpeg_died
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"❌ Timeout starting FFmpeg stream {timeline_id}")
                            raise RuntimeError(f"Timeout starting FFmpeg stream {timeline_id}")
                        except Exception as e:
                            logger.error(f"❌ Failed to start FFmpeg stream {timeline_id}: {e}")
                            traceback.print_exc()
                            raise
                    
                    # Notify watchdog manager about the stream (whether seamless or standard)
                    try:
                        from services.watchdog_manager import get_watchdog_manager
                        from models.destination import StreamingDestination
                        
                        watchdog_manager = get_watchdog_manager()
                        
                        dest_ids = []
                        dest_db = SessionLocal()
                        try:
                            for output_url in output_urls:
                                destinations = dest_db.query(StreamingDestination).all()
                                for dest in destinations:
                                    if dest.get_full_rtmp_url() == output_url:
                                        dest_ids.append(dest.id)
                                        break
                            
                            if dest_ids:
                                await watchdog_manager.notify_stream_started(
                                    destination_ids=dest_ids,
                                    stream_id=timeline_id,
                                    db_session=dest_db
                                )
                                logger.info(f"🐕 Notified watchdog manager: stream {timeline_id} → destinations {dest_ids}")
                        finally:
                            dest_db.close()
                    except Exception as e:
                        logger.warning(f"Failed to notify watchdog manager: {e}")
                else:
                    # Same camera, same overlays - just log that we're continuing
                    logger.info(f"📹 Continuing stream (same camera, preset changed to '{preset.name if preset else 'none'}')")
                
                # Wait for cue duration
                logger.info(f"⏱️  Waiting {duration}s for segment to complete...")
                await asyncio.sleep(duration)
                logger.info(f"✅ Segment at t={seg_start:.2f}s ({camera.name}) completed successfully")
                
                # Update heartbeat for stall detection
                self._last_segment_time[timeline_id] = datetime.utcnow()
                
            else:
                logger.warning("Unsupported action type for video cue")
                
        except Exception as e:
            logger.error(f"❌ Error executing segment at t={seg_start:.2f}s: {e}")
            traceback.print_exc()
            raise  # Re-raise the exception to stop timeline execution
    
    async def _standard_ffmpeg_restart(
        self,
        timeline_id: int,
        ffmpeg_manager: FFmpegProcessManager,
        rtsp_url: str,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile],
        timed_overlays: Optional[List[Dict]],
        timeline_duration: float,
        timeline_loop: bool,
        camera_name: str,
        overlay_info: str
    ):
        """
        Standard stop-then-start FFmpeg restart (fallback when seamless handoff fails).
        This is the original behavior - stops old stream, then starts new one.
        """
        logger.info(f"🔄 Standard FFmpeg restart for timeline {timeline_id}")
        
        # Stop existing stream
        try:
            ffmpeg_manager.unregister_stream_died_callback(timeline_id)
            await asyncio.wait_for(
                ffmpeg_manager.stop_stream(timeline_id),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout stopping FFmpeg for timeline {timeline_id} - forcing kill")
            try:
                if timeline_id in ffmpeg_manager.processes:
                    proc = ffmpeg_manager.processes[timeline_id].process
                    if proc:
                        proc.kill()
            except Exception:
                pass
        except KeyError:
            pass  # Not running
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
        
        # Start new stream
        logger.info(f"▶️  Starting FFmpeg stream {timeline_id} with camera {camera_name}{overlay_info}")
        await asyncio.wait_for(
            ffmpeg_manager.start_stream(
                stream_id=timeline_id,
                input_url=rtsp_url,
                output_urls=output_urls,
                profile=encoding_profile or EncodingProfile.reliability_profile(
                    ffmpeg_manager.hw_capabilities
                ),
                timed_overlays=timed_overlays,
                timeline_duration=timeline_duration,
                timeline_loop=timeline_loop
            ),
            timeout=60.0
        )
        logger.info(f"✅ FFmpeg stream {timeline_id} started successfully")
        
        # Register callback
        ffmpeg_manager.register_stream_died_callback(
            timeline_id,
            self._on_ffmpeg_died
        )
            
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
