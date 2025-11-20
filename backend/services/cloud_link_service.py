"""
Cloud Link Service
Manages the persistent WebSocket connection to VistterStudio (Cloud Companion App).
Handles authentication, pairing, and command dispatching.
"""

import asyncio
import logging
import json
import aiohttp
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from sqlalchemy.orm import Session

from models.database import SessionLocal, Settings

logger = logging.getLogger(__name__)

class CloudLinkService:
    _instance = None
    
    def __init__(self):
        self.is_running = False
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._stop_event = asyncio.Event()
        self._connection_task: Optional[asyncio.Task] = None
        self.connection_status = "disconnected"  # disconnected, connecting, connected, error
        self.last_error = None
        self.pairing_code: Optional[str] = None
        self.pairing_code_expires: Optional[datetime] = None
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CloudLinkService()
        return cls._instance
        
    async def start(self):
        """Start the cloud link service"""
        if self.is_running:
            return
            
        logger.info("☁️ Starting Cloud Link Service...")
        self.is_running = True
        self._stop_event.clear()
        self._connection_task = asyncio.create_task(self._connect_loop())
        
    async def stop(self):
        """Stop the cloud link service"""
        if not self.is_running:
            return
            
        logger.info("☁️ Stopping Cloud Link Service...")
        self.is_running = False
        self._stop_event.set()
        
        if self.ws:
            await self.ws.close()
            
        if self.session:
            await self.session.close()
            
        if self._connection_task:
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
                
    async def _connect_loop(self):
        """Main connection loop with exponential backoff"""
        backoff = 1
        max_backoff = 60
        
        while not self._stop_event.is_set():
            try:
                # Get settings for URL and token
                db = SessionLocal()
                try:
                    settings = db.query(Settings).first()
                    if not settings:
                        logger.warning("No settings found, waiting...")
                        await asyncio.sleep(5)
                        continue
                        
                    url = settings.cloud_api_url or "wss://api.vistterstudio.com/ws/device"
                    token = settings.cloud_pairing_token
                    device_id = settings.cloud_device_id
                finally:
                    db.close()
                
                # If no token, we are in "pairing mode" or just idle
                # For now, we connect even without token to allow pairing flow if supported by server
                # OR we only connect if we have a token or are requesting pairing?
                # Let's assume we always try to connect to the "device gateway"
                
                headers = {}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                if device_id:
                    headers["X-Device-ID"] = device_id
                    
                self.connection_status = "connecting"
                logger.info(f"☁️ Connecting to {url}...")
                
                async with aiohttp.ClientSession() as session:
                    self.session = session
                    try:
                        async with session.ws_connect(url, headers=headers, heartbeat=30) as ws:
                            self.ws = ws
                            self.connection_status = "connected"
                            self.last_error = None
                            backoff = 1  # Reset backoff
                            logger.info("✅ Connected to VistterStudio Cloud")
                            
                            # Send initial handshake/status
                            await self._send_status()
                            
                            # Start heartbeat loop
                            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                            
                            # Message loop
                            async for msg in ws:
                                if self._stop_event.is_set():
                                    break
                                    
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    await self._handle_message(msg.data)
                                elif msg.type == aiohttp.WSMsgType.ERROR:
                                    logger.error(f"WebSocket connection closed with error {ws.exception()}")
                                    break
                                    
                            # Cancel heartbeat on disconnect
                            heartbeat_task.cancel()
                            try:
                                await heartbeat_task
                            except asyncio.CancelledError:
                                pass
                    except Exception as e:
                        self.last_error = str(e)
                        logger.error(f"☁️ Connection error: {e}")
                        self.connection_status = "error"
                        
            except Exception as e:
                logger.error(f"☁️ Unexpected error in connect loop: {e}")
                self.last_error = str(e)
                
            if self._stop_event.is_set():
                break
                
            # Backoff
            logger.info(f"☁️ Reconnecting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            
    async def _handle_message(self, data: str):
        """Handle incoming WebSocket messages"""
        try:
            message = json.loads(data)
            msg_type = message.get("type")
            payload = message.get("payload", {})
            
            logger.debug(f"📩 Received message: {msg_type}")
            
            if msg_type == "pairing.code":
                # Received a pairing code response
                self.pairing_code = payload.get("code")
                expires_at = payload.get("expires_at") # ISO string
                if expires_at:
                    self.pairing_code_expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                logger.info(f"🔑 Received pairing code: {self.pairing_code}")
                
            elif msg_type == "pairing.success":
                # Pairing successful, save token
                token = payload.get("token")
                device_id = payload.get("device_id")
                if token and device_id:
                    self._save_credentials(token, device_id)
                    logger.info("✅ Pairing successful! Credentials saved.")
                    # Reconnect to apply new credentials
                    if self.ws:
                        await self.ws.close()
                        
            elif msg_type == "command":
                # Handle remote commands (start/stop stream, etc)
                await self._handle_command(payload)
                
        except json.JSONDecodeError:
            logger.error("Failed to decode WebSocket message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    async def _handle_command(self, payload: Dict[str, Any]):
        """Dispatch remote commands"""
        command = payload.get("command")
        params = payload.get("params", {})
        
        logger.info(f"🔔 Received command: {command}")
        
        try:
            if command == "stream.start":
                await self._handle_start_stream(params)
            elif command == "stream.stop":
                await self._handle_stop_stream(params)
            elif command == "ptz.move":
                await self._handle_ptz_move(params)
            elif command == "timeline.sync":
                # TODO: Implement in Phase 4
                logger.info("Timeline sync command received (not implemented yet)")
            else:
                logger.warning(f"Unknown command: {command}")
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            # Optionally send error back to cloud
            
    async def _handle_start_stream(self, params: Dict[str, Any]):
        """Handle stream start command"""
        timeline_id = params.get("timeline_id")
        output_urls = params.get("output_urls", [])
        
        if not timeline_id:
            logger.error("Missing timeline_id for stream.start")
            return
            
        logger.info(f"🚀 Starting stream for timeline {timeline_id}")
        
        from services.timeline_executor import get_timeline_executor
        executor = get_timeline_executor()
        
        # Start the timeline
        success = await executor.start_timeline(
            timeline_id=int(timeline_id),
            output_urls=output_urls
        )
        
        if success:
            logger.info(f"✅ Stream {timeline_id} started via remote command")
        else:
            logger.warning(f"❌ Failed to start stream {timeline_id} via remote command")

    async def _handle_stop_stream(self, params: Dict[str, Any]):
        """Handle stream stop command"""
        timeline_id = params.get("timeline_id")
        
        if not timeline_id:
            logger.error("Missing timeline_id for stream.stop")
            return
            
        logger.info(f"🛑 Stopping stream for timeline {timeline_id}")
        
        from services.timeline_executor import get_timeline_executor
        executor = get_timeline_executor()
        
        success = await executor.stop_timeline(int(timeline_id))
        
        if success:
            logger.info(f"✅ Stream {timeline_id} stopped via remote command")
        else:
            logger.warning(f"❌ Failed to stop stream {timeline_id} via remote command")
            
    async def _handle_ptz_move(self, params: Dict[str, Any]):
        """Handle PTZ move command"""
        camera_id = params.get("camera_id")
        pan = params.get("pan")
        tilt = params.get("tilt")
        zoom = params.get("zoom")
        
        if not camera_id:
            logger.error("Missing camera_id for ptz.move")
            return
            
        logger.info(f"🎥 Moving camera {camera_id} to P:{pan} T:{tilt} Z:{zoom}")
        
        from services.ptz_service import get_ptz_service
        from models.database import SessionLocal, Camera
        import base64
        
        db = SessionLocal()
        try:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                logger.error(f"Camera {camera_id} not found")
                return
                
            password = None
            if camera.password_enc:
                try:
                    password = base64.b64decode(camera.password_enc).decode()
                except Exception:
                    pass
            
            if not password:
                logger.warning(f"No password for camera {camera_id}")
                return

            ptz = get_ptz_service()
            await ptz.move_absolute(
                address=camera.address,
                port=camera.onvif_port,
                username=camera.username,
                password=password,
                pan=pan,
                tilt=tilt,
                zoom=zoom
            )
        except Exception as e:
            logger.error(f"Failed to execute PTZ move: {e}")
        finally:
            db.close()

    async def _heartbeat_loop(self):
        """Send heartbeat every 30 seconds"""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(30)
                await self._send_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)

    async def _send_status(self):
        """Send current device status (Heartbeat)"""
        if not self.ws:
            return
            
        try:
            import psutil
            
            # Gather system metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Gather app metrics
            uptime = 0 # TODO: Track app uptime
            
            status = {
                "type": "status.heartbeat",
                "payload": {
                    "system": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "disk_percent": disk.percent,
                        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
                    },
                    "app": {
                        "version": "1.0.0",
                        "uptime": uptime
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            await self.ws.send_json(status)
        except Exception as e:
            logger.error(f"Failed to send status: {e}")

    async def notify_stream_event(self, event_type: str, stream_id: int, details: Dict[str, Any] = None):
        """Notify cloud about stream events (started, stopped, error)"""
        if not self.ws:
            return
            
        payload = {
            "stream_id": stream_id,
            "timestamp": datetime.utcnow().isoformat(),
            **(details or {})
        }
        
        msg = {
            "type": f"stream.{event_type}",
            "payload": payload
        }
        
        try:
            await self.ws.send_json(msg)
            logger.info(f"☁️ Sent stream event: {event_type} for stream {stream_id}")
        except Exception as e:
            logger.error(f"Failed to send stream event: {e}")

    def _save_credentials(self, token: str, device_id: str):
        """Save pairing credentials to database"""
        db = SessionLocal()
        try:
            settings = db.query(Settings).first()
            if settings:
                settings.cloud_pairing_token = token
                settings.cloud_device_id = device_id
                db.commit()
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
        finally:
            db.close()
            
    async def request_pairing(self):
        """Request a new pairing code"""
        if not self.ws or self.connection_status != "connected":
            # If not connected, we might need to force a connection attempt or wait
            # For now, assume we are connected (even if anonymously)
            logger.warning("Cannot request pairing: Not connected to cloud")
            return False
            
        msg = {
            "type": "pairing.request",
            "payload": {}
        }
        try:
            await self.ws.send_json(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to request pairing: {e}")
            return False
            
    def get_status(self):
        """Get current service status"""
        return {
            "is_running": self.is_running,
            "connection_status": self.connection_status,
            "last_error": self.last_error,
            "pairing_code": self.pairing_code,
            "pairing_code_expires": self.pairing_code_expires,
            "is_paired": self._is_paired()
        }
        
    def _is_paired(self) -> bool:
        """Check if device has pairing credentials"""
        db = SessionLocal()
        try:
            settings = db.query(Settings).first()
            return bool(settings and settings.cloud_pairing_token)
        finally:
            db.close()

# Global accessor
def get_cloud_link_service():
    return CloudLinkService.get_instance()
