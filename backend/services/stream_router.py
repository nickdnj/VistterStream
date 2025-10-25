"""
Stream Router Service
Routes timeline output to preview server OR live destinations based on mode.

This service manages the preview → live workflow:
1. IDLE: No streaming
2. PREVIEW: Timeline → Local MediaMTX → HLS → Browser
3. LIVE: Timeline → External platforms (YouTube, Facebook, etc.)

See: docs/PreviewSystem-Specification.md Section 4.1
"""

import asyncio
import logging
from enum import Enum
from typing import Optional, List
from datetime import datetime

from models.database import SessionLocal
from models.destination import StreamingDestination
from services.timeline_executor import get_timeline_executor
from services.ffmpeg_manager import EncodingProfile

logger = logging.getLogger(__name__)


class PreviewMode(str, Enum):
    """Preview/Live mode states"""
    IDLE = "idle"           # No timeline running
    PREVIEW = "preview"     # Timeline → Preview Server
    LIVE = "live"           # Timeline → Live Destinations


class StreamRouter:
    """
    Routes timeline output between preview server and live destinations.
    
    Features:
    - State machine (IDLE → PREVIEW → LIVE)
    - Preview server routing (RTMP to localhost:1935)
    - Live destination routing (RTMP to YouTube, Facebook, etc.)
    - Go-live transition (preview → live)
    """
    
    def __init__(self):
        self.mode = PreviewMode.IDLE
        self.timeline_id: Optional[int] = None
        self.destination_ids: List[int] = []
        self._lock = asyncio.Lock()
    
    async def start_preview(self, timeline_id: int) -> bool:
        """
        Start timeline in preview mode (output to local MediaMTX).
        
        Args:
            timeline_id: Timeline to execute
            
        Returns:
            bool: Success status
            
        Raises:
            ValueError: If already running or timeline not found
        """
        async with self._lock:
            if self.mode != PreviewMode.IDLE:
                raise ValueError(f"Cannot start preview: currently in {self.mode} mode")
            
            logger.info(f"🎬 Starting preview for timeline {timeline_id}")
            
            # Build preview destination (MediaMTX in Docker on port 1936)
            # MediaMTX path is configured as "preview" in mediamtx.yml
            preview_url = "rtmp://localhost:1936/preview"
            output_urls = [preview_url]
            
            # Start timeline with preview destination
            executor = get_timeline_executor()
            success = await executor.start_timeline(
                timeline_id=timeline_id,
                output_urls=output_urls,
                encoding_profile=None  # Use default reliability profile
            )
            
            if not success:
                raise ValueError("Failed to start timeline (already running?)")
            
            # Update state
            self.mode = PreviewMode.PREVIEW
            self.timeline_id = timeline_id
            
            logger.info(f"✅ Preview started: timeline {timeline_id} → {preview_url}")
            return True
    
    async def stop(self) -> bool:
        """
        Stop current preview or live stream.
        
        Returns:
            bool: Success status
        """
        async with self._lock:
            if self.mode == PreviewMode.IDLE:
                logger.warning("Cannot stop: already idle")
                return False
            
            logger.info(f"🛑 Stopping {self.mode} mode for timeline {self.timeline_id}")
            
            # Get stream ID before stopping (for watchdog notification)
            stream_id = None
            if self.timeline_id is not None:
                try:
                    executor = get_timeline_executor()
                    timeline_state = executor.get_timeline_state(self.timeline_id)
                    if timeline_state and 'stream_id' in timeline_state:
                        stream_id = timeline_state['stream_id']
                except Exception as e:
                    logger.warning(f"Failed to get stream ID: {e}")
                
                # Stop timeline executor
                await executor.stop_timeline(self.timeline_id)
            
            # Notify watchdog manager that stream stopped
            if stream_id:
                try:
                    from services.watchdog_manager import get_watchdog_manager
                    watchdog_manager = get_watchdog_manager()
                    await watchdog_manager.notify_stream_stopped(stream_id)
                except Exception as e:
                    logger.warning(f"Failed to notify watchdog manager: {e}")
            
            # Reset state
            old_mode = self.mode
            self.mode = PreviewMode.IDLE
            self.timeline_id = None
            self.destination_ids = []
            
            logger.info(f"✅ Stopped {old_mode} mode")
            return True
    
    async def go_live(self, destination_ids: List[int]) -> bool:
        """
        Transition from preview to live streaming.
        
        This restarts the timeline with live destinations.
        Future: Seamless transition without restart.
        
        Args:
            destination_ids: List of destination IDs to stream to
            
        Returns:
            bool: Success status
            
        Raises:
            ValueError: If not in preview mode or invalid destinations
        """
        async with self._lock:
            if self.mode != PreviewMode.PREVIEW:
                raise ValueError(
                    f"Can only go live from preview mode (current: {self.mode})"
                )
            
            if not destination_ids:
                raise ValueError("No destinations specified")
            
            logger.info(f"🔴 Going LIVE: timeline {self.timeline_id} → {len(destination_ids)} destinations")
            
            # Get destination URLs from database
            db = SessionLocal()
            try:
                destinations = db.query(StreamingDestination).filter(
                    StreamingDestination.id.in_(destination_ids)
                ).all()
                
                if not destinations:
                    raise ValueError("No valid destinations found")
                
                output_urls = [dest.get_full_rtmp_url() for dest in destinations]
                destination_names = [dest.name for dest in destinations]
                
                # Update last_used timestamp
                for dest in destinations:
                    dest.last_used = datetime.utcnow()
                db.commit()
                
                logger.info(f"📡 Live destinations: {', '.join(destination_names)}")
                
            finally:
                db.close()
            
            # Stop preview stream
            timeline_id = self.timeline_id
            executor = get_timeline_executor()
            await executor.stop_timeline(timeline_id)
            
            # Wait a moment for cleanup
            await asyncio.sleep(1)
            
            # Restart with live destinations
            success = await executor.start_timeline(
                timeline_id=timeline_id,
                output_urls=output_urls,
                encoding_profile=None
            )
            
            if not success:
                raise ValueError("Failed to start live stream")
            
            # Update state
            self.mode = PreviewMode.LIVE
            self.timeline_id = timeline_id
            self.destination_ids = destination_ids
            
            # Notify watchdog manager about the new stream
            try:
                from services.watchdog_manager import get_watchdog_manager
                from services.timeline_executor import get_timeline_executor
                
                watchdog_manager = get_watchdog_manager()
                executor = get_timeline_executor()
                
                # Get the stream ID that was just started
                timeline_state = executor.get_timeline_state(timeline_id)
                if timeline_state and 'stream_id' in timeline_state:
                    stream_id = timeline_state['stream_id']
                    
                    # Re-open db session for watchdog notification
                    db_for_watchdog = SessionLocal()
                    try:
                        await watchdog_manager.notify_stream_started(
                            destination_ids=destination_ids,
                            stream_id=stream_id,
                            db_session=db_for_watchdog
                        )
                    finally:
                        db_for_watchdog.close()
            except Exception as e:
                logger.warning(f"Failed to notify watchdog manager: {e}")
            
            logger.info(f"✅ NOW LIVE: {', '.join(destination_names)}")
            logger.warning("⚠️  Timeline restarted from beginning (seamless transition coming in future version)")
            
            return True
    
    def get_status(self) -> dict:
        """Get current router status"""
        return {
            "mode": self.mode.value,
            "timeline_id": self.timeline_id,
            "destination_ids": self.destination_ids,
            "is_active": self.mode != PreviewMode.IDLE
        }


# Global singleton instance
_stream_router: Optional[StreamRouter] = None


def get_stream_router() -> StreamRouter:
    """Get the global stream router instance"""
    global _stream_router
    if _stream_router is None:
        _stream_router = StreamRouter()
    return _stream_router
