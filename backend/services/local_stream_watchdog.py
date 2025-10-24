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
            from services.ffmpeg_manager import get_ffmpeg_manager
            
            ffmpeg_manager = get_ffmpeg_manager()
            
            # Check if stream is running
            is_running = ffmpeg_manager.is_stream_running(self.stream_id)
            
            if not is_running:
                self.logger.warning(f"Stream {self.stream_id} is not running")
                is_healthy = False
            else:
                # Get stream process info
                process_info = ffmpeg_manager.get_stream_process_info(self.stream_id)
                
                if not process_info:
                    self.logger.warning(f"Could not get process info for stream {self.stream_id}")
                    is_healthy = False
                else:
                    # Check if process is actually alive and responding
                    pid = process_info.get('pid')
                    
                    if not pid:
                        self.logger.warning(f"Stream {self.stream_id} has no PID")
                        is_healthy = False
                    else:
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
        Check if YouTube shows the stream as live by requesting the channel /live URL
        
        Returns:
            True if stream appears to be live, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.youtube_channel_live_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True
                ) as response:
                    # If we get redirected to the home page or channel page (not /live), stream is offline
                    final_url = str(response.url)
                    
                    # Check if we're still on a /live URL (indicates stream is live)
                    if '/live' in final_url or '/watch?v=' in final_url:
                        # Check page content for live indicators
                        text = await response.text()
                        
                        # Look for common indicators that stream is live
                        live_indicators = [
                            '"isLive":true',
                            '"isLiveContent":true',
                            'watching now',
                            'Started streaming'
                        ]
                        
                        is_live = any(indicator in text for indicator in live_indicators)
                        
                        if is_live:
                            self.logger.debug(f"YouTube live check: Stream is LIVE")
                        else:
                            self.logger.warning(f"YouTube live check: Stream appears OFFLINE")
                        
                        return is_live
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
        1. Stop the existing stream (if still running)
        2. Wait a moment for cleanup
        3. Restart the stream
        """
        self.health_state.mark_recovery()
        recovery_num = self.health_state.recovery_count
        
        self.logger.warning(f"=== RECOVERY ATTEMPT #{recovery_num} for Stream {self.stream_id} ===")
        
        try:
            # Import here to avoid circular imports
            from services.ffmpeg_manager import get_ffmpeg_manager
            from services.stream_service import StreamService
            from models.database import get_db
            
            ffmpeg_manager = get_ffmpeg_manager()
            
            # Stop the stream if it's running
            if ffmpeg_manager.is_stream_running(self.stream_id):
                self.logger.info(f"Stopping stream {self.stream_id}")
                ffmpeg_manager.stop_stream(self.stream_id)
                await asyncio.sleep(2)
            
            # Get stream configuration from database
            db = next(get_db())
            try:
                stream_service = StreamService(db)
                stream_data = stream_service.get_stream(self.stream_id)
                
                if not stream_data:
                    self.logger.error(f"Stream {self.stream_id} not found in database")
                    return
                
                # Restart the stream
                self.logger.info(f"Restarting stream {self.stream_id}")
                await stream_service.start_stream(self.stream_id)
                
                self.logger.info(f"Stream {self.stream_id} restarted successfully")
                
                # Give it some time to stabilize
                await asyncio.sleep(10)
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Failed to recover stream: {e}", exc_info=True)
    
    def stop(self):
        """Stop the watchdog service"""
        self.logger.info("Stopping watchdog service...")
        self.running = False

