"""
Streaming Destinations API - Configure YouTube, Facebook, Twitch, etc.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel

from models.database import get_db
from models.destination import StreamingDestination
from services.youtube_api_helper import YouTubeAPIHelper, YouTubeAPIError
from services.youtube_oauth import (
    YouTubeOAuthManager,
    YouTubeOAuthError,
    DatabaseYouTubeTokenProvider,
)

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


# Pydantic schemas
class YouTubeWatchdogConfig(BaseModel):
    """YouTube-specific watchdog configuration"""
    enable_watchdog: bool = False
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3


class DestinationCreate(BaseModel):
    name: str
    platform: str  # "youtube", "facebook", "twitch", "custom"
    rtmp_url: str
    stream_key: str
    description: str = ""
    channel_id: Optional[str] = None
    
    # YouTube watchdog configuration (optional)
    enable_watchdog: bool = False
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3
    # YouTube OAuth credentials (per-destination)
    youtube_oauth_client_id: Optional[str] = None
    youtube_oauth_client_secret: Optional[str] = None
    youtube_oauth_redirect_uri: Optional[str] = None


class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    rtmp_url: Optional[str] = None
    stream_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    channel_id: Optional[str] = None
    
    # YouTube watchdog configuration (optional)
    enable_watchdog: Optional[bool] = None
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: Optional[int] = None
    watchdog_enable_frame_probe: Optional[bool] = None
    watchdog_enable_daily_reset: Optional[bool] = None
    watchdog_daily_reset_hour: Optional[int] = None
    # YouTube OAuth credentials (per-destination)
    youtube_oauth_client_id: Optional[str] = None
    youtube_oauth_client_secret: Optional[str] = None
    youtube_oauth_redirect_uri: Optional[str] = None


class DestinationResponse(BaseModel):
    id: int
    name: str
    platform: str
    rtmp_url: str
    stream_key: str  # Note: In production, you might want to mask this
    description: str
    channel_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None
    
    # YouTube watchdog configuration
    enable_watchdog: bool = False
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3
    youtube_oauth_connected: bool = False
    youtube_token_expires_at: Optional[datetime] = None
    youtube_oauth_scopes: Optional[str] = None
    # YouTube OAuth credentials (per-destination)
    youtube_oauth_client_id: Optional[str] = None
    youtube_oauth_client_secret: Optional[str] = None
    youtube_oauth_redirect_uri: Optional[str] = None

    class Config:
        from_attributes = True


class YouTubeOAuthStatus(BaseModel):
    connected: bool
    expires_at: Optional[datetime]
    scopes: Optional[str]


class YouTubeOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class YouTubeOAuthStartRequest(BaseModel):
    prompt_consent: bool = False


class YouTubeOAuthCallbackRequest(BaseModel):
    code: str
    state: str


class CreateBroadcastRequest(BaseModel):
    """Request to create a new YouTube broadcast"""
    title: str
    description: str = ""
    privacy_status: str = "public"  # "public", "unlisted", "private"
    create_stream: bool = False  # If True, also create and bind a new stream
    frame_rate: str = "30fps"
    resolution: str = "1080p"
    enable_dvr: bool = False  # Enable DVR (allows viewers to rewind/replay)


class YouTubeBroadcastTransitionRequest(BaseModel):
    status: Literal['testing', 'live', 'complete']


# Platform presets for easy setup
PLATFORM_PRESETS = {
    "youtube": {
        "name": "YouTube Live",
        "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
        "description": "YouTube Live primary server"
    },
    "facebook": {
        "name": "Facebook Live",
        "rtmp_url": "rtmps://live-api-s.facebook.com:443/rtmp",
        "description": "Facebook Live streaming"
    },
    "twitch": {
        "name": "Twitch",
        "rtmp_url": "rtmp://live.twitch.tv/app",
        "description": "Twitch live streaming"
    },
    "custom": {
        "name": "Custom RTMP",
        "rtmp_url": "",
        "description": "Custom RTMP server"
    }
}


def _get_oauth_manager(destination: Optional[StreamingDestination] = None) -> YouTubeOAuthManager:
    """Get OAuth manager using destination credentials if available, else fall back to env vars."""
    try:
        client_id = None
        client_secret = None
        redirect_uri = None
        
        if destination and destination.youtube_oauth_client_id:
            client_id = destination.youtube_oauth_client_id
            client_secret = destination.youtube_oauth_client_secret
            redirect_uri = destination.youtube_oauth_redirect_uri
        
        return YouTubeOAuthManager(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
    except YouTubeOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


def _serialize_destination(destination: StreamingDestination) -> DestinationResponse:
    response = DestinationResponse.model_validate(destination)
    response.youtube_oauth_connected = destination.youtube_oauth_connected
    response.youtube_token_expires_at = destination.youtube_token_expires_at
    response.youtube_oauth_scopes = destination.youtube_oauth_scopes
    return response


def _build_oauth_status(destination: StreamingDestination) -> YouTubeOAuthStatus:
    return YouTubeOAuthStatus(
        connected=destination.youtube_oauth_connected,
        expires_at=destination.youtube_token_expires_at,
        scopes=destination.youtube_oauth_scopes,
    )


@router.get("/presets")
def get_platform_presets():
    """Get platform presets for easy setup"""
    return PLATFORM_PRESETS


@router.get("/", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db)):
    """Get all streaming destinations"""
    destinations = db.query(StreamingDestination).order_by(StreamingDestination.created_at.desc()).all()
    return [_serialize_destination(dest) for dest in destinations]


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    """Get a specific destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    return _serialize_destination(destination)


@router.post("/", response_model=DestinationResponse)
def create_destination(destination_data: DestinationCreate, db: Session = Depends(get_db)):
    """Create a new streaming destination"""
    try:
        destination = StreamingDestination(
            name=destination_data.name,
            platform=destination_data.platform,
            rtmp_url=destination_data.rtmp_url,
            stream_key=destination_data.stream_key,
            description=destination_data.description,
            channel_id=destination_data.channel_id,
            # YouTube watchdog fields
            enable_watchdog=destination_data.enable_watchdog,
            youtube_api_key=destination_data.youtube_api_key,
            youtube_stream_id=destination_data.youtube_stream_id,
            youtube_broadcast_id=destination_data.youtube_broadcast_id,
            youtube_watch_url=destination_data.youtube_watch_url,
            watchdog_check_interval=destination_data.watchdog_check_interval,
            watchdog_enable_frame_probe=destination_data.watchdog_enable_frame_probe,
            watchdog_enable_daily_reset=destination_data.watchdog_enable_daily_reset,
            watchdog_daily_reset_hour=destination_data.watchdog_daily_reset_hour,
            # YouTube OAuth credentials
            youtube_oauth_client_id=destination_data.youtube_oauth_client_id,
            youtube_oauth_client_secret=destination_data.youtube_oauth_client_secret,
            youtube_oauth_redirect_uri=destination_data.youtube_oauth_redirect_uri
        )
        db.add(destination)
        db.commit()
        db.refresh(destination)
        return _serialize_destination(destination)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create destination: {str(e)}")


@router.put("/{destination_id}", response_model=DestinationResponse)
def update_destination(
    destination_id: int,
    destination_data: DestinationUpdate,
    db: Session = Depends(get_db)
):
    """Update a streaming destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    # Update basic fields
    if destination_data.name is not None:
        destination.name = destination_data.name
    if destination_data.platform is not None:
        destination.platform = destination_data.platform
    if destination_data.rtmp_url is not None:
        destination.rtmp_url = destination_data.rtmp_url
    if destination_data.stream_key is not None:
        destination.stream_key = destination_data.stream_key
    if destination_data.description is not None:
        destination.description = destination_data.description
    if destination_data.channel_id is not None:
        destination.channel_id = destination_data.channel_id
    if destination_data.is_active is not None:
        destination.is_active = destination_data.is_active
    
    # Update YouTube watchdog fields
    if destination_data.enable_watchdog is not None:
        destination.enable_watchdog = destination_data.enable_watchdog
    if destination_data.youtube_api_key is not None:
        destination.youtube_api_key = destination_data.youtube_api_key
    if destination_data.youtube_stream_id is not None:
        destination.youtube_stream_id = destination_data.youtube_stream_id
    if destination_data.youtube_broadcast_id is not None:
        destination.youtube_broadcast_id = destination_data.youtube_broadcast_id
    if destination_data.youtube_watch_url is not None:
        destination.youtube_watch_url = destination_data.youtube_watch_url
    if destination_data.watchdog_check_interval is not None:
        destination.watchdog_check_interval = destination_data.watchdog_check_interval
    if destination_data.watchdog_enable_frame_probe is not None:
        destination.watchdog_enable_frame_probe = destination_data.watchdog_enable_frame_probe
    if destination_data.watchdog_enable_daily_reset is not None:
        destination.watchdog_enable_daily_reset = destination_data.watchdog_enable_daily_reset
    if destination_data.watchdog_daily_reset_hour is not None:
        destination.watchdog_daily_reset_hour = destination_data.watchdog_daily_reset_hour
    
    # Update YouTube OAuth credentials
    if destination_data.youtube_oauth_client_id is not None:
        destination.youtube_oauth_client_id = destination_data.youtube_oauth_client_id
    if destination_data.youtube_oauth_client_secret is not None:
        destination.youtube_oauth_client_secret = destination_data.youtube_oauth_client_secret
    if destination_data.youtube_oauth_redirect_uri is not None:
        destination.youtube_oauth_redirect_uri = destination_data.youtube_oauth_redirect_uri
    
    destination.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(destination)
    return _serialize_destination(destination)


@router.delete("/{destination_id}")
def delete_destination(destination_id: int, db: Session = Depends(get_db)):
    """Delete a streaming destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    db.delete(destination)
    db.commit()
    return {"message": "Destination deleted successfully"}


@router.post("/{destination_id}/mark-used")
def mark_destination_used(destination_id: int, db: Session = Depends(get_db)):
    """Mark a destination as recently used (updates last_used timestamp)"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    destination.last_used = datetime.utcnow()
    db.commit()
    
    return {"message": "Destination marked as used"}


@router.get("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def get_watchdog_config(destination_id: int, db: Session = Depends(get_db)):
    """Get YouTube watchdog configuration for a destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    return YouTubeWatchdogConfig(
        enable_watchdog=destination.enable_watchdog or False,
        youtube_api_key=destination.youtube_api_key,
        youtube_stream_id=destination.youtube_stream_id,
        youtube_broadcast_id=destination.youtube_broadcast_id,
        youtube_watch_url=destination.youtube_watch_url,
        watchdog_check_interval=destination.watchdog_check_interval or 30,
        watchdog_enable_frame_probe=destination.watchdog_enable_frame_probe or False,
        watchdog_enable_daily_reset=destination.watchdog_enable_daily_reset or False,
        watchdog_daily_reset_hour=destination.watchdog_daily_reset_hour or 3
    )


@router.put("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def update_watchdog_config(
    destination_id: int,
    config: YouTubeWatchdogConfig,
    db: Session = Depends(get_db)
):
    """Update YouTube watchdog configuration for a destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    # Update watchdog configuration
    destination.enable_watchdog = config.enable_watchdog
    destination.youtube_api_key = config.youtube_api_key
    destination.youtube_stream_id = config.youtube_stream_id
    destination.youtube_broadcast_id = config.youtube_broadcast_id
    destination.youtube_watch_url = config.youtube_watch_url
    destination.watchdog_check_interval = config.watchdog_check_interval
    destination.watchdog_enable_frame_probe = config.watchdog_enable_frame_probe
    destination.watchdog_enable_daily_reset = config.watchdog_enable_daily_reset
    destination.watchdog_daily_reset_hour = config.watchdog_daily_reset_hour
    destination.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(destination)

    return config


@router.get("/{destination_id}/youtube/oauth-status", response_model=YouTubeOAuthStatus)
def get_youtube_oauth_status(destination_id: int, db: Session = Depends(get_db)):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    return _build_oauth_status(destination)


@router.post("/{destination_id}/youtube/oauth-start", response_model=YouTubeOAuthStartResponse)
def start_youtube_oauth(
    destination_id: int,
    request: YouTubeOAuthStartRequest = YouTubeOAuthStartRequest(),
    db: Session = Depends(get_db)
):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")

    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="OAuth is only available for YouTube destinations")

    manager = _get_oauth_manager(destination)
    authorization_url, state = manager.generate_authorization_url(destination, prompt_consent=request.prompt_consent)
    db.add(destination)
    db.commit()
    return YouTubeOAuthStartResponse(authorization_url=authorization_url, state=state)


@router.post("/{destination_id}/youtube/oauth-complete", response_model=YouTubeOAuthStatus)
def complete_youtube_oauth(
    destination_id: int,
    payload: YouTubeOAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")

    manager = _get_oauth_manager(destination)
    manager.exchange_code(db, destination, code=payload.code, state=payload.state)
    db.refresh(destination)
    return _build_oauth_status(destination)


@router.delete("/{destination_id}/youtube/oauth", response_model=YouTubeOAuthStatus)
def disconnect_youtube_oauth(destination_id: int, db: Session = Depends(get_db)):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")

    manager = _get_oauth_manager(destination)
    manager.clear_tokens(db, destination)
    db.refresh(destination)
    return _build_oauth_status(destination)


@router.get("/youtube/oauth/callback", response_class=HTMLResponse)
def youtube_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    OAuth callback endpoint that Google redirects to after user authorization.
    This endpoint exchanges the authorization code for access/refresh tokens.
    """
    destination = (
        db.query(StreamingDestination)
        .filter(StreamingDestination.youtube_oauth_state == state)
        .first()
    )
    if not destination:
        return HTMLResponse(
            status_code=400,
            content="""
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                    h1 { color: #dc2626; }
                    .error-box { background: #fee2e2; border: 1px solid #dc2626; padding: 20px; border-radius: 8px; max-width: 500px; margin: 20px auto; }
                </style>
            </head>
            <body>
                <h1>❌ Authorization Failed</h1>
                <div class="error-box">
                    <p><strong>Invalid or expired OAuth state.</strong></p>
                    <p>Please close this window and start the authorization process again from VistterStream.</p>
                </div>
            </body>
            </html>
            """,
        )

    try:
        manager = _get_oauth_manager(destination)
        manager.exchange_code(db, destination, code=code, state=state)
        
        # Success! Show a friendly message and auto-close script
        return HTMLResponse(
            content="""
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
                    h1 { color: #16a34a; }
                    .success-box { background: #dcfce7; border: 1px solid #16a34a; padding: 20px; border-radius: 8px; max-width: 500px; margin: 20px auto; }
                    .instructions { margin-top: 20px; color: #4b5563; }
                </style>
            </head>
            <body>
                <h1>✅ Authorization Complete!</h1>
                <div class="success-box">
                    <p><strong>Your YouTube account has been successfully connected.</strong></p>
                    <p>You may close this window and return to VistterStream.</p>
                    <div class="instructions">
                        <small>This window will automatically close in 3 seconds...</small>
                    </div>
                </div>
                <script>
                    // Notify parent window that OAuth completed successfully
                    if (window.opener && !window.opener.closed) {
                        try {
                            // Try to call a callback function if it exists
                            if (window.opener.oauthComplete) {
                                window.opener.oauthComplete();
                            }
                            // Also try postMessage for cross-origin scenarios
                            window.opener.postMessage({ type: 'oauth_complete', success: true }, '*');
                        } catch (e) {
                            console.log('Could not notify parent window:', e);
                        }
                    }
                    
                    // Auto-close after 3 seconds
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                </script>
            </body>
            </html>
            """
        )
        
    except HTTPException as http_exc:
        # Handle HTTP exceptions (from OAuth manager or exchange_code)
        return HTMLResponse(
            status_code=http_exc.status_code,
            content=f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; }}
                    h1 {{ color: #dc2626; }}
                    .error-box {{ background: #fee2e2; border: 1px solid #dc2626; padding: 20px; border-radius: 8px; max-width: 600px; margin: 20px auto; }}
                    .error-detail {{ background: #fef2f2; padding: 10px; margin-top: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; }}
                </style>
            </head>
            <body>
                <h1>❌ Authorization Failed</h1>
                <div class="error-box">
                    <p><strong>Error during OAuth token exchange:</strong></p>
                    <div class="error-detail">{http_exc.detail}</div>
                    <p style="margin-top: 20px;">Please close this window and try again. Make sure OAuth credentials are properly configured in your destination settings.</p>
                </div>
            </body>
            </html>
            """,
        )
        
    except Exception as exc:
        # Handle any other unexpected errors
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Unexpected error in OAuth callback: {error_trace}")
        
        return HTMLResponse(
            status_code=500,
            content=f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 40px; text-align: center; }}
                    h1 {{ color: #dc2626; }}
                    .error-box {{ background: #fee2e2; border: 1px solid #dc2626; padding: 20px; border-radius: 8px; max-width: 600px; margin: 20px auto; }}
                    .error-detail {{ background: #fef2f2; padding: 10px; margin-top: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; text-align: left; }}
                </style>
            </head>
            <body>
                <h1>❌ Unexpected Error</h1>
                <div class="error-box">
                    <p><strong>An unexpected error occurred during authorization:</strong></p>
                    <div class="error-detail">{str(exc)}</div>
                    <p style="margin-top: 20px;">Please close this window and contact support if the problem persists.</p>
                </div>
            </body>
            </html>
            """,
    )


def _get_tokenized_helper(destination: StreamingDestination) -> YouTubeAPIHelper:
    provider = DatabaseYouTubeTokenProvider(destination)
    return YouTubeAPIHelper(token_provider=provider)


@router.get("/{destination_id}/youtube/broadcast-status")
async def get_youtube_broadcast_status(destination_id: int, db: Session = Depends(get_db)):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    if not destination.youtube_broadcast_id:
        raise HTTPException(status_code=400, detail="Destination does not have a YouTube broadcast ID configured")
    if not destination.youtube_refresh_token:
        raise HTTPException(status_code=400, detail="Destination is not connected to YouTube via OAuth")

    helper = _get_tokenized_helper(destination)
    try:
        async with helper:
            return await helper.get_broadcast_status(destination.youtube_broadcast_id)
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{destination_id}/youtube/stream-health")
async def get_youtube_stream_health(destination_id: int, db: Session = Depends(get_db)):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    if not destination.youtube_stream_id:
        raise HTTPException(status_code=400, detail="Destination does not have a YouTube stream ID configured")
    if not destination.youtube_refresh_token:
        raise HTTPException(status_code=400, detail="Destination is not connected to YouTube via OAuth")

    helper = _get_tokenized_helper(destination)
    try:
        async with helper:
            return await helper.get_stream_health(destination.youtube_stream_id)
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{destination_id}/youtube/transition")
async def transition_youtube_broadcast(
    destination_id: int,
    request: YouTubeBroadcastTransitionRequest,
    db: Session = Depends(get_db)
):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    if not destination.youtube_broadcast_id:
        raise HTTPException(status_code=400, detail="Destination does not have a YouTube broadcast ID configured")
    if not destination.youtube_refresh_token:
        raise HTTPException(status_code=400, detail="Destination is not connected to YouTube via OAuth")

    helper = _get_tokenized_helper(destination)
    try:
        async with helper:
            return await helper.transition_broadcast(destination.youtube_broadcast_id, request.status)
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{destination_id}/youtube/reset")
async def reset_youtube_broadcast(destination_id: int, db: Session = Depends(get_db)):
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    if not destination.youtube_broadcast_id:
        raise HTTPException(status_code=400, detail="Destination does not have a YouTube broadcast ID configured")
    if not destination.youtube_refresh_token:
        raise HTTPException(status_code=400, detail="Destination is not connected to YouTube via OAuth")

    helper = _get_tokenized_helper(destination)
    try:
        async with helper:
            return await helper.reset_broadcast(destination.youtube_broadcast_id)
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{destination_id}/youtube/create-broadcast")
async def create_youtube_broadcast(
    destination_id: int,
    request: CreateBroadcastRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new YouTube broadcast (and optionally create/bind a stream)
    
    This will:
    1. Create a new broadcast
    2. Optionally create a new stream and bind it
    3. Update the destination with the new broadcast ID and stream ID
    """
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Destination is not a YouTube destination")
    
    if not destination.youtube_oauth_connected:
        raise HTTPException(
            status_code=400,
            detail="Destination is not connected to YouTube via OAuth. Please connect OAuth first."
        )
    
    helper = _get_tokenized_helper(destination)
    
    try:
        async with helper:
            # Create the broadcast
            broadcast_result = await helper.create_broadcast(
                title=request.title,
                description=request.description,
                privacy_status=request.privacy_status,
                enable_dvr=request.enable_dvr
            )
            
            broadcast_id = broadcast_result['broadcast_id']
            video_id = broadcast_result['video_id']
            stream_id = None
            stream_key = None
            rtmp_url = None
            
            # Optionally create and bind a stream
            if request.create_stream:
                stream_result = await helper.create_stream(
                    title=request.title,
                    description=request.description,
                    frame_rate=request.frame_rate,
                    resolution=request.resolution
                )
                
                stream_id = stream_result['stream_id']
                stream_key = stream_result['stream_key']
                rtmp_url = stream_result['rtmp_url']
                
                # Bind the stream to the broadcast
                await helper.bind_stream_to_broadcast(broadcast_id, stream_id)
            
            # Update the destination with the new IDs
            destination.youtube_broadcast_id = broadcast_id
            if stream_id:
                destination.youtube_stream_id = stream_id
            if stream_key:
                destination.stream_key = stream_key
            if rtmp_url:
                destination.rtmp_url = rtmp_url
            
            db.commit()
            db.refresh(destination)
            
            return {
                "success": True,
                "broadcast_id": broadcast_id,
                "video_id": video_id,  # For Studio URL
                "stream_id": stream_id,
                "stream_key": stream_key,
                "rtmp_url": rtmp_url,
                "title": broadcast_result['title'],
                "privacy_status": broadcast_result['privacy_status'],
                "life_cycle_status": broadcast_result['life_cycle_status'],
                "studio_url": f"https://studio.youtube.com/video/{video_id}/livestreaming",
                "watch_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                "destination": _serialize_destination(destination)
            }
            
    except YouTubeAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create broadcast: {str(exc)}") from exc


@router.post("/{destination_id}/validate-watchdog")
async def validate_watchdog_config(destination_id: int, db: Session = Depends(get_db)):
    """Validate watchdog configuration"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if not destination.enable_watchdog:
        raise HTTPException(status_code=400, detail="Watchdog is not enabled for this destination")
    
    # For now, local watchdog doesn't require API validation
    # Just confirm the watchdog is enabled
    return {
        "status": "OK",
        "message": "Local watchdog is enabled and will monitor FFmpeg encoder health",
        "check_interval": destination.watchdog_check_interval or 30,
        "destination_name": destination.name,
        "destination_id": destination.id
    }

