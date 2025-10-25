"""
Watchdog Manager Service
Manages multiple stream watchdog instances, one per destination
"""

import asyncio
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from services.local_stream_watchdog import LocalStreamWatchdog
from models.destination import StreamingDestination

logger = logging.getLogger(__name__)


class WatchdogManager:
    """
    Manages multiple watchdog instances
    
    Each destination with watchdog enabled gets its own
    LocalStreamWatchdog instance running concurrently.
    """
    
    def __init__(self):
        """Initialize watchdog manager"""
        self.watchdogs: Dict[int, LocalStreamWatchdog] = {}
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
        
        # Load all destinations with watchdog enabled
        destinations = db_session.query(StreamingDestination).filter(
            StreamingDestination.enable_watchdog == True,
            StreamingDestination.is_active == True
        ).all()
        
        logger.info(f"Found {len(destinations)} destination(s) with watchdog enabled")
        
        # Try to start watchdogs for each destination
        # Note: Watchdogs will only start if a stream is actually running to that destination
        for dest in destinations:
            await self.start_watchdog(dest)  # stream_id will be auto-detected
        
        logger.info("Watchdog Manager started successfully")
    
    async def start_watchdog(self, destination: StreamingDestination, stream_id: Optional[int] = None):
        """
        Start watchdog for a specific destination stream
        
        Args:
            destination: Destination to monitor
            stream_id: ID of the stream to monitor (auto-detected if None)
        """
        dest_id = destination.id
        
        # Auto-detect stream_id if not provided
        if stream_id is None:
            from services.ffmpeg_manager import get_ffmpeg_manager
            ffmpeg_manager = await get_ffmpeg_manager()
            destination_url = destination.get_full_rtmp_url()
            stream_id = ffmpeg_manager.find_stream_by_destination_url(destination_url)
            
            if stream_id is None:
                logger.warning(
                    f"No active stream found for destination {dest_id} ({destination.name}). "
                    f"Watchdog will not start until stream is active."
                )
                return
        
        # Check if already running
        if dest_id in self.watchdogs:
            logger.warning(f"Watchdog already running for destination {dest_id} ({destination.name})")
            return
        
        try:
            # Get YouTube channel live URL if available
            youtube_url = None
            if destination.youtube_watch_url:
                # Convert watch URL to channel/live URL if it's a watch URL
                # Otherwise use as-is (assuming it's already a /live URL)
                youtube_url = destination.youtube_watch_url
            
            # Create local watchdog instance
            watchdog = LocalStreamWatchdog(
                destination_id=dest_id,
                destination_name=destination.name,
                stream_id=stream_id,
                check_interval=destination.watchdog_check_interval or 30,
                youtube_channel_live_url=youtube_url
            )
            
            # Store instance
            self.watchdogs[dest_id] = watchdog
            
            # Start watchdog in background task
            task = asyncio.create_task(watchdog.start())
            self.watchdog_tasks[dest_id] = task
            
            logger.info(f"Started local watchdog for destination {dest_id} ({destination.name}) monitoring stream {stream_id}")
            
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
    
    async def restart_watchdog(self, destination: StreamingDestination, stream_id: Optional[int] = None):
        """
        Restart watchdog for a destination
        
        Args:
            destination: Destination to restart watchdog for
            stream_id: ID of the stream to monitor (auto-detected if None)
        """
        await self.stop_watchdog(destination.id)
        await asyncio.sleep(1)
        await self.start_watchdog(destination, stream_id)
    
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
        
        # Get all destinations with watchdog enabled
        enabled_destinations = db_session.query(StreamingDestination).filter(
            StreamingDestination.enable_watchdog == True,
            StreamingDestination.is_active == True
        ).all()
        
        enabled_ids = {dest.id for dest in enabled_destinations if hasattr(dest, 'active_stream_id') and dest.active_stream_id}
        running_ids = set(self.watchdogs.keys())
        
        # Stop watchdogs that should no longer run
        to_stop = running_ids - enabled_ids
        for dest_id in to_stop:
            logger.info(f"Stopping watchdog for destination {dest_id} (no longer enabled or no active stream)")
            await self.stop_watchdog(dest_id)
        
        # Start new watchdogs
        to_start = enabled_ids - running_ids
        for dest in enabled_destinations:
            if dest.id in to_start and hasattr(dest, 'active_stream_id') and dest.active_stream_id:
                logger.info(f"Starting new watchdog for destination {dest.id} ({dest.name})")
                await self.start_watchdog(dest, dest.active_stream_id)
        
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
            "check_interval": watchdog.check_interval
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
    
    async def notify_stream_started(self, destination_ids: List[int], stream_id: int, db_session: Session):
        """
        Notify watchdog manager that a stream has started streaming to destination(s).
        This will automatically start watchdogs for any enabled destinations.
        
        Args:
            destination_ids: List of destination IDs the stream is streaming to
            stream_id: ID of the stream that started
            db_session: Database session
        """
        logger.info(f"Stream {stream_id} started to {len(destination_ids)} destination(s)")
        
        for dest_id in destination_ids:
            # Get destination from database
            destination = db_session.query(StreamingDestination).filter(
                StreamingDestination.id == dest_id
            ).first()
            
            if not destination:
                logger.warning(f"Destination {dest_id} not found")
                continue
            
            # Start watchdog if enabled
            if destination.enable_watchdog:
                logger.info(f"Starting watchdog for destination {dest_id} ({destination.name})")
                await self.start_watchdog(destination, stream_id)
    
    async def notify_stream_stopped(self, stream_id: int):
        """
        Notify watchdog manager that a stream has stopped.
        This will stop all watchdogs monitoring that stream.
        
        Args:
            stream_id: ID of the stream that stopped
        """
        logger.info(f"Stream {stream_id} stopped, stopping associated watchdogs")
        
        # Find all watchdogs monitoring this stream
        to_stop = []
        for dest_id, watchdog in self.watchdogs.items():
            if watchdog.stream_id == stream_id:
                to_stop.append(dest_id)
        
        # Stop them
        for dest_id in to_stop:
            await self.stop_watchdog(dest_id)
    
    async def stop_all(self):
        """Stop all watchdogs"""
        logger.info("Stopping all watchdogs")
        self.running = False
        
        for dest_id in list(self.watchdogs.keys()):
            await self.stop_watchdog(dest_id)
        
        logger.info("All watchdogs stopped")
    


# Global watchdog manager instance
_watchdog_manager: Optional[WatchdogManager] = None


def get_watchdog_manager() -> WatchdogManager:
    """Get the global watchdog manager instance"""
    global _watchdog_manager
    if _watchdog_manager is None:
        _watchdog_manager = WatchdogManager()
    return _watchdog_manager

