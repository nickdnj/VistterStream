"""
Preview Server Health Monitoring
Checks if MediaMTX is running and accepting connections.

See: docs/PreviewSystem-Specification.md Section 4.2
"""

import httpx
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class PreviewServerHealth:
    """
    Monitors MediaMTX preview server health.
    
    Features:
    - Health check via MediaMTX API
    - Active stream detection
    - Timeout and retry handling
    """
    
    def __init__(self, api_url: str = "http://localhost:9997"):
        self.api_url = api_url
    
    async def check_health(self) -> bool:
        """
        Check if MediaMTX is running and accepting connections.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/v1/config/get")
                # 200 OK or 401 Unauthorized both mean the server is running
                is_healthy = response.status_code in [200, 401]
                
                if is_healthy:
                    logger.debug("✅ Preview server is healthy")
                else:
                    logger.warning(f"⚠️  Preview server returned status {response.status_code}")
                
                return is_healthy
                
        except httpx.ConnectError:
            logger.error("❌ Preview server is not running (connection refused)")
            return False
        except httpx.TimeoutException:
            logger.error("❌ Preview server health check timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Preview server health check failed: {e}")
            return False
    
    async def get_active_streams(self) -> Dict:
        """
        Get list of active streams from MediaMTX.
        
        Returns:
            dict: Streams data from MediaMTX API, or empty dict on failure
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/v1/paths/list")
                if response.status_code == 200:
                    data = response.json()
                    
                    # Log active paths
                    paths = data.get("items", {})
                    if paths:
                        active = [name for name, info in paths.items() if info.get("ready")]
                        logger.debug(f"📡 Active preview streams: {active}")
                    
                    return data
                else:
                    logger.warning(f"Failed to get active streams: HTTP {response.status_code}")
                    return {"items": {}}
                    
        except Exception as e:
            logger.error(f"Failed to get active streams: {e}")
            return {"items": {}}
    
    async def is_preview_active(self) -> bool:
        """
        Check if preview stream is currently active.
        
        Returns:
            bool: True if preview path is active and ready
        """
        streams = await self.get_active_streams()
        items = streams.get("items", {})
        
        # Check if 'preview' path exists and is ready
        preview = items.get("preview", {})
        return preview.get("ready", False)
