"""
Watchdog Manager Service
Manages multiple YouTube stream watchdog instances, one per destination
"""

import asyncio
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from services.youtube_stream_watchdog import YouTubeStreamWatchdog
from models.destination import StreamingDestination

logger = logging.getLogger(__name__)


class WatchdogManager:
    """
    Manages multiple watchdog instances
    
    Each YouTube destination with watchdog enabled gets its own
    YouTubeStreamWatchdog instance running concurrently.
    """
    
    def __init__(self):
        """Initialize watchdog manager"""
        self.watchdogs: Dict[int, YouTubeStreamWatchdog] = {}
        self.watchdog_tasks: Dict[int, asyncio.Task] = {}
        self.running = False
    
    async def start(self, db_session: Session):
        """
        Start watchdog manager and load all enabled watchdogs
        
        Args:
            db_session: Database session to query destinations
        """
        logger.info("Starting Watchdog Manager")
        self.running = True
        
        # Load all YouTube destinations with watchdog enabled
        destinations = db_session.query(StreamingDestination).filter(
            StreamingDestination.platform == "youtube",
            StreamingDestination.enable_watchdog == True,
            StreamingDestination.is_active == True
        ).all()
        
        logger.info(f"Found {len(destinations)} destination(s) with watchdog enabled")
        
        for dest in destinations:
            await self.start_watchdog(dest)
        
        logger.info("Watchdog Manager started successfully")
    
    async def start_watchdog(self, destination: StreamingDestination):
        """
        Start watchdog for a specific destination
        
        Args:
            destination: Destination to monitor
        """
        dest_id = destination.id
        
        # Check if already running
        if dest_id in self.watchdogs:
            logger.warning(f"Watchdog already running for destination {dest_id} ({destination.name})")
            return
        
        # Validate configuration
        if not self._validate_destination_config(destination):
            logger.error(f"Invalid watchdog configuration for destination {dest_id} ({destination.name})")
            return
        
        # Get API key (use destination-specific or fall back to system-wide)
        api_key = destination.youtube_api_key
        if not api_key:
            import os
            api_key = os.getenv('YOUTUBE_API_KEY')
        
        if not api_key:
            logger.error(f"No API key available for destination {dest_id} ({destination.name})")
            return
        
        try:
            # Create watchdog instance
            watchdog = YouTubeStreamWatchdog(
                youtube_api_key=api_key,
                stream_id=destination.youtube_stream_id,
                broadcast_id=destination.youtube_broadcast_id,
                watch_url=destination.youtube_watch_url,
                encoder_service_name=f"vistterstream-encoder-{dest_id}",  # Per-destination service
                check_interval=destination.watchdog_check_interval or 30,
                enable_frame_probe=destination.watchdog_enable_frame_probe or False,
                enable_daily_reset=destination.watchdog_enable_daily_reset or False,
                daily_reset_hour=destination.watchdog_daily_reset_hour or 3
            )
            
            # Store instance
            self.watchdogs[dest_id] = watchdog
            
            # Start watchdog in background task
            task = asyncio.create_task(watchdog.start())
            self.watchdog_tasks[dest_id] = task
            
            logger.info(f"Started watchdog for destination {dest_id} ({destination.name})")
            
        except Exception as e:
            logger.error(f"Failed to start watchdog for destination {dest_id}: {e}", exc_info=True)
    
    async def stop_watchdog(self, destination_id: int):
        """
        Stop watchdog for a specific destination
        
        Args:
            destination_id: Destination ID
        """
        if destination_id not in self.watchdogs:
            logger.warning(f"No watchdog running for destination {destination_id}")
            return
        
        try:
            # Stop the watchdog
            watchdog = self.watchdogs[destination_id]
            watchdog.stop()
            
            # Cancel the task
            task = self.watchdog_tasks.get(destination_id)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Remove from tracking
            del self.watchdogs[destination_id]
            if destination_id in self.watchdog_tasks:
                del self.watchdog_tasks[destination_id]
            
            logger.info(f"Stopped watchdog for destination {destination_id}")
            
        except Exception as e:
            logger.error(f"Error stopping watchdog for destination {destination_id}: {e}", exc_info=True)
    
    async def restart_watchdog(self, destination: StreamingDestination):
        """
        Restart watchdog for a destination
        
        Args:
            destination: Destination to restart watchdog for
        """
        await self.stop_watchdog(destination.id)
        await asyncio.sleep(1)
        await self.start_watchdog(destination)
    
    async def reload_from_db(self, db_session: Session):
        """
        Reload watchdog configuration from database
        
        Stops watchdogs that are no longer enabled,
        starts watchdogs that are newly enabled,
        restarts watchdogs with configuration changes.
        
        Args:
            db_session: Database session
        """
        logger.info("Reloading watchdog configuration from database")
        
        # Get all YouTube destinations with watchdog enabled
        enabled_destinations = db_session.query(StreamingDestination).filter(
            StreamingDestination.platform == "youtube",
            StreamingDestination.enable_watchdog == True,
            StreamingDestination.is_active == True
        ).all()
        
        enabled_ids = {dest.id for dest in enabled_destinations}
        running_ids = set(self.watchdogs.keys())
        
        # Stop watchdogs that should no longer run
        to_stop = running_ids - enabled_ids
        for dest_id in to_stop:
            logger.info(f"Stopping watchdog for destination {dest_id} (no longer enabled)")
            await self.stop_watchdog(dest_id)
        
        # Start new watchdogs
        to_start = enabled_ids - running_ids
        for dest in enabled_destinations:
            if dest.id in to_start:
                logger.info(f"Starting new watchdog for destination {dest.id} ({dest.name})")
                await self.start_watchdog(dest)
        
        logger.info("Watchdog configuration reload complete")
    
    def get_watchdog_status(self, destination_id: int) -> Dict:
        """
        Get status of watchdog for a destination
        
        Args:
            destination_id: Destination ID
            
        Returns:
            Status dictionary
        """
        if destination_id not in self.watchdogs:
            return {
                "running": False,
                "message": "Watchdog not running"
            }
        
        watchdog = self.watchdogs[destination_id]
        health_state = watchdog.health_state
        
        return {
            "running": True,
            "consecutive_unhealthy": health_state.consecutive_unhealthy,
            "last_healthy_time": health_state.last_healthy_time.isoformat() if health_state.last_healthy_time else None,
            "last_recovery_time": health_state.last_recovery_time.isoformat() if health_state.last_recovery_time else None,
            "recovery_count": health_state.recovery_count,
            "check_interval": watchdog.check_interval,
            "frame_probe_enabled": watchdog.enable_frame_probe,
            "daily_reset_enabled": watchdog.enable_daily_reset
        }
    
    def get_all_statuses(self) -> Dict[int, Dict]:
        """
        Get status of all running watchdogs
        
        Returns:
            Dictionary mapping destination_id to status
        """
        return {
            dest_id: self.get_watchdog_status(dest_id)
            for dest_id in self.watchdogs.keys()
        }
    
    async def stop_all(self):
        """Stop all watchdogs"""
        logger.info("Stopping all watchdogs")
        self.running = False
        
        for dest_id in list(self.watchdogs.keys()):
            await self.stop_watchdog(dest_id)
        
        logger.info("All watchdogs stopped")
    
    def _validate_destination_config(self, destination: StreamingDestination) -> bool:
        """
        Validate that destination has required watchdog configuration
        
        Args:
            destination: Destination to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'youtube_stream_id',
            'youtube_broadcast_id',
            'youtube_watch_url'
        ]
        
        for field in required_fields:
            value = getattr(destination, field, None)
            if not value:
                logger.error(f"Destination {destination.id} missing required field: {field}")
                return False
        
        return True


# Global watchdog manager instance
_watchdog_manager: Optional[WatchdogManager] = None


def get_watchdog_manager() -> WatchdogManager:
    """Get the global watchdog manager instance"""
    global _watchdog_manager
    if _watchdog_manager is None:
        _watchdog_manager = WatchdogManager()
    return _watchdog_manager

