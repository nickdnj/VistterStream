"""
RTMP Relay Service - Camera to Local RTMP Relay
This is the SECRET SAUCE for instant camera switching!

Each camera continuously streams to local RTMP server.
The main FFmpeg switcher pulls from local RTMP (instant switching!)
"""

import asyncio
import logging
import base64
from typing import Dict, Optional
from sqlalchemy.orm import Session

from models.database import Camera, SessionLocal

logger = logging.getLogger(__name__)


class CameraRelay:
    """Manages one camera's relay to local RTMP"""
    def __init__(self, camera_id: int, camera_name: str, rtsp_url: str):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.rtmp_url = f"rtmp://127.0.0.1:1935/live/camera_{camera_id}"
        self.process: Optional[asyncio.subprocess.Process] = None
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start relay from RTSP to local RTMP"""
        if self.process:
            logger.warning(f"Relay for {self.camera_name} already running")
            return
        
        # FFmpeg command: RTSP → Local RTMP
        # Key: -shortest and -reconnect for reliability
        cmd = [
            'ffmpeg',
            '-loglevel', 'warning',
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            '-c:v', 'copy',  # Copy video (no re-encoding = LOW latency!)
            '-c:a', 'aac',   # Re-encode audio to AAC
            '-b:a', '128k',
            '-ar', '44100',
            '-f', 'flv',
            self.rtmp_url
        ]
        
        logger.info(f"🎥 Starting relay: {self.camera_name} → {self.rtmp_url}")
        
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Start monitoring
            self.monitor_task = asyncio.create_task(self._monitor())
            
            logger.info(f"✅ Relay started for {self.camera_name} (PID: {self.process.pid})")
            
        except Exception as e:
            logger.error(f"❌ Failed to start relay for {self.camera_name}: {e}")
            raise
    
    async def stop(self):
        """Stop the relay"""
        if not self.process:
            return
        
        logger.info(f"🛑 Stopping relay for {self.camera_name}")
        
        try:
            self.process.terminate()
            await asyncio.sleep(1)
            if self.process.returncode is None:
                self.process.kill()
        except:
            pass
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.process = None
        self.monitor_task = None
        logger.info(f"✅ Relay stopped for {self.camera_name}")
    
    async def _monitor(self):
        """Monitor relay process and auto-restart on failure"""
        last_10_lines = []
        
        while True:
            try:
                line = await self.process.stderr.readline()
                if not line:
                    # Process ended
                    returncode = await self.process.wait()
                    logger.error(f"❌ Relay {self.camera_name} DIED (exit code: {returncode})")
                    
                    # Log the last 10 lines before death
                    if last_10_lines:
                        logger.error(f"Last FFmpeg output before death:")
                        for log_line in last_10_lines:
                            logger.error(f"  {log_line}")
                    
                    # Auto-restart after 5 seconds
                    await asyncio.sleep(5)
                    logger.info(f"🔄 Auto-restarting relay for {self.camera_name}")
                    self.process = None
                    last_10_lines = []
                    await self.start()
                    return
                
                # Decode and log all output (temporarily for debugging)
                line_str = line.decode().strip()
                last_10_lines.append(line_str)
                if len(last_10_lines) > 10:
                    last_10_lines.pop(0)
                
                # Log everything for now (debugging mode)
                logger.info(f"FFmpeg [{self.camera_name}]: {line_str}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error for {self.camera_name}: {e}")
                break


class RTMPRelayService:
    """
    Manages all camera relays to local RTMP server.
    This enables INSTANT camera switching with ZERO black screens!
    """
    
    def __init__(self):
        self.relays: Dict[int, CameraRelay] = {}
        self._shutdown_event = asyncio.Event()
    
    async def start_camera_relay(self, camera_id: int, db: Session) -> bool:
        """Start relay for a specific camera"""
        if camera_id in self.relays:
            logger.info(f"Relay for camera {camera_id} already running")
            return True
        
        # Get camera from database
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            logger.error(f"Camera {camera_id} not found")
            return False
        
        # Build RTSP URL
        rtsp_url = self._build_rtsp_url(camera)
        
        # Create and start relay
        relay = CameraRelay(camera_id, camera.name, rtsp_url)
        await relay.start()
        
        self.relays[camera_id] = relay
        return True
    
    async def stop_camera_relay(self, camera_id: int):
        """Stop relay for a specific camera"""
        if camera_id not in self.relays:
            return
        
        relay = self.relays[camera_id]
        await relay.stop()
        del self.relays[camera_id]
    
    async def start_all_cameras(self):
        """Start relays for ALL cameras in database"""
        db = SessionLocal()
        try:
            cameras = db.query(Camera).filter(Camera.is_active == True).all()
            logger.info(f"🚀 Starting relays for {len(cameras)} cameras...")
            
            tasks = []
            for camera in cameras:
                tasks.append(self.start_camera_relay(camera.id, db))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r is True)
            logger.info(f"✅ Started {success_count}/{len(cameras)} camera relays")
            
        finally:
            db.close()
    
    async def stop_all_relays(self):
        """Stop all camera relays"""
        logger.info(f"🛑 Stopping all {len(self.relays)} camera relays...")
        
        tasks = []
        for camera_id in list(self.relays.keys()):
            tasks.append(self.stop_camera_relay(camera_id))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"✅ All relays stopped")
    
    def get_relay_url(self, camera_id: int) -> Optional[str]:
        """Get the local RTMP URL for a camera"""
        if camera_id in self.relays:
            return self.relays[camera_id].rtmp_url
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
_rtmp_relay_service: Optional[RTMPRelayService] = None


def get_rtmp_relay_service() -> RTMPRelayService:
    """Get the global RTMP relay service"""
    global _rtmp_relay_service
    if _rtmp_relay_service is None:
        _rtmp_relay_service = RTMPRelayService()
    return _rtmp_relay_service


