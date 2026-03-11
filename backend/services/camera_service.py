"""
Camera service for managing cameras and testing connections
"""

import logging
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
import httpx
from httpx import BasicAuth, DigestAuth
import asyncio
import base64
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse, quote, urlunparse, unquote

from models.database import Camera, Preset
from utils.crypto import encrypt, decrypt
from utils.log_utils import redact_url
from models.schemas import (
    CameraCreate, CameraUpdate, Camera as CameraSchema,
    CameraWithStatus, CameraTestResponse, PresetCreate, Preset
)

logger = logging.getLogger(__name__)

class CameraService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def normalize_snapshot_url(snapshot_url: Optional[str]) -> Optional[str]:
        """Strip embedded credentials from snapshot URL if present"""
        if not snapshot_url:
            return snapshot_url
        parsed = urlparse(snapshot_url)
        if '@' in parsed.netloc:
            # Extract host:port from netloc (strip credentials)
            clean_netloc = parsed.netloc.split('@')[-1]
            # Rebuild URL without credentials
            normalized = urlunparse((
                parsed.scheme,
                clean_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            logger.warning("Stripped embedded credentials from snapshot URL: %s -> %s",
                           redact_url(snapshot_url), redact_url(normalized))
            return normalized
        return snapshot_url

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
            password_enc = encrypt(camera_data.password)

        # Normalize snapshot URL (strip embedded credentials if present)
        normalized_snapshot_url = self.normalize_snapshot_url(camera_data.snapshot_url)

        camera = Camera(
            name=camera_data.name,
            type=camera_data.type,
            protocol=camera_data.protocol,
            address=camera_data.address,
            username=camera_data.username,
            password_enc=password_enc,
            port=camera_data.port,
            stream_path=camera_data.stream_path,
            snapshot_url=normalized_snapshot_url
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
            update_data["password_enc"] = encrypt(update_data["password"])
            del update_data["password"]

        # Normalize snapshot URL if being updated (strip embedded credentials if present)
        if "snapshot_url" in update_data:
            update_data["snapshot_url"] = self.normalize_snapshot_url(update_data["snapshot_url"])

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
            password_enc=encrypt(camera_data.password) if camera_data.password else None,
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
            camera.last_seen = datetime.now(timezone.utc)
            self.db.commit()
            logger.debug("Updated last_seen for camera %d (%s)", camera.id, camera.name)

        return CameraTestResponse(
            success=success,
            message="Camera test completed",
            rtsp_accessible=rtsp_accessible,
            snapshot_accessible=snapshot_accessible,
            error_details="; ".join(error_details) if error_details else None
        )

    async def _test_rtsp_connection(self, rtsp_url: str) -> bool:
        """Test RTSP connection using FFmpeg"""
        logger.debug("Testing RTSP URL with FFmpeg: %s", redact_url(rtsp_url))
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
                logger.debug("FFmpeg test result - return code: %d", process.returncode)
                if stderr:
                    stderr_str = stderr.decode()
                    logger.debug("FFmpeg stderr: %s", stderr_str[:500])
                return result
            except asyncio.TimeoutError:
                logger.warning("FFmpeg test timed out after 15 seconds")
                process.kill()
                return False

        except Exception as e:
            logger.error("FFmpeg test exception: %s", str(e))
            return False

    async def _test_snapshot_url(self, snapshot_url: str, username: str, password_enc: str, camera_name: str = "") -> bool:
        """Test snapshot URL accessibility"""
        try:
            # Decode password if encrypted
            password = None
            if password_enc:
                password = decrypt(password_enc)

            # Parse URL and strip embedded credentials if present (always use provided username/password)
            parsed_url = urlparse(snapshot_url)
            has_credentials_in_url = '@' in parsed_url.netloc

            # Build clean URL without embedded credentials (always strip them)
            if has_credentials_in_url:
                clean_netloc = parsed_url.netloc.split('@')[-1]
                clean_url = urlunparse((
                    parsed_url.scheme,
                    clean_netloc,
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    parsed_url.fragment
                ))
                logger.debug("Stripped embedded credentials from snapshot URL for testing")
            else:
                clean_url = snapshot_url

            # Always use provided username/password (never use embedded credentials from URL)
            # Try multiple auth methods for ALL cameras (Digest first, then Basic, then embedded creds)
            if username and password:
                logger.debug("Testing snapshot with provided credentials")

                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Try 1: Digest auth (preferred for IP cameras like Reolink)
                    try:
                        response = await client.get(clean_url, auth=DigestAuth(username, password))
                        if response.status_code == 200:
                            logger.debug("Snapshot accessible with Digest auth")
                            return True
                    except Exception as e:
                        logger.debug("Digest auth test failed: %s", e)

                    # Try 2: Basic auth
                    try:
                        response = await client.get(clean_url, auth=BasicAuth(username, password))
                        if response.status_code == 200:
                            logger.debug("Snapshot accessible with Basic auth")
                            return True
                    except Exception as e:
                        logger.debug("Basic auth test failed: %s", e)

                    # Try 3: URL with embedded credentials
                    try:
                        parsed_url = urlparse(clean_url)
                        if parsed_url.scheme in ['http', 'https']:
                            encoded_username = quote(username, safe='')
                            encoded_password = quote(password, safe='')
                            cred_url = f"{parsed_url.scheme}://{encoded_username}:{encoded_password}@{parsed_url.netloc}{parsed_url.path}{'?' + parsed_url.query if parsed_url.query else ''}"
                            response = await client.get(cred_url)
                            if response.status_code == 200:
                                logger.debug("Snapshot accessible with embedded credentials")
                                return True
                    except Exception as e:
                        logger.debug("Embedded credentials test failed: %s", e)

                return False

            # No credentials - try without auth
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(clean_url)
                    return response.status_code == 200
            except Exception as e:
                logger.debug("No-auth test failed: %s", e)
                return False
        except Exception as e:
            logger.error("Snapshot test exception: %s", e)
            return False

    def _build_rtsp_url(self, camera: Camera) -> str:
        """Build RTSP URL from camera configuration"""
        # Decode password if encrypted
        password = None
        if camera.password_enc:
            password = decrypt(camera.password_enc)

        logger.debug("Building RTSP URL for %s", camera.name)
        logger.debug("Username: %s, Password available: %s", camera.username, password is not None)
        logger.debug("Address: %s, Port: %s, Path: %s", camera.address, camera.port, camera.stream_path)

        # Build URL (URL-encode credentials to handle special characters like !, @, #)
        if camera.username and password:
            encoded_username = quote(camera.username, safe='')
            encoded_password = quote(password, safe='')
            url = f"rtsp://{encoded_username}:{encoded_password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            url = f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"

        logger.debug("Final RTSP URL: %s", redact_url(url))
        return url

    async def _check_camera_status(self, camera: Camera) -> dict:
        """Check camera status (online/offline/error) - optimized for speed"""
        try:
            # Use cached status if camera was seen recently (within 5 minutes)
            if camera.last_seen and (datetime.now(timezone.utc) - camera.last_seen).total_seconds() < 300:
                return {"status": "online"}

            probe_success, probe_error = await self._quick_probe_camera(camera)

            if probe_success:
                camera.last_seen = datetime.now(timezone.utc)
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

        password = None
        if camera.password_enc:
            try:
                password = decrypt(camera.password_enc)
            except Exception as exc:
                return False, f"Failed to decode camera credentials: {exc}"

        # Parse URL and strip embedded credentials if present (always use camera username/password fields)
        parsed_url = urlparse(camera.snapshot_url)
        has_credentials_in_url = '@' in parsed_url.netloc

        # Build clean URL without embedded credentials (always strip them)
        if has_credentials_in_url:
            clean_netloc = parsed_url.netloc.split('@')[-1]
            probe_url = urlunparse((
                parsed_url.scheme,
                clean_netloc,
                parsed_url.path,
                parsed_url.params,
                parsed_url.query,
                parsed_url.fragment
            ))
            logger.debug("Stripped embedded credentials from snapshot URL for probe")
        else:
            probe_url = camera.snapshot_url

        # Always use camera username/password fields (never use embedded credentials from URL)
        # Try multiple auth methods: Digest first (used by Reolink and many IP cameras), then Basic
        if camera.username and password:
            # Try 1: Digest auth (preferred for IP cameras like Reolink)
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.head(probe_url, auth=DigestAuth(camera.username, password))
                    if response.status_code < 400:
                        logger.debug("Snapshot probe succeeded with Digest auth")
                        return True, None
                    if response.status_code == 405:
                        # Try GET instead of HEAD
                        response = await client.get(probe_url, auth=DigestAuth(camera.username, password))
                        if response.status_code < 400:
                            logger.debug("Snapshot probe succeeded with Digest auth (GET)")
                            return True, None
            except Exception as e:
                logger.debug("Digest auth probe failed: %s", e)

            # Try 2: Basic auth
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.head(probe_url, auth=BasicAuth(camera.username, password))
                    if response.status_code < 400:
                        logger.debug("Snapshot probe succeeded with Basic auth")
                        return True, None
                    if response.status_code == 405:
                        response = await client.get(probe_url, auth=BasicAuth(camera.username, password))
                        if response.status_code < 400:
                            logger.debug("Snapshot probe succeeded with Basic auth (GET)")
                            return True, None
            except Exception as e:
                logger.debug("Basic auth probe failed: %s", e)

            return False, "Snapshot probe unauthorized (tried Digest and Basic auth)"

        # No credentials - try without auth
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.head(probe_url)
                if response.status_code < 400:
                    return True, None
                if response.status_code == 405:
                    response = await client.get(probe_url)
                    if response.status_code < 400:
                        return True, None
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
            password = None
            if camera.password_enc:
                password = decrypt(camera.password_enc)

            # Parse URL and strip embedded credentials if present (always use camera username/password fields)
            parsed_url = urlparse(camera.snapshot_url)
            has_credentials_in_url = '@' in parsed_url.netloc

            # Build clean URL without embedded credentials (always strip them)
            if has_credentials_in_url:
                clean_netloc = parsed_url.netloc.split('@')[-1]
                clean_url = urlunparse((
                    parsed_url.scheme,
                    clean_netloc,
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    parsed_url.fragment
                ))
                logger.debug("Stripped embedded credentials from snapshot URL")
            else:
                clean_url = camera.snapshot_url

            # Always use camera username/password fields (never use embedded credentials from URL)
            # Try multiple auth methods: Digest first (used by Reolink and many IP cameras), then Basic
            if camera.username and password:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Try 1: Digest auth (preferred for IP cameras like Reolink)
                    logger.debug("Trying Digest auth for snapshot")
                    try:
                        response = await client.get(clean_url, auth=DigestAuth(camera.username, password))

                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "")
                            logger.debug("Snapshot with Digest auth - content-type: %s", content_type)

                            if content_type.startswith("image/"):
                                image_data = base64.b64encode(response.content).decode()
                                return {
                                    "image_data": image_data,
                                    "content_type": content_type,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                    except Exception as e:
                        logger.debug("Digest auth failed: %s", e)

                    # Try 2: Basic auth
                    logger.debug("Trying Basic auth for snapshot")
                    try:
                        response = await client.get(clean_url, auth=BasicAuth(camera.username, password))

                        if response.status_code == 200:
                            content_type = response.headers.get("content-type", "")
                            logger.debug("Snapshot with Basic auth - content-type: %s", content_type)

                            if content_type.startswith("image/"):
                                image_data = base64.b64encode(response.content).decode()
                                return {
                                    "image_data": image_data,
                                    "content_type": content_type,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                    except Exception as e:
                        logger.debug("Basic auth failed: %s", e)

                    # Try 3: URL with embedded credentials
                    logger.debug("Trying URL with embedded credentials for snapshot")
                    try:
                        parsed_url = urlparse(clean_url)
                        if parsed_url.scheme in ['http', 'https']:
                            encoded_username = quote(camera.username, safe='')
                            encoded_password = quote(password, safe='')
                            cred_url = f"{parsed_url.scheme}://{encoded_username}:{encoded_password}@{parsed_url.netloc}{parsed_url.path}{'?' + parsed_url.query if parsed_url.query else ''}"
                            response = await client.get(cred_url)

                            if response.status_code == 200:
                                content_type = response.headers.get("content-type", "")
                                logger.debug("Snapshot with embedded creds - content-type: %s", content_type)

                                if content_type.startswith("image/"):
                                    image_data = base64.b64encode(response.content).decode()
                                    return {
                                        "image_data": image_data,
                                        "content_type": content_type,
                                        "timestamp": datetime.now(timezone.utc).isoformat()
                                    }
                    except Exception as e:
                        logger.debug("Embedded credentials failed: %s", e)

                logger.debug("All HTTP auth methods failed for snapshot, trying FFmpeg RTSP fallback")
                return await self._ffmpeg_snapshot(camera)

            # No credentials - try without auth
            logger.debug("No credentials, trying snapshot without auth")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(clean_url)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if content_type.startswith("image/"):
                        image_data = base64.b64encode(response.content).decode()
                        return {
                            "image_data": image_data,
                            "content_type": content_type,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
            return None
        except Exception as e:
            logger.error("Error getting snapshot: %s", e)

        return None

    async def _ffmpeg_snapshot(self, camera) -> Optional[dict]:
        """Grab a single frame from the camera's RTSP stream using FFmpeg"""
        import subprocess, tempfile, os
        rtsp_url = self._build_rtsp_url(camera)
        tmp_path = f"/tmp/snapshot_{camera.id}.jpg"
        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-rtsp_transport", "tcp",
                 "-i", rtsp_url, "-frames:v", "1", "-f", "image2", tmp_path],
                capture_output=True, timeout=15
            )
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                with open(tmp_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()
                os.remove(tmp_path)
                logger.info("FFmpeg RTSP snapshot succeeded for %s", camera.name)
                return {
                    "image_data": image_data,
                    "content_type": "image/jpeg",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error("FFmpeg snapshot failed: %s", e)
        return None

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
