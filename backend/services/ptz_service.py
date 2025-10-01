"""
PTZ Camera Control Service using ONVIF
"""

import asyncio
import logging
from typing import Optional, Tuple

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


class PTZService:
    """Service for controlling PTZ cameras via ONVIF"""
    
    def __init__(self):
        self._camera_connections = {}  # Cache ONVIF connections
        self._onvif_available = ONVIFCamera is not None
    
    async def get_onvif_camera(self, address: str, port: int, username: str, password: str):
        """Get or create ONVIF camera connection"""
        cache_key = f"{address}:{port}"
        
        if cache_key not in self._camera_connections:
            try:
                logger.info(f"Creating ONVIF connection to {address}:{port}")
                camera = ONVIFCamera(address, port, username, password)
                await asyncio.get_event_loop().run_in_executor(None, camera.update_xaddrs)
                self._camera_connections[cache_key] = camera
                logger.info(f"✅ ONVIF connection established to {address}:{port}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to ONVIF camera {address}:{port}: {e}")
                raise
        
        return self._camera_connections[cache_key]
    
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
            logger.info(f"🎯 Moving camera {address} to preset {preset_token}")
            
            # Get ONVIF camera connection
            camera = await self.get_onvif_camera(address, port, username, password)
            
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
            
            # Use first profile
            media_profile = profiles[0]
            
            # Create request
            request = ptz_service.create_type('GotoPreset')
            request.ProfileToken = media_profile.token
            request.PresetToken = preset_token
            
            # Execute move
            await asyncio.get_event_loop().run_in_executor(
                None,
                ptz_service.GotoPreset,
                request
            )
            
            logger.info(f"✅ Camera {address} moved to preset {preset_token}")
            return True
            
        except ONVIFError as e:
            logger.error(f"❌ ONVIF error moving to preset: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error moving to preset: {e}")
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
            logger.info(f"📍 Getting current position for camera {address}")
            
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
                
                logger.info(f"✅ Current position: pan={pan}, tilt={tilt}, zoom={zoom}")
                return (pan, tilt, zoom)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current position: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def set_preset(
        self,
        address: str,
        port: int,
        username: str,
        password: str,
        preset_token: str,
        preset_name: str
    ) -> bool:
        """
        Save current position as a preset
        
        Args:
            address: Camera IP address
            port: ONVIF port
            username: Camera username
            password: Camera password
            preset_token: Preset token (ID)
            preset_name: Human-readable preset name
        
        Returns:
            True if successful
        """
        if not self._onvif_available:
            logger.warning("⚠️  ONVIF not available, cannot set preset")
            return False
            
        try:
            logger.info(f"💾 Saving preset {preset_name} (token: {preset_token}) for camera {address}")
            
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
                return False
            
            media_profile = profiles[0]
            
            # Create request
            request = ptz_service.create_type('SetPreset')
            request.ProfileToken = media_profile.token
            request.PresetToken = preset_token
            request.PresetName = preset_name
            
            # Execute save
            await asyncio.get_event_loop().run_in_executor(
                None,
                ptz_service.SetPreset,
                request
            )
            
            logger.info(f"✅ Preset {preset_name} saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving preset: {e}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance
_ptz_service = None

def get_ptz_service() -> PTZService:
    """Get the singleton PTZ service instance"""
    global _ptz_service
    if _ptz_service is None:
        _ptz_service = PTZService()
    return _ptz_service

