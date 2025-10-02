"""
Camera service for managing cameras and testing connections
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
import httpx
from httpx import BasicAuth, DigestAuth
import asyncio
import base64
import subprocess
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from urllib.parse import quote as urlquote

from models.database import Camera, Preset
from models.schemas import (
    CameraCreate, CameraUpdate, Camera as CameraSchema, 
    CameraWithStatus, CameraTestResponse, PresetCreate, Preset
)

class CameraService:
    def __init__(self, db: Session):
        self.db = db

    async def get_all_cameras_with_status(self) -> List[CameraWithStatus]:
        """Get all cameras with their current status"""
        cameras = self.db.query(Camera).filter(Camera.is_active == True).all()
        cameras_with_status = []
        
        for camera in cameras:
            status = await self._check_camera_status(camera)
            camera_with_status = CameraWithStatus(
                id=camera.id,
                name=camera.name,
                type=camera.type,
                protocol=camera.protocol,
                address=camera.address,
                username=camera.username,
                port=camera.port,
                stream_path=camera.stream_path,
                snapshot_url=camera.snapshot_url,
                is_active=camera.is_active,
                created_at=camera.created_at,
                last_seen=camera.last_seen,
                status=status["status"],
                last_error=status.get("error")
            )
            cameras_with_status.append(camera_with_status)
        
        return cameras_with_status

    async def get_camera_with_status(self, camera_id: int) -> Optional[CameraWithStatus]:
        """Get a specific camera with status"""
        camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return None
        
        status = await self._check_camera_status(camera)
        return CameraWithStatus(
            id=camera.id,
            name=camera.name,
            type=camera.type,
            protocol=camera.protocol,
            address=camera.address,
            username=camera.username,
            port=camera.port,
            stream_path=camera.stream_path,
            snapshot_url=camera.snapshot_url,
            is_active=camera.is_active,
            created_at=camera.created_at,
            last_seen=camera.last_seen,
            status=status["status"],
            last_error=status.get("error")
        )

    async def create_camera(self, camera_data: CameraCreate) -> CameraSchema:
        """Create a new camera"""
        # Encrypt password if provided
        password_enc = None
        if camera_data.password:
            # Simple base64 encoding for now - should use proper encryption in production
            password_enc = base64.b64encode(camera_data.password.encode()).decode()
        
        camera = Camera(
            name=camera_data.name,
            type=camera_data.type,
            protocol=camera_data.protocol,
            address=camera_data.address,
            username=camera_data.username,
            password_enc=password_enc,
            port=camera_data.port,
            stream_path=camera_data.stream_path,
            snapshot_url=camera_data.snapshot_url
        )
        
        self.db.add(camera)
        self.db.commit()
        self.db.refresh(camera)
        
        return CameraSchema.from_orm(camera)

    async def update_camera(self, camera_id: int, camera_update: CameraUpdate) -> Optional[CameraSchema]:
        """Update a camera"""
        camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return None
        
        update_data = camera_update.dict(exclude_unset=True)
        
        # Handle password encryption
        if "password" in update_data and update_data["password"]:
            update_data["password_enc"] = base64.b64encode(update_data["password"].encode()).decode()
            del update_data["password"]
        
        for field, value in update_data.items():
            setattr(camera, field, value)
        
        self.db.commit()
        self.db.refresh(camera)
        
        return CameraSchema.from_orm(camera)

    async def delete_camera(self, camera_id: int) -> bool:
        """Delete a camera"""
        camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return False
        
        camera.is_active = False
        self.db.commit()
        return True

    async def test_camera_connection(self, camera_id: int) -> CameraTestResponse:
        """Test camera connection"""
        camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return CameraTestResponse(
                success=False,
                message="Camera not found",
                rtsp_accessible=False,
                snapshot_accessible=False
            )
        
        return await self._test_camera_connection_internal(camera)

    async def test_camera_connection_direct(self, camera_data: CameraCreate) -> CameraTestResponse:
        """Test camera connection without saving to database"""
        # Create a temporary camera object for testing
        camera = Camera(
            name=camera_data.name,
            type=camera_data.type,
            protocol=camera_data.protocol,
            address=camera_data.address,
            username=camera_data.username,
            password_enc=base64.b64encode(camera_data.password.encode()).decode() if camera_data.password else None,
            port=camera_data.port,
            stream_path=camera_data.stream_path,
            snapshot_url=camera_data.snapshot_url
        )
        
        return await self._test_camera_connection_internal(camera)

    async def _test_camera_connection_internal(self, camera: Camera) -> CameraTestResponse:
        """Internal method to test camera connection"""
        rtsp_accessible = False
        snapshot_accessible = False
        error_details = []
        
        # Test RTSP connection
        try:
            rtsp_url = self._build_rtsp_url(camera)
            rtsp_accessible = await self._test_rtsp_connection(rtsp_url)
            if not rtsp_accessible:
                error_details.append("RTSP stream not accessible")
        except Exception as e:
            error_details.append(f"RTSP test error: {str(e)}")
        
        # Test snapshot URL
        if camera.snapshot_url:
            try:
                snapshot_accessible = await self._test_snapshot_url(camera.snapshot_url, camera.username, camera.password_enc, camera.name)
                if not snapshot_accessible:
                    error_details.append("Snapshot URL not accessible")
            except Exception as e:
                error_details.append(f"Snapshot test error: {str(e)}")
        
        success = rtsp_accessible and (snapshot_accessible or not camera.snapshot_url)
        
        # Update last_seen timestamp if test successful and camera has an ID (saved in DB)
        if success and hasattr(camera, 'id') and camera.id:
            camera.last_seen = datetime.utcnow()
            self.db.commit()
            print(f"DEBUG: Updated last_seen for camera {camera.id} ({camera.name})")
        
        return CameraTestResponse(
            success=success,
            message="Camera test completed",
            rtsp_accessible=rtsp_accessible,
            snapshot_accessible=snapshot_accessible,
            error_details="; ".join(error_details) if error_details else None
        )

    async def _test_rtsp_connection(self, rtsp_url: str) -> bool:
        """Test RTSP connection using FFmpeg"""
        print(f"DEBUG: Testing RTSP URL with FFmpeg: {rtsp_url}")
        try:
            # Use FFmpeg to test the stream with a 10-second timeout (cameras need time to respond)
            cmd = [
                'ffmpeg',
                '-timeout', '10000000',  # 10 seconds in microseconds
                '-rtsp_transport', 'tcp',  # Use TCP for more reliable connection
                '-i', rtsp_url,
                '-t', '1',  # Try for 1 second of video
                '-f', 'null',
                '-'
            ]

            # Run FFmpeg with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
                result = process.returncode == 0
                print(f"DEBUG: FFmpeg test result - return code: {process.returncode}")
                if stderr:
                    stderr_str = stderr.decode()
                    print(f"DEBUG: FFmpeg stderr: {stderr_str[:500]}...")
                return result
            except asyncio.TimeoutError:
                print("DEBUG: FFmpeg test timed out after 15 seconds")
                process.kill()
                return False
                
        except Exception as e:
            print(f"DEBUG: FFmpeg test exception: {str(e)}")
            return False

    async def _test_snapshot_url(self, snapshot_url: str, username: str, password_enc: str, camera_name: str = "") -> bool:
        """Test snapshot URL accessibility"""
        try:
            # Decode password if encrypted
            password = self._decode_password(password_enc)

            # Try with Digest auth for Reolink cameras (they use HTTP Digest)
            if username and password and "reolink" in camera_name.lower():
                print(f"DEBUG: Testing Reolink snapshot with Digest auth")
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(snapshot_url, auth=DigestAuth(username, password))
                    return response.status_code == 200
                except Exception as e:
                    print(f"DEBUG: Digest auth test failed: {e}")
                    return False

            # Build URL with credentials if provided (for other cameras)
            if username and password:
                snapshot_url = self._inject_credentials(snapshot_url, username, password)

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(snapshot_url)
                return response.status_code == 200
        except Exception as e:
            print(f"DEBUG: Snapshot test exception: {e}")
            return False

    def _build_rtsp_url(self, camera: Camera) -> str:
        """Build RTSP URL from camera configuration"""
        # Decode password if encrypted
        password = self._decode_password(camera.password_enc)

        print(f"DEBUG: Building RTSP URL for {camera.name}")
        print(f"DEBUG: Username: {camera.username}, Password available: {password is not None}")
        print(f"DEBUG: Address: {camera.address}, Port: {camera.port}, Path: {camera.stream_path}")

        # Build URL
        if camera.username and password:
            safe_username = urlquote(camera.username, safe="")
            safe_password = urlquote(password, safe="")
            url = f"rtsp://{safe_username}:{safe_password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            url = f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"
        
        print(f"DEBUG: Final RTSP URL: {url}")
        return url

    async def _check_camera_status(self, camera: Camera) -> dict:
        """Check camera status (online/offline/error) - optimized for speed"""
        try:
            # Use cached status if camera was seen recently (within 5 minutes)
            if camera.last_seen and (datetime.utcnow() - camera.last_seen).total_seconds() < 300:
                return {"status": "online"}

            probe_success, probe_error = await self._quick_probe_camera(camera)

            if probe_success:
                camera.last_seen = datetime.utcnow()
                self.db.commit()
                return {"status": "online"}

            error_message = probe_error or "Quick status probe failed"
            return {"status": "offline", "error": error_message}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _quick_probe_camera(self, camera: Camera) -> Tuple[bool, Optional[str]]:
        """Perform a lightweight probe to determine if the camera is reachable."""
        if not camera.snapshot_url:
            return False, "No snapshot URL configured for quick probe"

        password = self._decode_password(camera.password_enc)
        if camera.password_enc and password is None:
            return False, "Failed to decode camera credentials"

        auth = None
        if camera.username and password:
            if "reolink" in camera.name.lower():
                auth = DigestAuth(camera.username, password)
            else:
                auth = BasicAuth(camera.username, password)

        try:
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
                try:
                    response = await client.head(camera.snapshot_url, auth=auth)
                except httpx.RequestError as exc:
                    return False, f"Snapshot probe failed: {exc}"

                if response.status_code < 400:
                    return True, None

                if response.status_code == 405:
                    # Some cameras reject HEAD; fall back to a small GET request
                    headers = {"Range": "bytes=0-0"}
                    try:
                        get_response = await client.get(camera.snapshot_url, headers=headers, auth=auth)
                    except httpx.RequestError as exc:
                        return False, f"Snapshot GET probe failed: {exc}"

                    if get_response.status_code < 400:
                        return True, None

                    return False, f"Snapshot GET probe returned status {get_response.status_code}"

                if response.status_code in (401, 403):
                    return False, "Snapshot probe unauthorized"

                return False, f"Snapshot probe returned status {response.status_code}"
        except Exception as exc:
            return False, str(exc)

    async def get_camera_snapshot(self, camera_id: int) -> Optional[dict]:
        """Get a snapshot from the camera"""
        camera = self.db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera or not camera.snapshot_url:
            return None
        
        try:
            # Decode password if encrypted
            password = self._decode_password(camera.password_enc)
            
            # Build URL with credentials if provided
            snapshot_url = camera.snapshot_url
            if camera.username and password:
                snapshot_url = self._inject_credentials(snapshot_url, camera.username, password)

            auth: Optional[DigestAuth] = None
            if camera.username and password and "reolink" in camera.name.lower():
                print(f"DEBUG: Using Digest auth for Reolink camera")
                auth = DigestAuth(camera.username, password)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(snapshot_url, auth=auth)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    print(f"DEBUG: Snapshot response content-type: {content_type}")
                    
                    # Check if response is actually an image
                    if content_type.startswith("image/"):
                        # Return base64 encoded image data
                        image_data = base64.b64encode(response.content).decode()
                        return {
                            "image_data": image_data,
                            "content_type": content_type,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        # Response is not an image, likely an error
                        error_content = response.content.decode('utf-8', errors='ignore')[:200]
                        print(f"DEBUG: Snapshot returned non-image content: {error_content}")
                        return None
        except Exception as e:
            print(f"Error getting snapshot: {e}")

        return None

    def _decode_password(self, password_enc: Optional[str]) -> Optional[str]:
        """Safely decode a stored password string."""
        if not password_enc:
            return None

        try:
            return base64.b64decode(password_enc, validate=True).decode()
        except Exception as exc:
            print(f"DEBUG: Failed to decode password: {exc}")
            return None

    def _inject_credentials(self, url: str, username: str, password: str) -> str:
        """Insert credentials into an HTTP/RTSP URL with proper escaping."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https", "rtsp"}:
            return url

        netloc = parsed.netloc.split("@")[-1]
        safe_username = urlquote(username, safe="")
        safe_password = urlquote(password, safe="")
        new_netloc = f"{safe_username}:{safe_password}@{netloc}"
        return urlunparse(parsed._replace(netloc=new_netloc))

    async def create_preset(self, preset_data: PresetCreate) -> Preset:
        """Create a PTZ preset"""
        preset = Preset(
            camera_id=preset_data.camera_id,
            name=preset_data.name,
            pan=preset_data.pan,
            tilt=preset_data.tilt,
            zoom=preset_data.zoom
        )
        
        self.db.add(preset)
        self.db.commit()
        self.db.refresh(preset)
        
        return preset

    async def get_camera_presets(self, camera_id: int) -> List[Preset]:
        """Get all presets for a camera"""
        presets = self.db.query(Preset).filter(Preset.camera_id == camera_id).all()
        return presets

    async def execute_preset(self, camera_id: int, preset_id: int) -> bool:
        """Execute a PTZ preset"""
        preset = self.db.query(Preset).filter(
            Preset.id == preset_id,
            Preset.camera_id == camera_id
        ).first()
        
        if not preset:
            return False
        
        # TODO: Implement actual PTZ control via ONVIF
        # For now, just return success
        return True
