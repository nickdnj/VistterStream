"""
PTZ Camera Control Service using ONVIF
"""

import asyncio
import logging
import os
import platform
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse

# Lazy import ONVIF to avoid startup issues
ONVIFCamera = None
ONVIFError = None

try:
    from onvif import ONVIFCamera as _ONVIFCamera
    from onvif.exceptions import ONVIFError as _ONVIFError
    ONVIFCamera = _ONVIFCamera
    ONVIFError = _ONVIFError
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️  ONVIF library not available. PTZ features will be disabled.")
    logger.warning("   Install with: pip install onvif-zeep")

logger = logging.getLogger(__name__)


def _env_flag(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 2:
        return "*" * len(value)
    return f"{value[0]}***{value[-1]}"


def _sanitize_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        parsed = parsed._replace(netloc=netloc)
    return urlunparse(parsed)


class PTZService:
    """Service for controlling PTZ cameras via ONVIF"""
    
    def __init__(self):
        self._camera_connections = {}  # Cache ONVIF connections
        self._onvif_available = ONVIFCamera is not None
        self._ptz_debug = _env_flag(os.getenv("PTZ_DEBUG"))
        self._device_override = self._parse_override_url(os.getenv("ONVIF_DEVICE_URL"))
        self._ptz_override = self._normalize_url(os.getenv("ONVIF_PTZ_URL"))
        if self._ptz_debug:
            logger.info("🔍 PTZ_DEBUG enabled")
    
    def _debug(self, message: str, **context):
        if not self._ptz_debug:
            return
        context_items = " ".join(f"{key}={value}" for key, value in context.items() if value is not None)
        logger.info(f"[PTZ_DEBUG] {message}{(' ' + context_items) if context_items else ''}")

    @staticmethod
    def _normalize_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            logger.warning("⚠️  Ignoring invalid ONVIF override URL: %s", url)
            return None
        return _sanitize_url(url)

    def _parse_override_url(self, url: Optional[str]):
        normalized = self._normalize_url(url)
        if not normalized:
            return None

        parsed = urlparse(normalized)
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        path = parsed.path or "/onvif/device_service"

        if path != "/onvif/device_service":
            self._debug(
                "Device override uses non-standard path; client will still request /onvif/device_service",
                provided_path=path,
            )

        return {
            "hostname": parsed.hostname,
            "port": port,
            "url": normalized,
        }

    def _resolve_address(self, address: str, port: int) -> Tuple[str, int]:
        resolved_address = address
        resolved_port = port

        if self._device_override:
            resolved_address = self._device_override["hostname"]
            resolved_port = self._device_override["port"]
            self._debug(
                "Applying explicit ONVIF_DEVICE_URL override",
                requested=f"{address}:{port}",
                resolved=f"{resolved_address}:{resolved_port}",
            )

        forbidden = {"localhost", "127.0.0.1", "host.docker.internal"}
        if platform.system().lower() == "linux" and resolved_address in forbidden:
            raise ValueError(
                f"Camera address {resolved_address} is not reachable from Linux containers. "
                "Configure ONVIF_DEVICE_URL with the camera IP address."
            )

        return resolved_address, resolved_port

    def _register_connection_aliases(self, camera, keys):
        for key in keys:
            self._camera_connections[key] = camera

    def _apply_ptz_override(self, camera):
        if not self._ptz_override:
            return
        try:
            from onvif import client as onvif_client  # local import to avoid optional dep issues
        except ImportError:
            logger.debug("ONVIF client unavailable; cannot apply PTZ override")
            return

        ns = onvif_client.SERVICES["ptz"]["ns"]
        camera.xaddrs[ns] = self._ptz_override
        self._debug(
            "Applied explicit PTZ service override",
            ptz_url=_sanitize_url(self._ptz_override),
        )

    async def get_onvif_camera(self, address: str, port: int, username: str, password: str):
        """Get or create ONVIF camera connection"""
        resolved_address, resolved_port = self._resolve_address(address, port)
        cache_keys = {
            f"{address}:{port}",
            f"{resolved_address}:{resolved_port}",
        }

        for key in cache_keys:
            if key in self._camera_connections:
                self._debug(
                    "Reusing cached ONVIF connection",
                    cache_key=key,
                    user=username,
                )
                return self._camera_connections[key]

        ports_to_try = [resolved_port]
        if not self._device_override:
            for alt in (8899, 8000, 80):
                if alt not in ports_to_try:
                    ports_to_try.append(alt)

        loop = asyncio.get_event_loop()
        last_error = None

        for candidate in ports_to_try:
            try:
                self._debug(
                    "Attempting ONVIF connection",
                    address=resolved_address,
                    candidate_port=candidate,
                    username=username,
                )
                camera = ONVIFCamera(resolved_address, candidate, username, password)
                await loop.run_in_executor(None, camera.update_xaddrs)
                self._apply_ptz_override(camera)
                self._register_connection_aliases(
                    camera,
                    {
                        f"{resolved_address}:{candidate}",
                        f"{address}:{port}",
                        f"{address}:{candidate}",
                    },
                )
                if candidate != port:
                    logger.info(
                        "✅ ONVIF connection established to %s:%s (fallback from %s)",
                        resolved_address,
                        candidate,
                        port,
                    )
                else:
                    logger.info("✅ ONVIF connection established to %s:%s", resolved_address, candidate)
                self._debug(
                    "ONVIF services discovered",
                    xaddrs={key: _sanitize_url(value) for key, value in camera.xaddrs.items()},
                )
                break
            except Exception as e:
                logger.error(
                    "❌ Failed to connect to ONVIF camera %s:%s: %s",
                    resolved_address,
                    candidate,
                    e,
                )
                last_error = e
        else:
            raise last_error or RuntimeError("Unable to establish ONVIF connection")

        # Return connection stored under the resolved key
        resolved_key = f"{resolved_address}:{resolved_port}"
        return self._camera_connections[resolved_key]
    
    async def move_to_preset(
        self,
        address: str,
        port: int,
        username: str,
        password: str,
        preset_token: str
    ) -> bool:
        """
        Move camera to a preset position
        
        Args:
            address: Camera IP address
            port: ONVIF port (usually 80 or 8000)
            username: Camera username
            password: Camera password
            preset_token: Preset token (usually the preset ID as string)
        
        Returns:
            True if successful, False otherwise
        """
        if not self._onvif_available:
            logger.warning("⚠️  ONVIF not available, cannot move to preset")
            return False
            
        try:
            logger.info("🎯 Moving camera %s to preset %s", address, preset_token)
            
            # Get ONVIF camera connection
            camera = await self.get_onvif_camera(address, port, username, password)
            self._debug(
                "Camera connection ready for preset move",
                user=username,
                cache_keys=[key for key, value in self._camera_connections.items() if value is camera],
            )
            
            # Get PTZ service
            ptz_service = camera.create_ptz_service()
            
            # Get media profile
            media_service = camera.create_media_service()
            profiles = await asyncio.get_event_loop().run_in_executor(
                None,
                media_service.GetProfiles
            )
            
            if not profiles:
                logger.error("No media profiles found")
                return False
            
            profile_tokens = [getattr(profile, "token", "unknown") for profile in profiles]
            self._debug(
                "Loaded media profiles",
                profile_tokens=profile_tokens,
            )
            
            # Use first profile
            media_profile = profiles[0]
            
            # Create request
            request = ptz_service.create_type('GotoPreset')
            request.ProfileToken = media_profile.token
            request.PresetToken = preset_token
            
            self._debug(
                "Dispatching GotoPreset",
                profile_token=media_profile.token,
                preset_token=preset_token,
            )
            
            # Execute move
            await asyncio.get_event_loop().run_in_executor(
                None,
                ptz_service.GotoPreset,
                request
            )
            
            logger.info("✅ Camera %s moved to preset %s", address, preset_token)
            return True
            
        except ONVIFError as e:
            logger.error("❌ ONVIF error moving to preset: %s", e)
            self._debug("ONVIFError context", error_type=type(e).__name__)
            return False
        except Exception as e:
            logger.error("❌ Error moving to preset: %s", e)
            import traceback
            traceback.print_exc()
            return False
    
    async def get_current_position(
        self,
        address: str,
        port: int,
        username: str,
        password: str
    ) -> Optional[Tuple[float, float, float]]:
        """
        Get current PTZ position (pan, tilt, zoom)
        
        Returns:
            Tuple of (pan, tilt, zoom) or None if failed
        """
        if not self._onvif_available:
            logger.warning("⚠️  ONVIF not available, cannot get current position")
            return None
            
        try:
            logger.info("📍 Getting current position for camera %s", address)
            
            camera = await self.get_onvif_camera(address, port, username, password)
            ptz_service = camera.create_ptz_service()
            
            # Get media profile
            media_service = camera.create_media_service()
            profiles = await asyncio.get_event_loop().run_in_executor(
                None,
                media_service.GetProfiles
            )
            
            if not profiles:
                logger.error("No media profiles found")
                return None
            
            media_profile = profiles[0]
            self._debug("Using media profile for status", profile_token=media_profile.token)
            
            # Get status
            request = ptz_service.create_type('GetStatus')
            request.ProfileToken = media_profile.token
            
            status = await asyncio.get_event_loop().run_in_executor(
                None,
                ptz_service.GetStatus,
                request
            )
            
            if status and status.Position:
                pan = status.Position.PanTilt.x if status.Position.PanTilt else 0.0
                tilt = status.Position.PanTilt.y if status.Position.PanTilt else 0.0
                zoom = status.Position.Zoom.x if status.Position.Zoom else 1.0
                
                logger.info("✅ Current position: pan=%s, tilt=%s, zoom=%s", pan, tilt, zoom)
                return (pan, tilt, zoom)
            
            self._debug("PTZ status unavailable", status=bool(status))
            return None
            
        except Exception as e:
            logger.error("❌ Error getting current position: %s", e)
            import traceback
            traceback.print_exc()
            return None
    
    async def set_preset(
        self,
        address: str,
        port: int,
        username: str,
        password: str,
        preset_name: str,
        preset_token: Optional[str] = None
    ) -> str:
        """
        Save current position as a preset

        Args:
            address: Camera IP address
            port: ONVIF port
            username: Camera username
            password: Camera password
            preset_name: Human-readable preset name
            preset_token: Optional preset token to reuse

        Returns:
            Preset token assigned by the camera
        """
        if not self._onvif_available:
            logger.warning("⚠️  ONVIF not available, cannot set preset")
            raise RuntimeError('ONVIF support is not available')

        try:
            logger.info(
                "💾 Saving preset %s (token: %s) for camera %s",
                preset_name,
                preset_token or "new",
                address,
            )

            camera = await self.get_onvif_camera(address, port, username, password)
            ptz = camera.create_ptz_service()

            # Get media profile
            media_service = camera.create_media_service()
            loop = asyncio.get_event_loop()
            profiles = await loop.run_in_executor(None, media_service.GetProfiles)

            if not profiles:
                raise RuntimeError('Camera did not return any media profiles')

            media_profile = profiles[0]

            # Create request
            request = ptz.create_type('SetPreset')
            request.ProfileToken = media_profile.token
            if preset_token:
                request.PresetToken = preset_token
            request.PresetName = preset_name

            # Execute save and capture response
            response = await loop.run_in_executor(None, ptz.SetPreset, request)
            self._debug(
                "SetPreset dispatched",
                profile_token=media_profile.token,
                preset_token=preset_token,
            )

            token = getattr(response, 'PresetToken', None) if response else None
            if not token:
                token = preset_token

            if not token:
                raise RuntimeError('Camera did not provide a preset token')

            logger.info(f"✅ Preset {preset_name} saved successfully (token: {token})")
            return token

        except Exception as e:
            logger.error(f"❌ Error saving preset: {e}")
            import traceback
            traceback.print_exc()
            raise


# Singleton instance
_ptz_service = None

def get_ptz_service() -> PTZService:
    """Get the singleton PTZ service instance"""
    global _ptz_service
    if _ptz_service is None:
        _ptz_service = PTZService()
    return _ptz_service
