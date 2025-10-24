"""
YouTube Stream Watchdog Service
Monitors YouTube Live stream health and automatically recovers from zombie states.

This service:
1. Checks YouTube API stream health every 30 seconds
2. Detects when stream is stuck (green status but no frames)
3. Attempts local encoder restart first
4. Falls back to YouTube API broadcast reset if needed
5. Logs all actions for debugging
6. Runs continuously as a systemd service
"""

import os
import sys
import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from services.youtube_api_helper import YouTubeAPIHelper, YouTubeAPIError


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


class YouTubeStreamWatchdog:
    """Main watchdog service for monitoring and recovering YouTube streams"""
    
    def __init__(
        self,
        youtube_api_key: str,
        stream_id: str,
        broadcast_id: str,
        watch_url: str,
        encoder_service_name: str = 'vistterstream-encoder',
        check_interval: int = 30,
        enable_frame_probe: bool = False,
        enable_daily_reset: bool = False,
        daily_reset_hour: int = 3
    ):
        """
        Initialize the watchdog
        
        Args:
            youtube_api_key: YouTube Data API v3 key
            stream_id: YouTube stream ID
            broadcast_id: YouTube broadcast ID
            watch_url: YouTube watch URL for frame probing
            encoder_service_name: Name of systemd service running the encoder
            check_interval: Seconds between health checks
            enable_frame_probe: Whether to probe actual video frames (requires yt-dlp)
            enable_daily_reset: Whether to do a daily broadcast reset
            daily_reset_hour: Hour (0-23) to perform daily reset
        """
        self.api_key = youtube_api_key
        self.stream_id = stream_id
        self.broadcast_id = broadcast_id
        self.watch_url = watch_url
        self.encoder_service_name = encoder_service_name
        self.check_interval = check_interval
        self.enable_frame_probe = enable_frame_probe
        self.enable_daily_reset = enable_daily_reset
        self.daily_reset_hour = daily_reset_hour
        
        self.health_state = StreamHealthState(unhealthy_threshold=3)
        self.api: Optional[YouTubeAPIHelper] = None
        self.running = False
        self.last_daily_reset: Optional[datetime] = None
        
        # Configure logging
        self.logger = logging.getLogger('watchdog')
    
    async def start(self):
        """Start the watchdog service"""
        self.logger.info("=" * 60)
        self.logger.info("YouTube Stream Watchdog Starting")
        self.logger.info("=" * 60)
        self.logger.info(f"Stream ID: {self.stream_id}")
        self.logger.info(f"Broadcast ID: {self.broadcast_id}")
        self.logger.info(f"Encoder Service: {self.encoder_service_name}")
        self.logger.info(f"Check Interval: {self.check_interval}s")
        self.logger.info(f"Frame Probe: {'Enabled' if self.enable_frame_probe else 'Disabled'}")
        self.logger.info(f"Daily Reset: {'Enabled' if self.enable_daily_reset else 'Disabled'}")
        self.logger.info("=" * 60)
        
        self.running = True
        self.api = YouTubeAPIHelper(self.api_key)
        
        try:
            async with self.api:
                while self.running:
                    try:
                        await self.check_and_recover()
                        
                        if self.enable_daily_reset:
                            await self.check_daily_reset()
                        
                        await asyncio.sleep(self.check_interval)
                        
                    except Exception as e:
                        self.logger.error(f"Error in watchdog loop: {e}", exc_info=True)
                        await asyncio.sleep(self.check_interval)
                        
        except KeyboardInterrupt:
            self.logger.info("Watchdog stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in watchdog: {e}", exc_info=True)
        finally:
            self.running = False
            self.logger.info("Watchdog service stopped")
    
    async def check_and_recover(self):
        """Main health check and recovery logic"""
        try:
            # Check stream health via API
            health = await self.api.get_stream_health(self.stream_id)
            
            status = health['status']
            stream_status = health['stream_status']
            
            self.logger.info(
                f"Health check: status={status}, stream_status={stream_status}, "
                f"consecutive_unhealthy={self.health_state.consecutive_unhealthy}"
            )
            
            # Determine if stream is healthy
            is_healthy = self._evaluate_health(health)
            
            # Optional: Probe for actual video frames
            if is_healthy and self.enable_frame_probe:
                frames_ok = await self.api.probe_stream_frames(self.watch_url, timeout=20)
                if not frames_ok:
                    self.logger.warning("Frame probe failed - no video detected despite good health status")
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
                
        except YouTubeAPIError as e:
            self.logger.error(f"YouTube API error during health check: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during health check: {e}", exc_info=True)
    
    def _evaluate_health(self, health: Dict) -> bool:
        """
        Evaluate if stream is healthy based on API response
        
        Args:
            health: Health data from YouTube API
            
        Returns:
            True if healthy, False otherwise
        """
        status = health['status']
        stream_status = health['stream_status']
        
        # Good or ok status is healthy
        if status in ('good', 'ok'):
            return True
        
        # Bad status is definitely unhealthy
        if status == 'bad':
            return False
        
        # noData is concerning but might be temporary
        if status == 'noData':
            # If stream is supposed to be active, this is unhealthy
            if stream_status == 'active':
                return False
            # Otherwise might just be starting up
            return True
        
        # Unknown status - treat as unhealthy
        return False
    
    async def recover_stream(self):
        """
        Attempt to recover the stream
        
        Recovery strategy:
        1. First attempt: Restart encoder service
        2. Second attempt: Restart encoder service again
        3. Third attempt: Reset broadcast via YouTube API
        """
        self.health_state.mark_recovery()
        recovery_num = self.health_state.recovery_count
        
        self.logger.warning(f"=== RECOVERY ATTEMPT #{recovery_num} ===")
        
        # For first two attempts, try restarting encoder
        if recovery_num <= 2:
            success = await self.restart_encoder()
            if success:
                self.logger.info("Encoder restarted successfully - monitoring for recovery")
                # Give it some time to reconnect
                await asyncio.sleep(15)
            else:
                self.logger.error("Failed to restart encoder")
        
        # For third and subsequent attempts, do YouTube API reset
        else:
            self.logger.warning("Multiple encoder restarts failed - attempting YouTube API reset")
            try:
                await self.api.reset_broadcast(self.broadcast_id)
                self.logger.info("Broadcast reset via API - waiting for encoder to reconnect")
                await asyncio.sleep(20)
            except YouTubeAPIError as e:
                self.logger.error(f"Failed to reset broadcast: {e}")
    
    async def restart_encoder(self) -> bool:
        """
        Restart the encoder service
        
        Returns:
            True if restart succeeded, False otherwise
        """
        self.logger.info(f"Restarting encoder service: {self.encoder_service_name}")
        
        try:
            # Use systemctl to restart the service
            result = subprocess.run(
                ['systemctl', 'restart', self.encoder_service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info("Encoder service restart command succeeded")
                return True
            else:
                self.logger.error(
                    f"Encoder restart failed: {result.returncode}\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Encoder restart timed out")
            return False
        except FileNotFoundError:
            self.logger.error("systemctl not found - cannot restart encoder")
            return False
        except Exception as e:
            self.logger.error(f"Error restarting encoder: {e}", exc_info=True)
            return False
    
    async def check_daily_reset(self):
        """
        Check if it's time for daily broadcast reset
        
        This prevents long-running broadcasts from accumulating drift or issues.
        """
        now = datetime.utcnow()
        
        # Check if we're in the reset hour
        if now.hour != self.daily_reset_hour:
            return
        
        # Check if we've already done reset today
        if self.last_daily_reset and \
           self.last_daily_reset.date() == now.date():
            return
        
        self.logger.info(f"Performing daily broadcast reset at {now}")
        
        try:
            await self.api.reset_broadcast(self.broadcast_id)
            self.last_daily_reset = now
            self.logger.info("Daily broadcast reset complete")
            
            # Give encoder time to reconnect
            await asyncio.sleep(20)
            
        except YouTubeAPIError as e:
            self.logger.error(f"Daily broadcast reset failed: {e}")
    
    def stop(self):
        """Stop the watchdog service"""
        self.logger.info("Stopping watchdog service...")
        self.running = False


def setup_logging(log_file: str = '/var/log/vistterstream-watchdog.log'):
    """
    Configure logging for the watchdog
    
    Args:
        log_file: Path to log file
    """
    # Create log directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)


def load_config() -> Dict:
    """
    Load configuration from environment variables
    
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = [
        'YOUTUBE_API_KEY',
        'YOUTUBE_STREAM_ID',
        'YOUTUBE_BROADCAST_ID',
        'YOUTUBE_WATCH_URL'
    ]
    
    config = {}
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        config[var.lower()] = value
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Optional config
    config['encoder_service_name'] = os.getenv('ENCODER_SERVICE_NAME', 'vistterstream-encoder')
    config['check_interval'] = int(os.getenv('WATCHDOG_CHECK_INTERVAL', '30'))
    config['enable_frame_probe'] = os.getenv('WATCHDOG_ENABLE_FRAME_PROBE', 'false').lower() == 'true'
    config['enable_daily_reset'] = os.getenv('WATCHDOG_ENABLE_DAILY_RESET', 'false').lower() == 'true'
    config['daily_reset_hour'] = int(os.getenv('WATCHDOG_DAILY_RESET_HOUR', '3'))
    config['log_file'] = os.getenv('WATCHDOG_LOG_FILE', '/var/log/vistterstream-watchdog.log')
    
    return config


async def main():
    """Main entry point"""
    try:
        # Load configuration
        config = load_config()
        
        # Setup logging
        setup_logging(config['log_file'])
        logger = logging.getLogger('watchdog')
        
        # Create and start watchdog
        watchdog = YouTubeStreamWatchdog(
            youtube_api_key=config['youtube_api_key'],
            stream_id=config['youtube_stream_id'],
            broadcast_id=config['youtube_broadcast_id'],
            watch_url=config['youtube_watch_url'],
            encoder_service_name=config['encoder_service_name'],
            check_interval=config['check_interval'],
            enable_frame_probe=config['enable_frame_probe'],
            enable_daily_reset=config['enable_daily_reset'],
            daily_reset_hour=config['daily_reset_hour']
        )
        
        await watchdog.start()
        
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

