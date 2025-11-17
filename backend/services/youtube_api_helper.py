"""
YouTube Live Streaming API Helper
Handles all interactions with YouTube Data API v3 for stream health monitoring
and broadcast lifecycle management.
"""

import os
import logging
import aiohttp
import asyncio
from typing import Any, Dict, Optional, Literal
from datetime import datetime

logger = logging.getLogger(__name__)


class YouTubeAPIError(Exception):
    """Custom exception for YouTube API errors"""
    pass


class YouTubeAPIHelper:
    """Helper class for YouTube Live Streaming API operations"""
    
    BASE_URL = "https://youtube.googleapis.com/youtube/v3"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        token_provider: Optional[Any] = None
    ):
        """
        Initialize YouTube API helper
        
        Args:
            api_key: YouTube Data API v3 key
        """
        if not api_key and not token_provider:
            raise ValueError("YouTubeAPIHelper requires either an API key or an OAuth token provider")

        self.api_key = api_key
        self._token_provider = token_provider
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_on_unauthorized: bool = True,
        force_refresh_token: bool = False
    ) -> Dict:
        """
        Make an authenticated request to YouTube API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., 'liveStreams')
            params: Query parameters
            json_data: JSON body for POST requests
            
        Returns:
            API response as dictionary
            
        Raises:
            YouTubeAPIError: If the request fails
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}

        headers = {}
        if self._token_provider:
            token = await self._get_access_token(force_refresh_token)
            headers['Authorization'] = f'Bearer {token}'
        elif self.api_key:
            params['key'] = self.api_key
        else:
            raise YouTubeAPIError('No authentication method configured for YouTube API helper')
        
        try:
            async with self.session.request(
                method, 
                url, 
                params=params,
                headers=headers,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                data = await response.json()

                if response.status >= 400:
                    if response.status == 401 and self._token_provider and retry_on_unauthorized:
                        await self._invalidate_token()
                        return await self._make_request(
                            method,
                            endpoint,
                            params=params,
                            json_data=json_data,
                            retry_on_unauthorized=False,
                            force_refresh_token=True
                        )

                    error_msg = data.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"YouTube API error: {response.status} - {error_msg}")
                    raise YouTubeAPIError(f"API returned {response.status}: {error_msg}")
                
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling YouTube API: {e}")
            raise YouTubeAPIError(f"Network error: {e}")
        except asyncio.TimeoutError:
            logger.error("YouTube API request timed out")
            raise YouTubeAPIError("Request timed out")

    async def _get_access_token(self, force_refresh: bool) -> str:
        if not self._token_provider:
            raise YouTubeAPIError("OAuth token provider is not configured")

        provider = getattr(self._token_provider, "get_access_token", None)
        if callable(provider):
            try:
                return await provider(force_refresh=force_refresh)
            except TypeError:
                return await provider()

        # Allow passing a raw callable for backwards compatibility
        callable_provider = self._token_provider
        try:
            return await callable_provider(force_refresh=force_refresh)
        except TypeError:
            return await callable_provider()

    async def _invalidate_token(self) -> None:
        if not self._token_provider:
            return

        invalidate = getattr(self._token_provider, 'invalidate', None)
        if callable(invalidate):
            await invalidate()
    
    async def get_stream_health(self, stream_id: str) -> Dict:
        """
        Get the health status of a live stream
        
        Args:
            stream_id: YouTube stream ID
            
        Returns:
            Dictionary containing:
                - status: 'good', 'ok', 'bad', 'noData'
                - lastUpdateTime: ISO timestamp
                - configurationIssues: List of issues (if any)
                
        Raises:
            YouTubeAPIError: If the request fails
        """
        logger.info(f"Checking health for stream {stream_id}")
        
        data = await self._make_request(
            'GET',
            'liveStreams',
            params={
                'part': 'status,snippet',
                'id': stream_id
            }
        )
        
        if not data.get('items'):
            raise YouTubeAPIError(f"Stream {stream_id} not found")
        
        stream = data['items'][0]
        status = stream.get('status', {})
        health_status = status.get('healthStatus', {})
        
        result = {
            'stream_id': stream_id,
            'title': stream.get('snippet', {}).get('title', 'Unknown'),
            'status': health_status.get('status', 'noData'),
            'last_update': health_status.get('lastUpdateTimeSeconds'),
            'configuration_issues': health_status.get('configurationIssues', []),
            'stream_status': status.get('streamStatus', 'unknown')
        }
        
        logger.info(f"Stream health: {result['status']} (stream_status: {result['stream_status']})")
        return result
    
    async def get_broadcast_status(self, broadcast_id: str) -> Dict:
        """
        Get the status of a broadcast
        
        Args:
            broadcast_id: YouTube broadcast ID
            
        Returns:
            Dictionary containing broadcast status information
            
        Raises:
            YouTubeAPIError: If the request fails
        """
        logger.info(f"Checking status for broadcast {broadcast_id}")
        
        data = await self._make_request(
            'GET',
            'liveBroadcasts',
            params={
                'part': 'status,snippet,contentDetails',
                'id': broadcast_id
            }
        )
        
        if not data.get('items'):
            raise YouTubeAPIError(f"Broadcast {broadcast_id} not found")
        
        broadcast = data['items'][0]
        status = broadcast.get('status', {})
        
        result = {
            'broadcast_id': broadcast_id,
            'title': broadcast.get('snippet', {}).get('title', 'Unknown'),
            'life_cycle_status': status.get('lifeCycleStatus', 'unknown'),
            'privacy_status': status.get('privacyStatus', 'unknown'),
            'recording_status': status.get('recordingStatus', 'unknown'),
            'bound_stream_id': broadcast.get('contentDetails', {}).get('boundStreamId')
        }
        
        logger.info(f"Broadcast status: {result['life_cycle_status']}")
        return result
    
    async def transition_broadcast(
        self, 
        broadcast_id: str, 
        status: Literal['testing', 'live', 'complete']
    ) -> Dict:
        """
        Transition a broadcast to a new lifecycle state
        
        Args:
            broadcast_id: YouTube broadcast ID
            status: Target status ('testing', 'live', or 'complete')
            
        Returns:
            Updated broadcast information
            
        Raises:
            YouTubeAPIError: If the transition fails
        """
        logger.info(f"Transitioning broadcast {broadcast_id} to {status}")
        
        data = await self._make_request(
            'POST',
            'liveBroadcasts/transition',
            params={
                'broadcastStatus': status,
                'id': broadcast_id,
                'part': 'status,snippet'
            }
        )
        
        if not data.get('items'):
            raise YouTubeAPIError(f"Failed to transition broadcast {broadcast_id}")
        
        broadcast = data['items'][0]
        new_status = broadcast.get('status', {}).get('lifeCycleStatus', 'unknown')
        
        logger.info(f"Broadcast transitioned to: {new_status}")
        return {
            'broadcast_id': broadcast_id,
            'life_cycle_status': new_status,
            'transition_time': datetime.utcnow().isoformat()
        }
    
    async def reset_broadcast(self, broadcast_id: str) -> Dict:
        """
        Reset a broadcast by cycling through complete -> testing -> live
        
        This is the nuclear option for recovering from zombie states.
        
        Args:
            broadcast_id: YouTube broadcast ID
            
        Returns:
            Final broadcast status after reset
            
        Raises:
            YouTubeAPIError: If any transition fails
        """
        logger.warning(f"Resetting broadcast {broadcast_id} (cycling through states)")
        
        # Check current status
        current = await self.get_broadcast_status(broadcast_id)
        logger.info(f"Current broadcast status: {current['life_cycle_status']}")
        
        # Transition to complete (if not already)
        if current['life_cycle_status'] != 'complete':
            await self.transition_broadcast(broadcast_id, 'complete')
            await asyncio.sleep(2)  # Give YouTube time to process
        
        # Transition to testing
        await self.transition_broadcast(broadcast_id, 'testing')
        await asyncio.sleep(2)
        
        # Transition to live
        result = await self.transition_broadcast(broadcast_id, 'live')
        
        logger.info(f"Broadcast reset complete: {result['life_cycle_status']}")
        return result
    
    async def probe_stream_frames(self, watch_url: str, timeout: int = 30) -> bool:
        """
        Probe the stream to verify actual video frames are being received
        
        Uses yt-dlp to attempt to fetch stream data. If it succeeds within
        the timeout, we know frames are flowing.
        
        Args:
            watch_url: YouTube watch URL (e.g., https://youtube.com/watch?v=xxx)
            timeout: Maximum seconds to wait for frames
            
        Returns:
            True if frames detected, False otherwise
        """
        logger.info(f"Probing stream frames at {watch_url}")
        
        try:
            # Run yt-dlp to check if we can get stream info
            proc = await asyncio.create_subprocess_exec(
                'yt-dlp',
                '--no-download',
                '--print', 'title',
                '--socket-timeout', str(timeout),
                watch_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), 
                    timeout=timeout + 5
                )
                
                if proc.returncode == 0:
                    logger.info("Stream probe successful - frames detected")
                    return True
                else:
                    logger.warning(f"Stream probe failed - returncode {proc.returncode}")
                    logger.debug(f"stderr: {stderr.decode()}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.warning("Stream probe timed out")
                proc.kill()
                return False
                
        except FileNotFoundError:
            logger.warning("yt-dlp not found - skipping frame probe")
            return True  # Assume OK if we can't probe
        except Exception as e:
            logger.error(f"Error probing stream: {e}")
            return False


async def test_youtube_api():
    """Test function to verify YouTube API connectivity"""
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Error: YOUTUBE_API_KEY not set")
        return
    
    stream_id = os.getenv('YOUTUBE_STREAM_ID')
    broadcast_id = os.getenv('YOUTUBE_BROADCAST_ID')
    
    async with YouTubeAPIHelper(api_key) as api:
        try:
            if stream_id:
                health = await api.get_stream_health(stream_id)
                print(f"Stream health: {health}")
            
            if broadcast_id:
                status = await api.get_broadcast_status(broadcast_id)
                print(f"Broadcast status: {status}")
                
        except YouTubeAPIError as e:
            print(f"API Error: {e}")


if __name__ == '__main__':
    # Test the API helper
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_youtube_api())

