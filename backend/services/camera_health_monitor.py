"""
Camera Health Monitor - Background service to keep cameras online
Automatically tests cameras every 3 minutes to update their last_seen status
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from models.database import SessionLocal, Camera
from services.camera_service import CameraService

logger = logging.getLogger(__name__)


class CameraHealthMonitor:
    """Background service that monitors camera health"""
    
    def __init__(self, check_interval: int = 180):  # 3 minutes
        self.check_interval = check_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the health monitoring background task"""
        if self.running:
            logger.warning("Camera health monitor already running")
            return
            
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"🔄 Camera health monitor started (checking every {self.check_interval}s)")
        
    async def stop(self):
        """Stop the health monitoring background task"""
        if not self.running:
            return
            
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Camera health monitor stopped")
        
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._check_all_cameras()
            except Exception as e:
                logger.error(f"Error in camera health monitor: {e}")
            
            # Wait for next check interval
            await asyncio.sleep(self.check_interval)
    
    async def _check_all_cameras(self):
        """Check health of all active cameras"""
        db = SessionLocal()
        try:
            # Get all active cameras
            cameras = db.query(Camera).filter(Camera.is_active == True).all()
            
            if not cameras:
                return
            
            logger.info(f"📷 Health check: Testing {len(cameras)} cameras...")
            
            camera_service = CameraService(db)
            
            for camera in cameras:
                try:
                    # Test the camera
                    result = await camera_service.test_camera_connection(camera.id)
                    
                    if result.success:
                        # Camera is healthy - last_seen was updated in test_camera_connection
                        logger.debug(f"✅ Camera {camera.id} ({camera.name}): Healthy")
                    else:
                        logger.warning(f"⚠️ Camera {camera.id} ({camera.name}): Failed health check - {result.error_details}")
                        
                except Exception as e:
                    logger.error(f"❌ Camera {camera.id} ({camera.name}): Health check error - {e}")
                    
            logger.info(f"✅ Health check complete")
            
        except Exception as e:
            logger.error(f"Error checking cameras: {e}")
        finally:
            db.close()


# Global instance
_health_monitor: Optional[CameraHealthMonitor] = None


def get_health_monitor() -> CameraHealthMonitor:
    """Get the global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = CameraHealthMonitor(check_interval=180)  # 3 minutes
    return _health_monitor


async def start_health_monitor():
    """Start the global health monitor"""
    monitor = get_health_monitor()
    await monitor.start()


async def stop_health_monitor():
    """Stop the global health monitor"""
    global _health_monitor
    if _health_monitor:
        await _health_monitor.stop()

