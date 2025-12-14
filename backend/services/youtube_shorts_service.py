"""
YouTube Shorts Publishing Service

Handles OAuth authentication and video uploads to YouTube Shorts.
"""

import os
import logging
import base64
import json
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# YouTube API scopes for uploading videos
YOUTUBE_SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]


class YouTubeShortsService:
    """Service for uploading videos to YouTube Shorts"""
    
    def __init__(self):
        self._credentials: Optional[Credentials] = None
        self._youtube = None
    
    def _encrypt(self, value: str) -> str:
        """Simple base64 encoding (use proper encryption in production)"""
        return base64.b64encode(value.encode()).decode()
    
    def _decrypt(self, encrypted: str) -> str:
        """Decode base64"""
        return base64.b64decode(encrypted.encode()).decode()
    
    def get_oauth_url(self, client_id: str, client_secret: str, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL for YouTube
        
        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            redirect_uri: Callback URL after authorization
            
        Returns:
            Authorization URL to redirect user to
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url
    
    def exchange_code_for_tokens(
        self, 
        code: str, 
        client_id: str, 
        client_secret: str, 
        redirect_uri: str
    ) -> Dict:
        """
        Exchange authorization code for access/refresh tokens
        
        Args:
            code: Authorization code from OAuth callback
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            redirect_uri: Same redirect URI used in authorization
            
        Returns:
            Dict with refresh_token and channel info
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get channel info
        youtube = build('youtube', 'v3', credentials=credentials)
        channel_response = youtube.channels().list(
            part='snippet',
            mine=True
        ).execute()
        
        channel_name = "Unknown"
        if channel_response.get('items'):
            channel_name = channel_response['items'][0]['snippet']['title']
        
        return {
            "refresh_token": credentials.refresh_token,
            "channel_name": channel_name
        }
    
    def _get_credentials(
        self, 
        client_id: str, 
        client_secret: str, 
        refresh_token: str
    ) -> Credentials:
        """Create credentials object from stored tokens"""
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=YOUTUBE_SCOPES
        )
    
    async def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> Dict:
        """
        Upload a video to YouTube Shorts
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            refresh_token: Stored refresh token
            
        Returns:
            Dict with video_id and url
        """
        try:
            # Validate video exists
            if not Path(video_path).exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Get credentials
            credentials = self._get_credentials(client_id, client_secret, refresh_token)
            
            # Build YouTube API client
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Prepare video metadata
            # Adding #Shorts to title/description helps YouTube categorize as Short
            if '#Shorts' not in title and '#shorts' not in title:
                title = f"{title} #Shorts"
            
            body = {
                'snippet': {
                    'title': title[:100],  # YouTube title limit
                    'description': description[:5000],  # YouTube description limit
                    'tags': tags[:500] if tags else [],  # YouTube tags limit
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': 'public',  # or 'private', 'unlisted'
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Create media upload
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            # Execute upload
            logger.info(f"📺 Uploading video to YouTube Shorts: {title}")
            
            request = youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"📺 Upload progress: {int(status.progress() * 100)}%")
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/shorts/{video_id}"
            
            logger.info(f"📺 Upload complete! Video ID: {video_id}")
            logger.info(f"📺 Video URL: {video_url}")
            
            return {
                "video_id": video_id,
                "url": video_url,
                "success": True
            }
            
        except HttpError as e:
            error_msg = str(e)
            logger.error(f"📺 YouTube API error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            logger.error(f"📺 Upload failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
_youtube_service: Optional[YouTubeShortsService] = None


def get_youtube_service() -> YouTubeShortsService:
    """Get the global YouTube service instance"""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeShortsService()
    return _youtube_service
