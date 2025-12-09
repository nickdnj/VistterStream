"""
FFmpeg Process Manager
Manages FFmpeg processes with lifecycle control, health monitoring, and auto-restart.

References:
    See docs/StreamingPipeline-TechnicalSpec.md §"Streaming Pipeline Architecture"
"""

import asyncio
import re
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Callable
from enum import Enum
import logging

from .hardware_detector import get_hardware_capabilities, HardwareCapabilities

logger = logging.getLogger(__name__)


class StreamStatus(str, Enum):
    """Stream status states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class EncodingProfile:
    """Encoding configuration profile"""
    codec: str  # Will be set by hardware detector
    resolution: tuple[int, int] = (1920, 1080)
    framerate: int = 30
    bitrate: str = "4500k"  # Conservative for reliability
    keyframe_interval: int = 2  # seconds
    buffer_size: str = "9000k"  # 2x bitrate
    preset: str = "fast"
    profile: str = "main"
    level: str = "4.1"
    
    @classmethod
    def reliability_profile(cls, hw_capabilities: HardwareCapabilities) -> 'EncodingProfile':
        """
        Create reliability-focused profile per spec.
        
        See: StreamingPipeline-TechnicalSpec.md §"Encoding Profiles"
        """
        return cls(
            codec=hw_capabilities.encoder,
            resolution=(1920, 1080),
            framerate=30,
            bitrate="4500k",
            keyframe_interval=2,
            buffer_size="9000k",
            preset="fast",
            profile="main",
            level="4.1"
        )


@dataclass
class StreamMetrics:
    """Real-time stream metrics"""
    bitrate_current: float = 0.0  # Mbps
    bitrate_target: float = 4.5
    framerate_actual: float = 0.0
    framerate_target: float = 30.0
    dropped_frames: int = 0
    encoding_time_ms: float = 0.0  # Time to encode each frame
    buffer_fullness: float = 100.0  # percentage
    uptime_seconds: int = 0
    total_bytes_sent: int = 0
    last_update: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StreamProcess:
    """Represents a running FFmpeg stream process"""
    stream_id: int
    process: Optional[asyncio.subprocess.Process] = None
    status: StreamStatus = StreamStatus.STOPPED
    metrics: StreamMetrics = field(default_factory=StreamMetrics)
    retry_count: int = 0
    started_at: Optional[datetime] = None
    last_error: Optional[str] = None
    command: List[str] = field(default_factory=list)
    should_auto_restart: bool = True  # Set to False when manually stopped
    output_urls: List[str] = field(default_factory=list)  # Track destination URLs


class FFmpegProcessManager:
    """
    Manages FFmpeg processes with lifecycle control and health monitoring.
    
    Features:
    - Process spawning with hardware acceleration
    - Real-time metrics parsing from FFmpeg output
    - Graceful shutdown (SIGTERM → SIGKILL)
    - Auto-restart with exponential backoff
    - Health monitoring with heartbeat checks
    """
    
    def __init__(self):
        self.processes: Dict[int, StreamProcess] = {}
        self.hw_capabilities: Optional[HardwareCapabilities] = None
        self._monitoring_tasks: Dict[int, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize the manager and detect hardware"""
        logger.info("Initializing FFmpeg Process Manager...")
        self.hw_capabilities = await get_hardware_capabilities()
        logger.info(f"Hardware capabilities: {self.hw_capabilities.encoder} "
                   f"(max {self.hw_capabilities.max_concurrent_streams} streams)")
    
    async def start_stream(
        self,
        stream_id: int,
        input_url: str,
        output_urls: List[str],
        profile: Optional[EncodingProfile] = None,
        overlay_images: Optional[List[Dict]] = None
    ) -> StreamProcess:
        """
        Start a new FFmpeg stream process.
        
        Args:
            stream_id: Unique stream identifier
            input_url: RTSP/RTMP input URL (camera feed)
            output_urls: List of RTMP output destinations
            profile: Encoding profile (uses reliability profile if None)
            overlay_images: Optional list of overlay dicts with {path, x, y, opacity}
        
        Returns:
            StreamProcess representing the running stream
        
        Raises:
            RuntimeError: If stream is already running or too many streams active
        """
        # Check if already running
        if stream_id in self.processes and self.processes[stream_id].status == StreamStatus.RUNNING:
            raise RuntimeError(f"Stream {stream_id} is already running")
        
        # Check concurrent stream limit
        active_streams = sum(1 for p in self.processes.values() if p.status == StreamStatus.RUNNING)
        if active_streams >= self.hw_capabilities.max_concurrent_streams:
            raise RuntimeError(
                f"Maximum concurrent streams ({self.hw_capabilities.max_concurrent_streams}) reached"
            )
        
        # Use default profile if not provided
        if profile is None:
            profile = EncodingProfile.reliability_profile(self.hw_capabilities)
        
        logger.info(f"Starting stream {stream_id} with {len(output_urls)} destinations")
        if overlay_images:
            logger.info(f"  🎨 With {len(overlay_images)} overlay(s)")
        
        # Build FFmpeg command
        command = self._build_ffmpeg_command(input_url, output_urls, profile, overlay_images)
        
        # Create stream process entry
        stream_process = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.STARTING,
            started_at=datetime.utcnow(),
            command=command,
            output_urls=output_urls  # Store destination URLs
        )
        
        try:
            # Spawn FFmpeg process
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stream_process.process = process
            stream_process.status = StreamStatus.RUNNING
            self.processes[stream_id] = stream_process
            
            # Start monitoring task
            monitor_task = asyncio.create_task(self._monitor_process(stream_id))
            self._monitoring_tasks[stream_id] = monitor_task
            
            logger.info(f"Stream {stream_id} started successfully (PID: {process.pid})")
            
            return stream_process
            
        except Exception as e:
            stream_process.status = StreamStatus.ERROR
            stream_process.last_error = str(e)
            logger.error(f"Failed to start stream {stream_id}: {e}")
            raise
    
    async def stop_stream(self, stream_id: int, graceful: bool = True) -> None:
        """
        Stop a running stream process.
        
        Args:
            stream_id: Stream identifier
            graceful: If True, send SIGTERM first, then SIGKILL after timeout
        
        Raises:
            KeyError: If stream_id not found
        """
        if stream_id not in self.processes:
            raise KeyError(f"Stream {stream_id} not found")
        
        stream_process = self.processes[stream_id]
        
        if stream_process.status == StreamStatus.STOPPED:
            logger.info(f"Stream {stream_id} is already stopped")
            return
        
        logger.info(f"Stopping stream {stream_id}...")
        
        # Disable auto-restart before stopping
        stream_process.should_auto_restart = False
        
        # Cancel monitoring task
        if stream_id in self._monitoring_tasks:
            self._monitoring_tasks[stream_id].cancel()
            try:
                await self._monitoring_tasks[stream_id]
            except asyncio.CancelledError:
                pass
            del self._monitoring_tasks[stream_id]
        
        # Stop the process
        if stream_process.process:
            await self._graceful_shutdown(stream_process.process, graceful)
        
        stream_process.status = StreamStatus.STOPPED
        logger.info(f"Stream {stream_id} stopped")
    
    async def restart_stream(self, stream_id: int) -> StreamProcess:
        """
        Restart a stream with exponential backoff.
        
        Args:
            stream_id: Stream identifier
        
        Returns:
            StreamProcess after restart
        """
        if stream_id not in self.processes:
            raise KeyError(f"Stream {stream_id} not found")
        
        stream_process = self.processes[stream_id]
        
        # Increment retry count
        stream_process.retry_count += 1
        
        # Check max retries (10 per spec)
        if stream_process.retry_count > 10:
            logger.error(f"Stream {stream_id} exceeded max retries (10)")
            stream_process.status = StreamStatus.ERROR
            stream_process.last_error = "Max retries exceeded"
            raise RuntimeError("Max retries exceeded")
        
        # Calculate backoff: 2s, 4s, 8s, 16s, 32s, 60s (max)
        wait_time = min(2 ** stream_process.retry_count, 60)
        
        logger.info(f"Restarting stream {stream_id} in {wait_time}s (attempt {stream_process.retry_count}/10)")
        stream_process.status = StreamStatus.RESTARTING
        
        await asyncio.sleep(wait_time)
        
        # Stop existing process
        if stream_process.process:
            await self._graceful_shutdown(stream_process.process, graceful=False)
        
        # Restart with same command
        try:
            process = await asyncio.create_subprocess_exec(
                *stream_process.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stream_process.process = process
            stream_process.status = StreamStatus.RUNNING
            stream_process.started_at = datetime.utcnow()
            
            # Restart monitoring
            monitor_task = asyncio.create_task(self._monitor_process(stream_id))
            self._monitoring_tasks[stream_id] = monitor_task
            
            logger.info(f"Stream {stream_id} restarted successfully")
            
            return stream_process
            
        except Exception as e:
            stream_process.status = StreamStatus.ERROR
            stream_process.last_error = str(e)
            logger.error(f"Failed to restart stream {stream_id}: {e}")
            raise
    
    async def get_stream_status(self, stream_id: int) -> Optional[StreamProcess]:
        """Get current status of a stream"""
        return self.processes.get(stream_id)
    
    async def get_all_streams(self) -> List[StreamProcess]:
        """Get all stream processes"""
        return list(self.processes.values())
    
    async def shutdown_all(self):
        """Shutdown all running streams"""
        logger.info("Shutting down all streams...")
        self._shutdown_event.set()
        
        # Stop all streams
        tasks = []
        for stream_id in list(self.processes.keys()):
            tasks.append(self.stop_stream(stream_id, graceful=True))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("All streams shut down")
    
    # Private methods
    
    def _build_ffmpeg_command(
        self,
        input_url: str,
        output_urls: List[str],
        profile: EncodingProfile,
        overlay_images: Optional[List[Dict]] = None
    ) -> List[str]:
        """
        Build FFmpeg command with hardware acceleration and optional overlays.
        
        Args:
            input_url: RTSP URL of camera feed
            output_urls: List of RTMP destinations
            profile: Encoding profile
            overlay_images: List of overlay dicts with {path, x, y, opacity}
        
        References:
            See StreamingPipeline-TechnicalSpec.md §"FFmpeg Strategy"
        """
        cmd = ['ffmpeg']
        
        # Input options
        cmd.extend(['-re'])  # Read input at native framerate
        # Use TCP for RTSP cameras to avoid UDP packet loss / stalls
        if input_url.lower().startswith('rtsp://'):
            cmd.extend(['-rtsp_transport', 'tcp'])
        cmd.extend([
            '-timeout', '5000000',  # 5 second timeout (microseconds)
            '-i', input_url
        ])
        
        # Add overlay image inputs
        if overlay_images:
            for overlay in overlay_images:
                # Loop still images so the filter graph never ends early
                cmd.extend(['-loop', '1', '-i', overlay['path']])

        # Add a persistent silent audio source to guarantee audio presence for RTMP destinations
        # Index calculation: [0] camera, [1..N] overlays (if any), next is silent audio input
        cmd.extend(['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100'])
        
        # Video encoding options
        resolution_str = f"{profile.resolution[0]}x{profile.resolution[1]}"
        
        # Build filter complex for overlays
        filter_parts = []
        if overlay_images:
            # Start with base video scaled to output resolution
            filter_parts.append(f"[0:v]scale={resolution_str}[base]")
            
            # Layer each overlay on top
            current_label = "base"
            for idx, overlay in enumerate(overlay_images):
                next_label = f"tmp{idx}" if idx < len(overlay_images) - 1 else "out"
                x = int(overlay.get('x', 0))
                y = int(overlay.get('y', 0))
                opacity = overlay.get('opacity', 1.0)
                width = overlay.get('width')
                height = overlay.get('height')
                
                # Scale overlay if dimensions specified
                overlay_input = f"[{idx+1}:v]"
                if width or height:
                    # Build scale filter (width:height, -1 means maintain aspect ratio)
                    w = width if width else -1
                    h = height if height else -1
                    scaled_label = f"scaled{idx}"
                    filter_parts.append(f"{overlay_input}scale={w}:{h}[{scaled_label}]")
                    overlay_input = f"[{scaled_label}]"
                
                # Overlay filter with positioning
                overlay_filter = f"[{current_label}]{overlay_input}overlay=x={x}:y={y}"
                if opacity < 1.0:
                    overlay_filter += f":alpha={opacity}"
                overlay_filter += f"[{next_label}]"
                
                filter_parts.append(overlay_filter)
                current_label = next_label
            
            filter_complex = ";".join(filter_parts)
            cmd.extend(['-filter_complex', filter_complex, '-map', '[out]'])
        else:
            # No overlays, just scale video
            cmd.extend(['-vf', f'scale={resolution_str}'])
            cmd.extend(['-map', '0:v'])
        
        # Map audio from the silent source to ensure audio is always present
        # Silent audio input index depends on number of overlay inputs added above
        audio_input_index = 1 + (len(overlay_images) if overlay_images else 0)
        cmd.extend(['-map', f'{audio_input_index}:a'])
        
        if profile.codec == 'h264_v4l2m2m':
            # Pi 5 V4L2 hardware encoding
            cmd.extend([
                '-c:v', 'h264_v4l2m2m',
                '-num_output_buffers', '32',
                '-num_capture_buffers', '16',
            ])
        elif profile.codec == 'h264_videotoolbox':
            # Mac VideoToolbox hardware encoding
            cmd.extend([
                '-c:v', 'h264_videotoolbox',
                '-allow_sw', '1',
                '-realtime', '1',
            ])
        else:
            # Software encoding (libx264)
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', profile.preset,
                '-tune', 'zerolatency',
            ])
        
        # Common encoding parameters
        cmd.extend([
            '-r', str(profile.framerate),
            '-b:v', profile.bitrate,
            '-maxrate', profile.bitrate,
            '-bufsize', profile.buffer_size,
            '-g', str(profile.framerate * profile.keyframe_interval),  # Keyframe every N seconds
            '-profile:v', profile.profile,
            '-level', profile.level,
        ])
        
        # Audio encoding
        cmd.extend([
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
        ])
        
        # Output options
        cmd.extend([
            '-f', 'flv',  # FLV format for RTMP
        ])
        
        # Multiple outputs (tee for multi-destination)
        if len(output_urls) == 1:
            cmd.append(output_urls[0])
        else:
            # Use tee muxer for multiple destinations
            tee_outputs = '|'.join(output_urls)
            cmd.extend(['-f', 'tee', tee_outputs])
        
        return cmd
    
    async def _monitor_process(self, stream_id: int):
        """
        Monitor FFmpeg process output and update metrics.
        
        Parses FFmpeg stderr for:
        - Bitrate, framerate, dropped frames
        - Encoding time per frame
        - Errors and warnings
        """
        stream_process = self.processes[stream_id]
        process = stream_process.process
        
        if not process or not process.stderr:
            logger.error(f"No process stderr for stream {stream_id}")
            return
        
        logger.info(f"Started monitoring stream {stream_id}")
        
        # Keep last 20 lines of FFmpeg output for error diagnosis
        last_output_lines = []
        error_patterns = ['error', 'Error', 'ERROR', 'failed', 'Failed', 'timeout', 'Timeout', 'Connection refused', 'Connection reset']
        
        # Buffer for incomplete lines
        line_buffer = ""
        
        try:
            while not self._shutdown_event.is_set():
                # Read in chunks to avoid buffer overflow ("Separator not found")
                try:
                    chunk = await asyncio.wait_for(process.stderr.read(8192), timeout=60.0)
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        chunk = b''
                    else:
                        continue
                line = chunk
                
                if not line:
                    # Process ended - capture any remaining output before it dies
                    try:
                        # Try to read any remaining buffered output
                        remaining = await asyncio.wait_for(process.stderr.read(4096), timeout=0.5)
                        if remaining:
                            remaining_lines = remaining.decode('utf-8', errors='ignore').split('\n')
                            last_output_lines.extend([l.strip() for l in remaining_lines if l.strip()])
                    except (asyncio.TimeoutError, Exception):
                        pass
                    
                    # Process ended
                    returncode = await process.wait()
                    logger.warning(f"Stream {stream_id} process ended (exit code: {returncode})")
                    
                    # Log the last output lines to help diagnose the issue
                    if last_output_lines:
                        logger.error(f"Last FFmpeg output before stream {stream_id} died:")
                        for i, log_line in enumerate(last_output_lines[-20:], 1):  # Last 20 lines
                            logger.error(f"  [{i}] {log_line}")
                    
                    # Check for specific error patterns in the last output
                    error_found = False
                    for line in last_output_lines[-20:]:
                        for pattern in error_patterns:
                            if pattern in line:
                                logger.error(f"⚠️  Error pattern detected in FFmpeg output: '{pattern}' in: {line[:200]}")
                                error_found = True
                                break
                        if error_found:
                            break
                    
                    stream_process.status = StreamStatus.ERROR
                    error_msg = f"Process exited with code {returncode}"
                    if last_output_lines:
                        # Include last error line in error message if available
                        for line in reversed(last_output_lines[-10:]):
                            if any(pattern in line for pattern in error_patterns):
                                error_msg = f"Process exited with code {returncode}. Last error: {line[:200]}"
                                break
                    stream_process.last_error = error_msg
                    
                    # Check if stream should auto-restart by checking database status
                    should_restart = stream_process.should_auto_restart
                    
                    # Also check database - if stream is stopped in DB, don't restart
                    try:
                        from models.database import SessionLocal, Stream
                        db = SessionLocal()
                        db_stream = db.query(Stream).filter(Stream.id == stream_id).first()
                        if db_stream and db_stream.status == 'stopped':
                            logger.info(f"Stream {stream_id} is marked as stopped in database, not restarting")
                            should_restart = False
                        db.close()
                    except Exception as e:
                        logger.error(f"Failed to check database status for stream {stream_id}: {e}")
                    
                    # Only attempt restart if auto-restart is enabled AND database allows it
                    if should_restart:
                        logger.info(f"Auto-restart enabled for stream {stream_id}, attempting restart...")
                        try:
                            await self.restart_stream(stream_id)
                        except Exception as e:
                            logger.error(f"Failed to restart stream {stream_id}: {e}")
                    else:
                        logger.info(f"Auto-restart disabled for stream {stream_id}, not restarting")
                    
                    break
                
                # Parse output line
                line_str = line.decode('utf-8', errors='ignore').strip()
                
                # Keep last 20 lines for error diagnosis
                last_output_lines.append(line_str)
                if len(last_output_lines) > 20:
                    last_output_lines.pop(0)
                
                # Log errors and warnings immediately for visibility
                if any(pattern in line_str for pattern in error_patterns):
                    logger.warning(f"⚠️  FFmpeg [stream {stream_id}]: {line_str}")
                
                # Update metrics from FFmpeg output
                self._parse_ffmpeg_output(stream_id, line_str)
                
        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for stream {stream_id}")
            raise
        except Exception as e:
            logger.error(f"Error monitoring stream {stream_id}: {e}")
            stream_process.status = StreamStatus.ERROR
            stream_process.last_error = str(e)
    
    def _parse_ffmpeg_output(self, stream_id: int, line: str):
        """
        Parse FFmpeg stderr output to extract metrics.
        
        FFmpeg progress line format:
        frame= 1234 fps=30 q=28.0 size=   12345kB time=00:01:23.45 bitrate=1234.5kbits/s speed=1.00x
        """
        stream_process = self.processes.get(stream_id)
        if not stream_process:
            return
        
        metrics = stream_process.metrics
        
        try:
            # Extract frame rate
            fps_match = re.search(r'fps=\s*([\d.]+)', line)
            if fps_match:
                metrics.framerate_actual = float(fps_match.group(1))
            
            # Extract bitrate
            bitrate_match = re.search(r'bitrate=\s*([\d.]+)kbits/s', line)
            if bitrate_match:
                metrics.bitrate_current = float(bitrate_match.group(1)) / 1000  # Convert to Mbps
            
            # Extract dropped frames
            drop_match = re.search(r'drop=\s*(\d+)', line)
            if drop_match:
                metrics.dropped_frames = int(drop_match.group(1))
            
            # Extract encoding speed
            speed_match = re.search(r'speed=\s*([\d.]+)x', line)
            if speed_match:
                speed = float(speed_match.group(1))
                # Calculate encoding time per frame (inverse of speed)
                if speed > 0:
                    metrics.encoding_time_ms = (1000.0 / metrics.framerate_target) / speed
            
            # Calculate uptime
            if stream_process.started_at:
                metrics.uptime_seconds = int((datetime.utcnow() - stream_process.started_at).total_seconds())
            
            metrics.last_update = datetime.utcnow()
            
        except Exception as e:
            logger.debug(f"Error parsing FFmpeg output: {e}")
            # Don't fail on parse errors, just continue
    
    async def _graceful_shutdown(self, process: asyncio.subprocess.Process, graceful: bool = True):
        """
        Gracefully shutdown FFmpeg process.
        
        Process:
        1. Send SIGTERM (if graceful)
        2. Wait up to 5 seconds
        3. Send SIGKILL if still running
        """
        if not process:
            return
        
        try:
            if graceful:
                # Try graceful shutdown first
                process.terminate()  # SIGTERM
                
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                    logger.debug(f"Process {process.pid} terminated gracefully")
                    return
                except asyncio.TimeoutError:
                    logger.warning(f"Process {process.pid} did not respond to SIGTERM, sending SIGKILL")
            
            # Force kill
            process.kill()  # SIGKILL
            await process.wait()
            logger.debug(f"Process {process.pid} killed")
            
        except ProcessLookupError:
            # Process already dead
            pass
        except Exception as e:
            logger.error(f"Error shutting down process: {e}")
    
    def find_stream_by_destination_url(self, destination_url: str) -> Optional[int]:
        """
        Find a running stream that's streaming to a specific destination URL.
        
        Args:
            destination_url: RTMP URL to search for (e.g., rtmp://a.rtmp.youtube.com/live2/key)
            
        Returns:
            Stream ID if found, None otherwise
        """
        for stream_id, stream_process in self.processes.items():
            if stream_process.status == StreamStatus.RUNNING:
                if destination_url in stream_process.output_urls:
                    return stream_id
        return None

