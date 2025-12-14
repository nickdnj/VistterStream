"""
Local Stream Watchdog Service
Monitors FFmpeg encoder health and automatically recovers from failures.

This simplified watchdog:
1. Monitors FFmpeg process health (CPU, memory, running state)
2. Detects when encoder has stopped or is unresponsive
3. Automatically restarts the encoder on failure
4. Logs all actions for debugging
5. Does NOT require YouTube API (local monitoring only)
"""

import asyncio
import logging
import psutil
import aiohttp
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class StreamHealthState:
    """Track stream health state over time"""
    
    def __init__(self, unhealthy_threshold: int = 3):
        """
        Initialize health state tracker
        
        Args:
            unhealthy_threshold: Number of consecutive unhealthy checks before recovery
        """
        self.unhealthy_threshold = unhealthy_threshold
        self.consecutive_unhealthy = 0
        self.last_healthy_time: Optional[datetime] = None
        self.last_recovery_time: Optional[datetime] = None
        self.recovery_count = 0
    
    def mark_healthy(self):
        """Mark stream as healthy"""
        self.consecutive_unhealthy = 0
        self.last_healthy_time = datetime.utcnow()
    
    def mark_unhealthy(self) -> bool:
        """
        Mark stream as unhealthy
        
        Returns:
            True if threshold reached and recovery should be triggered
        """
        self.consecutive_unhealthy += 1
        return self.consecutive_unhealthy >= self.unhealthy_threshold
    
    def mark_recovery(self):
        """Mark that recovery was attempted"""
        self.last_recovery_time = datetime.utcnow()
        self.recovery_count += 1
        self.consecutive_unhealthy = 0
    
    def should_allow_recovery(self, cooldown_seconds: int = 120) -> bool:
        """
        Check if enough time has passed since last recovery to allow another
        
        Args:
            cooldown_seconds: Minimum seconds between recovery attempts
            
        Returns:
            True if recovery is allowed
        """
        if not self.last_recovery_time:
            return True
        
        elapsed = (datetime.utcnow() - self.last_recovery_time).total_seconds()
        return elapsed >= cooldown_seconds


class LocalStreamWatchdog:
    """
    Local watchdog service for monitoring FFmpeg encoder health
    
    This version monitors the local encoder process without needing YouTube API.
    """
    
    def __init__(
        self,
        destination_id: int,
        destination_name: str,
        stream_id: int,
        check_interval: int = 30,
        youtube_channel_live_url: Optional[str] = None
    ):
        """
        Initialize the local watchdog
        
        Args:
            destination_id: ID of the streaming destination
            destination_name: Name of the destination
            stream_id: ID of the active stream
            check_interval: Seconds between health checks
            youtube_channel_live_url: Optional YouTube channel /live URL to check stream status
        """
        self.destination_id = destination_id
        self.destination_name = destination_name
        self.stream_id = stream_id
        self.check_interval = check_interval
        self.youtube_channel_live_url = youtube_channel_live_url
        
        self.health_state = StreamHealthState(unhealthy_threshold=3)
        self.running = False
        
        self.logger = logging.getLogger(f'watchdog.dest{destination_id}')
    
    async def start(self):
        """Start the watchdog service"""
        self.logger.info("=" * 60)
        self.logger.info(f"Local Stream Watchdog Starting")
        self.logger.info("=" * 60)
        self.logger.info(f"Destination ID: {self.destination_id}")
        self.logger.info(f"Destination Name: {self.destination_name}")
        self.logger.info(f"Stream ID: {self.stream_id}")
        self.logger.info(f"Check Interval: {self.check_interval}s")
        self.logger.info(f"YouTube Live Check: {'Enabled' if self.youtube_channel_live_url else 'Disabled'}")
        self.logger.info("=" * 60)
        
        self.running = True
        
        try:
            while self.running:
                try:
                    await self.check_and_recover()
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in watchdog loop: {e}", exc_info=True)
                    await asyncio.sleep(self.check_interval)
                    
        except asyncio.CancelledError:
            self.logger.info("Watchdog stopped by cancellation")
        except Exception as e:
            self.logger.error(f"Fatal error in watchdog: {e}", exc_info=True)
        finally:
            self.running = False
            self.logger.info("Watchdog service stopped")
    
    async def check_and_recover(self):
        """Main health check and recovery logic"""
        try:
            # Import here to avoid circular imports
            from services.timeline_executor import get_timeline_executor
            from services.ffmpeg_manager import StreamStatus
            
            # Get the timeline executor instance
            executor = get_timeline_executor()
            
            # Check if the timeline has an FFmpeg manager
            if self.stream_id not in executor.ffmpeg_managers:
                self.logger.warning(f"Stream {self.stream_id} has no FFmpeg manager (timeline may have stopped)")
                is_healthy = False
            else:
                ffmpeg_manager = executor.ffmpeg_managers[self.stream_id]
                
                # Check if stream exists in the manager's processes
                if self.stream_id not in ffmpeg_manager.processes:
                    self.logger.warning(f"Stream {self.stream_id} is not in FFmpeg manager processes")
                    is_healthy = False
                else:
                    stream_process = ffmpeg_manager.processes[self.stream_id]
                    
                    # Check stream status
                    if stream_process.status != StreamStatus.RUNNING:
                        self.logger.warning(f"Stream {self.stream_id} status is {stream_process.status}")
                        is_healthy = False
                    elif not stream_process.process:
                        self.logger.warning(f"Stream {self.stream_id} has no process object")
                        is_healthy = False
                    else:
                        # Get PID from the process
                        pid = stream_process.process.pid
                        
                        # Check if process exists and is responsive
                        try:
                            process = psutil.Process(pid)
                            
                            # Check if process is running (not zombie)
                            if process.status() == psutil.STATUS_ZOMBIE:
                                self.logger.warning(f"Stream {self.stream_id} process is zombie (PID: {pid})")
                                is_healthy = False
                            else:
                                # Process is running normally
                                cpu_percent = process.cpu_percent(interval=0.1)
                                memory_mb = process.memory_info().rss / 1024 / 1024
                                
                                self.logger.info(
                                    f"Stream {self.stream_id} healthy - "
                                    f"PID: {pid}, CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB"
                                )
                                is_healthy = True
                                
                        except psutil.NoSuchProcess:
                            self.logger.warning(f"Stream {self.stream_id} process not found (PID: {pid})")
                            is_healthy = False
                        except psutil.AccessDenied:
                            self.logger.warning(f"Access denied to stream {self.stream_id} process (PID: {pid})")
                            # Assume healthy if we can't check (don't want false alarms)
                            is_healthy = True
                        except Exception as e:
                            self.logger.error(f"Error checking process health: {e}")
                            is_healthy = False
            
            # Optional: Check if YouTube actually shows the stream as live
            if is_healthy and self.youtube_channel_live_url:
                youtube_live = await self._check_youtube_live()
                if not youtube_live:
                    self.logger.warning(
                        f"FFmpeg is running but YouTube shows stream as offline at {self.youtube_channel_live_url}"
                    )
                    is_healthy = False
            
            # Check timeline progress (detect stalled timeline even if FFmpeg is healthy)
            if is_healthy:
                stall_threshold = 300  # 5 minutes without segment progress
                if self.stream_id in executor._last_segment_time:
                    last_progress = executor._last_segment_time[self.stream_id]
                    stall_duration = (datetime.utcnow() - last_progress).total_seconds()
                    if stall_duration > stall_threshold:
                        self.logger.warning(
                            f"Timeline {self.stream_id} appears stalled - no segment progress for {stall_duration:.0f}s "
                            f"(threshold: {stall_threshold}s)"
                        )
                        is_healthy = False
                    else:
                        self.logger.debug(f"Timeline {self.stream_id} last segment: {stall_duration:.0f}s ago")
            
            # Update health state
            if is_healthy:
                self.health_state.mark_healthy()
                return
            
            # Stream is unhealthy
            should_recover = self.health_state.mark_unhealthy()
            
            if should_recover and self.health_state.should_allow_recovery():
                self.logger.warning(
                    f"Stream unhealthy for {self.health_state.consecutive_unhealthy} consecutive checks - "
                    f"triggering recovery"
                )
                await self.recover_stream()
            elif should_recover:
                self.logger.warning(
                    f"Stream unhealthy but recovery on cooldown (last recovery: "
                    f"{self.health_state.last_recovery_time})"
                )
            else:
                self.logger.warning(
                    f"Stream unhealthy ({self.health_state.consecutive_unhealthy}/"
                    f"{self.health_state.unhealthy_threshold} checks)"
                )
                
        except Exception as e:
            self.logger.error(f"Unexpected error during health check: {e}", exc_info=True)
    
    async def _check_youtube_live(self) -> bool:
        """
        Check if YouTube shows the stream as live by requesting the watch URL
        
        Returns:
            True if stream appears to be live, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.youtube_channel_live_url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    allow_redirects=True,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                ) as response:
                    final_url = str(response.url)
                    text = await response.text()
                    
                    # Offline indicators - these mean stream is NOT live
                    offline_indicators = [
                        '"isLive":false',
                        'This video is unavailable',
                        'This live stream recording is not available',
                        'Video unavailable',
                        '"playabilityStatus":{"status":"LIVE_STREAM_OFFLINE"',
                        '"playabilityStatus":{"status":"ERROR"',
                        'This video has been removed',
                        'This video is private',
                        'Scheduled for',
                        '"status":"LIVE_STREAM_OFFLINE"',
                        '"status":"ERROR"',
                        'is offline',
                        'stream has ended',
                        'Stream offline',
                    ]
                    
                    # Check for offline indicators first (higher priority)
                    is_offline = any(indicator.lower() in text.lower() for indicator in offline_indicators)
                    if is_offline:
                        self.logger.warning(f"YouTube shows stream as OFFLINE (found offline indicator)")
                        return False
                    
                    # Check if we're on a valid video page
                    if '/live' in final_url or '/watch?v=' in final_url:
                        # Look for common indicators that stream is live
                        live_indicators = [
                            '"isLive":true',
                            '"isLiveContent":true',
                            'watching now',
                            'Started streaming',
                            '"isLiveNow":true',
                        ]
                        
                        is_live = any(indicator in text for indicator in live_indicators)
                        
                        if is_live:
                            self.logger.debug(f"YouTube live check: Stream is LIVE")
                            return True
                        else:
                            self.logger.warning(f"YouTube live check: No live indicators found - stream may be OFFLINE")
                            return False
                    else:
                        self.logger.warning(
                            f"YouTube live check: Redirected to {final_url} (stream offline)"
                        )
                        return False
                        
        except asyncio.TimeoutError:
            self.logger.warning("YouTube live check timed out")
            # Don't mark as unhealthy on timeout - might be network issue
            return True
        except Exception as e:
            self.logger.error(f"Error checking YouTube live status: {e}")
            # Don't mark as unhealthy on errors - might be temporary
            return True
    
    async def recover_stream(self):
        """
        Attempt to recover the stream
        
        Recovery strategy:
        1. Stop the existing FFmpeg process
        2. Wait a moment for cleanup
        3. The timeline executor will automatically restart it
        
        Note: For timeline-based streams, we just restart the FFmpeg process.
        The timeline executor manages the overall timeline execution.
        """
        self.health_state.mark_recovery()
        recovery_num = self.health_state.recovery_count
        
        self.logger.warning(f"=== RECOVERY ATTEMPT #{recovery_num} for Stream {self.stream_id} ===")
        
        try:
            # Import here to avoid circular imports
            from services.timeline_executor import get_timeline_executor
            
            executor = get_timeline_executor()
            
            # Check if the timeline has an FFmpeg manager
            if self.stream_id not in executor.ffmpeg_managers:
                self.logger.error(f"Stream {self.stream_id} has no FFmpeg manager - cannot recover")
                return
            
            ffmpeg_manager = executor.ffmpeg_managers[self.stream_id]
            
            # Stop the stream if it's running
            if self.stream_id in ffmpeg_manager.processes:
                self.logger.info(f"Stopping FFmpeg process for stream {self.stream_id}")
                await ffmpeg_manager.stop_stream(self.stream_id, graceful=False)
                await asyncio.sleep(3)
                self.logger.info(f"FFmpeg process stopped, timeline executor will restart it")
            else:
                self.logger.warning(f"Stream {self.stream_id} not in ffmpeg_manager.processes")
                
        except Exception as e:
            self.logger.error(f"Failed to recover stream: {e}", exc_info=True)
    
    def stop(self):
        """Stop the watchdog service"""
        self.logger.info("Stopping watchdog service...")
        self.running = False

