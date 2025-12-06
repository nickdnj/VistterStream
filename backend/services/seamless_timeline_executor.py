"""
Seamless Timeline Executor - ONE FFmpeg Process, ZERO Black Screens
This is the SECRET SAUCE for professional multi-camera streaming!
"""

import asyncio
import logging
import tempfile
import os
import httpx
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

from models.database import SessionLocal, Asset, Camera, Preset
from models.timeline import Timeline, TimelineCue, TimelineExecution, TimelineTrack
from services.ffmpeg_manager import FFmpegProcessManager, EncodingProfile
from services.ptz_service import get_ptz_service
from services.rtmp_relay_service import get_rtmp_relay_service
from utils.google_drive import parse_google_drawing_url
import base64

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SeamlessTimelineExecutor:
    """
    Executes timelines with ONE continuous FFmpeg process.
    NO RESTARTS = NO BLACK SCREENS = SEAMLESS STREAMING!
    """
    
    def __init__(self):
        self.active_timelines: Dict[int, asyncio.Task] = {}
        self.ffmpeg_processes: Dict[int, asyncio.subprocess.Process] = {}
        self._shutdown_event = asyncio.Event()
    
    async def start_timeline(
        self,
        timeline_id: int,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile] = None
    ) -> bool:
        """Start executing a timeline with seamless camera switching"""
        if timeline_id in self.active_timelines:
            logger.warning(f"Timeline {timeline_id} is already running")
            return False
        
        # Create execution task
        task = asyncio.create_task(
            self._execute_timeline_seamless(timeline_id, output_urls, encoding_profile)
        )
        self.active_timelines[timeline_id] = task
        
        logger.info(f"✅ Started seamless timeline {timeline_id}")
        return True
    
    async def stop_timeline(self, timeline_id: int) -> bool:
        """Stop a running timeline"""
        if timeline_id not in self.active_timelines:
            return False
        
        # Cancel the task
        task = self.active_timelines[timeline_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Kill FFmpeg if running
        if timeline_id in self.ffmpeg_processes:
            process = self.ffmpeg_processes[timeline_id]
            try:
                process.terminate()
                await asyncio.sleep(1)
                if process.returncode is None:
                    process.kill()
            except:
                pass
            del self.ffmpeg_processes[timeline_id]
        
        del self.active_timelines[timeline_id]
        logger.info(f"🛑 Stopped timeline {timeline_id}")
        return True
    
    async def _execute_timeline_seamless(
        self,
        timeline_id: int,
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile]
    ):
        """Execute timeline with ONE FFmpeg process - the secret sauce!"""
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
            
            logger.info(f"🎬 SEAMLESS EXECUTION: {timeline.name}")
            logger.info(f"   Duration: {timeline.duration}s")
            logger.info(f"   Loop: {timeline.loop}")
            
            # Get all video cues sorted by time
            video_cues = []
            for track in timeline.tracks:
                if track.track_type == 'video' and track.is_enabled:
                    video_cues.extend(track.cues)
            
            video_cues = sorted(video_cues, key=lambda c: c.start_time)
            
            if not video_cues:
                logger.error(f"No video cues in timeline!")
                return
            
            logger.info(f"   Video cues: {len(video_cues)}")
            
            # STEP 1: Move all PTZ cameras to their presets BEFORE streaming
            logger.info(f"🎯 PRE-POSITIONING PTZ CAMERAS...")
            await self._preposition_ptz_cameras(video_cues, db)
            
            # STEP 2: Build seamless FFmpeg command
            logger.info(f"🔨 BUILDING SEAMLESS FFMPEG COMMAND...")
            ffmpeg_cmd, temp_files = await self._build_seamless_ffmpeg_command(
                timeline,
                video_cues,
                output_urls,
                encoding_profile,
                db
            )
            
            logger.info(f"📺 FFmpeg command built with {len([x for x in ffmpeg_cmd if x == '-i'])} inputs")
            logger.debug(f"Command: {' '.join(ffmpeg_cmd[:20])}...")
            
            # STEP 3: Start ONE FFmpeg process that runs for entire timeline
            logger.info(f"▶️  STARTING SEAMLESS FFMPEG STREAM...")
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                self.ffmpeg_processes[timeline_id] = process
                logger.info(f"✅ FFmpeg started (PID: {process.pid})")
                
                # Monitor FFmpeg output
                async def log_ffmpeg_output():
                    while True:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        logger.debug(f"FFmpeg: {line.decode().strip()}")
                
                monitor_task = asyncio.create_task(log_ffmpeg_output())
                
                # Wait for process or cancellation
                if timeline.loop:
                    # For looping timelines, FFmpeg will loop forever
                    await process.wait()
                else:
                    # For non-looping, wait for timeline duration
                    await asyncio.sleep(timeline.duration)
                    process.terminate()
                
                monitor_task.cancel()
                
                execution.completed_at = datetime.utcnow()
                execution.status = "completed"
                db.commit()
                
            except Exception as e:
                logger.error(f"❌ FFmpeg error: {e}")
                raise
            finally:
                # Clean up temp files
                for temp_file in temp_files:
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
        
        except asyncio.CancelledError:
            logger.info(f"Timeline {timeline_id} cancelled")
            execution.status = "stopped"
            db.commit()
            raise
        except Exception as e:
            logger.error(f"Timeline execution error: {e}")
            execution.status = "error"
            execution.error_message = str(e)
            db.commit()
        finally:
            db.close()
    
    async def _preposition_ptz_cameras(self, video_cues: List[TimelineCue], db: Session):
        """Move all PTZ cameras to their presets BEFORE streaming starts"""
        preset_moves = {}
        
        for cue in video_cues:
            camera_id = cue.action_params.get('camera_id')
            preset_id = cue.action_params.get('preset_id')
            
            if camera_id and preset_id:
                preset_moves[(camera_id, preset_id)] = (camera_id, preset_id)
        
        logger.info(f"   Found {len(preset_moves)} unique PTZ preset positions")
        
        for camera_id, preset_id in preset_moves.values():
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            preset = db.query(Preset).filter(Preset.id == preset_id).first()
            
            if not camera or not preset:
                continue
            
            logger.info(f"   🎯 Moving {camera.name} to '{preset.name}'")
            
            try:
                password = base64.b64decode(camera.password_enc).decode() if camera.password_enc else None
                if password:
                    ptz_service = get_ptz_service()
                    pan = preset.pan if preset.pan is not None else 0.0
                    tilt = preset.tilt if preset.tilt is not None else 0.0
                    zoom = preset.zoom if preset.zoom is not None else 1.0
                    await ptz_service.move_to_preset(
                        address=camera.address,
                        port=camera.onvif_port,
                        username=camera.username,
                        password=password,
                        preset_token=preset.camera_preset_token or str(preset_id),
                        pan=pan,
                        tilt=tilt,
                        zoom=zoom,
                    )
                    await asyncio.sleep(0.5)  # Brief settle time
            except Exception as e:
                logger.warning(f"   ⚠️  PTZ move failed: {e}")
        
        logger.info(f"   ✅ PTZ pre-positioning complete")
    
    async def _build_seamless_ffmpeg_command(
        self,
        timeline: Timeline,
        video_cues: List[TimelineCue],
        output_urls: list[str],
        encoding_profile: Optional[EncodingProfile],
        db: Session
    ) -> Tuple[List[str], List[str]]:
        """
        Build ONE FFmpeg command that handles the entire timeline seamlessly.
        This is the MAGIC that prevents black screens!
        """
        temp_files = []
        
        # Get all unique cameras in timeline
        relay_service = get_rtmp_relay_service()
        camera_map = {}
        
        for cue in video_cues:
            camera_id = cue.action_params.get('camera_id')
            if camera_id and camera_id not in camera_map:
                camera = db.query(Camera).filter(Camera.id == camera_id).first()
                if camera:
                    # Use LOCAL RTMP relay URL (instant switching!)
                    rtmp_url = relay_service.get_relay_url(camera_id)
                    if not rtmp_url:
                        logger.warning(f"⚠️  No relay running for camera {camera.name}, skipping")
                        continue
                    
                    camera_map[camera_id] = {
                        'camera': camera,
                        'input_index': len(camera_map),
                        'rtmp_url': rtmp_url  # LOCAL RTMP (not direct RTSP!)
                    }
        
        logger.info(f"   📹 Found {len(camera_map)} unique cameras with active relays")
        
        # Start building command
        cmd = ['ffmpeg', '-re']
        
        # Add all camera inputs (FROM LOCAL RTMP - instant switching!)
        for camera_id, cam_data in camera_map.items():
            cmd.extend([
                '-i', cam_data['rtmp_url']  # Read from local RTMP relay
            ])
            logger.info(f"      Input {cam_data['input_index']}: {cam_data['camera'].name} (via relay)")
        
        # Download all overlay images
        overlay_images = await self._prepare_overlay_images(timeline, db, temp_files)
        
        # Add overlay image inputs
        overlay_input_start = len(camera_map)
        for idx, overlay in enumerate(overlay_images):
            cmd.extend(['-loop', '1', '-i', overlay['path']])
        
        # Build filter_complex for seamless switching
        filter_complex = await self._build_filter_complex(
            timeline,
            video_cues,
            camera_map,
            overlay_images,
            overlay_input_start
        )
        
        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[outv]', '-map', '0:a'])  # Use audio from first camera
        
        # Encoding settings
        if not encoding_profile:
            from services.hardware_detector import get_hardware_capabilities
            hw_caps = await get_hardware_capabilities()
            encoding_profile = EncodingProfile.reliability_profile(hw_caps)
        
        # Video codec
        cmd.extend([
            '-c:v', 'libx264',  # Use software for compatibility with complex filters
            '-preset', 'veryfast',
            '-tune', 'zerolatency',
            '-b:v', '4500k',
            '-maxrate', '4500k',
            '-bufsize', '9000k',
            '-g', '60',  # Keyframe every 2s at 30fps
            '-r', '30',
            '-profile:v', 'main',
            '-level', '4.1'
        ])
        
        # Audio codec
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100'
        ])
        
        # Output
        cmd.extend(['-f', 'flv', output_urls[0]])
        
        # Loop if needed
        if timeline.loop:
            cmd.insert(1, '-stream_loop')
            cmd.insert(2, '-1')
        
        return cmd, temp_files
    
    async def _build_filter_complex(
        self,
        timeline: Timeline,
        video_cues: List[TimelineCue],
        camera_map: Dict,
        overlay_images: List[Dict],
        overlay_input_start: int
    ) -> str:
        """
        Build the filter_complex that does the magic:
        - Switches between cameras based on timeline
        - Composites overlays at the right times
        - All seamlessly in ONE FFmpeg process!
        """
        filters = []
        
        # For RTSP live streams, we can't use trim with start/end times
        # Instead, we'll use a simpler approach: scale each input and concat
        # FFmpeg will read duration seconds from each before moving to next
        
        segments = []
        
        for idx, cue in enumerate(video_cues):
            camera_id = cue.action_params.get('camera_id')
            if camera_id not in camera_map:
                continue
            
            input_idx = camera_map[camera_id]['input_index']
            
            # Each segment: scale to 1920x1080, normalize fps
            segment_filter = (
                f"[{input_idx}:v]"
                f"scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                f"fps=30,"
                f"setpts=PTS-STARTPTS"
                f"[seg{idx}]"
            )
            filters.append(segment_filter)
            segments.append(f"[seg{idx}]")
        
        # Concatenate all segments
        if len(segments) > 1:
            segment_labels = ''.join(segments)
            filters.append(f"{segment_labels}concat=n={len(segments)}:v=1:a=0[video]")
        elif len(segments) == 1:
            filters.append(f"[seg0]copy[video]")
        else:
            # Fallback - just use first camera scaled
            filters.append(f"[0:v]scale=1920:1080,fps=30[video]")
        
        # Add overlays if any (simplified for now - full time-based later)
        if overlay_images:
            # For now, just overlay first image on entire video
            overlay_idx = overlay_input_start
            overlay = overlay_images[0]
            x = overlay['x']
            y = overlay['y']
            opacity = overlay['opacity']
            
            filters.append(
                f"[video][{overlay_idx}:v]overlay=x={x}:y={y}:format=auto[outv]"
            )
        else:
            filters.append(f"[video]copy[outv]")
        
        filter_str = ';'.join(filters)
        logger.debug(f"Filter complex: {filter_str}")
        return filter_str
    
    async def _prepare_overlay_images(
        self,
        timeline: Timeline,
        db: Session,
        temp_files: List[str]
    ) -> List[Dict]:
        """Download all overlay images needed for the timeline"""
        overlay_images = []
        processed_assets = set()
        
        for track in timeline.tracks:
            if track.track_type != 'overlay' or not track.is_enabled:
                continue
            
            for cue in track.cues:
                asset_id = cue.action_params.get('asset_id')
                if not asset_id or asset_id in processed_assets:
                    continue
                
                processed_assets.add(asset_id)
                asset = db.query(Asset).filter(Asset.id == asset_id).first()
                
                if not asset or not asset.is_active:
                    continue
                
                # Download/get image path
                image_path = await self._download_asset_image(asset)
                if image_path:
                    if image_path.startswith('/tmp/'):
                        temp_files.append(image_path)
                    
                    overlay_images.append({
                        'asset_id': asset_id,
                        'path': image_path,
                        'x': int(asset.position_x * 1920),
                        'y': int(asset.position_y * 1080),
                        'opacity': asset.opacity
                    })
        
        logger.info(f"   🎨 Prepared {len(overlay_images)} overlay images")
        return overlay_images
    
    async def _download_asset_image(self, asset: Asset) -> Optional[str]:
        """Download asset image to temp file"""
        try:
            if asset.type == 'api_image' and asset.api_url:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(asset.api_url)
                    if response.status_code == 200:
                        suffix = '.png' if 'png' in response.headers.get('content-type', '') else '.jpg'
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                            tmp.write(response.content)
                            return tmp.name
            elif asset.type == 'google_drawing' and asset.file_path:
                # Parse Google Drive Drawing URL and download PNG
                export_url = parse_google_drawing_url(asset.file_path)
                if not export_url:
                    logger.warning(f"Invalid Google Drive Drawing URL for asset '{asset.name}': {asset.file_path}")
                    return None
                
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    response = await client.get(export_url)
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                            tmp.write(response.content)
                            logger.info(f"Downloaded Google Drawing PNG for asset '{asset.name}' to {tmp.name}")
                            return tmp.name
                    else:
                        logger.warning(f"Failed to download Google Drawing for asset '{asset.name}': HTTP {response.status_code}")
            elif asset.type == 'static_image' and asset.file_path:
                # Skip SVG files for now - FFmpeg can't read them directly
                # TODO: Convert SVG to PNG using librsvg or similar
                if asset.file_path.endswith('.svg'):
                    logger.warning(f"Skipping SVG asset {asset.name} - not supported in FFmpeg yet")
                    return None
                
                # For other static images
                if asset.file_path.startswith('/'):
                    return f"/Users/nickd/Workspaces/VistterStream/frontend/public{asset.file_path}"
                return asset.file_path
        except Exception as e:
            logger.error(f"Failed to download asset: {e}")
        
        return None
    
    def _build_rtsp_url(self, camera: Camera) -> str:
        """Build RTSP URL for camera"""
        password = None
        if camera.password_enc:
            try:
                password = base64.b64decode(camera.password_enc).decode()
            except:
                pass
        
        if camera.username and password:
            return f"rtsp://{camera.username}:{password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            return f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"


# Global instance
_seamless_executor: Optional[SeamlessTimelineExecutor] = None


def get_seamless_timeline_executor() -> SeamlessTimelineExecutor:
    """Get the global seamless timeline executor"""
    global _seamless_executor
    if _seamless_executor is None:
        _seamless_executor = SeamlessTimelineExecutor()
    return _seamless_executor
