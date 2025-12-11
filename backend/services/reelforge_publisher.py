"""
ReelForge Publisher Service - Stub for future VistterStream Cloud integration

Note: This is a simplified stub. Automatic publishing is not implemented in the
local VistterStream appliance. Users download videos and manually post to platforms.

Future: VistterStream Cloud will provide automatic publishing via OAuth integration.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ReelForgePublisher:
    """
    Stub publisher service for ReelForge.
    
    In the MVP, posts are downloaded manually and uploaded by users.
    This service is a placeholder for future VistterStream Cloud integration.
    """
    
    def __init__(self):
        pass
    
    def get_status(self) -> dict:
        """Get publisher status"""
        return {
            "mode": "manual",
            "message": "Automatic publishing is available in VistterStream Cloud. Download videos and post manually."
        }


# Global instance
_publisher: Optional[ReelForgePublisher] = None


def get_reelforge_publisher() -> ReelForgePublisher:
    """Get the global ReelForge publisher"""
    global _publisher
    if _publisher is None:
        _publisher = ReelForgePublisher()
    return _publisher
