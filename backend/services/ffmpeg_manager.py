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
        profile: Optional[EncodingProfile] = None
    ) -> StreamProcess:
        """
        Start a new FFmpeg stream process.
        
        Args:
            stream_id: Unique stream identifier
            input_url: RTSP/RTMP input URL (camera feed)
            output_urls: List of RTMP output destinations
            profile: Encoding profile (uses reliability profile if None)
        
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
        
        # Build FFmpeg command
        command = self._build_ffmpeg_command(input_url, output_urls, profile)
        
        # Create stream process entry
        stream_process = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.STARTING,
            started_at=datetime.utcnow(),
            command=command
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
        profile: EncodingProfile
    ) -> List[str]:
        """
        Build FFmpeg command with hardware acceleration.
        
        References:
            See StreamingPipeline-TechnicalSpec.md §"FFmpeg Strategy"
        """
        cmd = ['ffmpeg']
        
        # Input options
        cmd.extend([
            '-re',  # Read input at native framerate
            '-timeout', '2000000',  # 2 second timeout (microseconds)
            '-i', input_url
        ])
        
        # Video encoding options
        resolution_str = f"{profile.resolution[0]}x{profile.resolution[1]}"
        
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
            '-s', resolution_str,
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
            cmd.extend(['-f', 'tee', '-map', '0:v', '-map', '0:a', tee_outputs])
        
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
        
        try:
            while not self._shutdown_event.is_set():
                # Read line from stderr
                line = await process.stderr.readline()
                
                if not line:
                    # Process ended
                    returncode = await process.wait()
                    logger.warning(f"Stream {stream_id} process ended (exit code: {returncode})")
                    
                    stream_process.status = StreamStatus.ERROR
                    stream_process.last_error = f"Process exited with code {returncode}"
                    
                    # Attempt restart
                    try:
                        await self.restart_stream(stream_id)
                    except Exception as e:
                        logger.error(f"Failed to restart stream {stream_id}: {e}")
                    
                    break
                
                # Parse output line
                line_str = line.decode('utf-8', errors='ignore').strip()
                
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

