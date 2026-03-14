"""
Streaming Destinations API - Configure YouTube, Facebook, Twitch, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
import hashlib
import hmac
from html import escape as html_escape
import logging
import os
import uuid

from models.database import get_db
from models.destination import StreamingDestination
from routers.auth import get_current_user
from utils.crypto import encrypt, decrypt

logger = logging.getLogger(__name__)

# ── Authenticated router (all existing routes + new YouTube OAuth routes) ────
router = APIRouter(prefix="/api/destinations", tags=["destinations"], dependencies=[Depends(get_current_user)])

# ── Public router for the OAuth callback (no auth required) ──────────────────
# Google redirects the browser here; there is no Bearer token in the request.
public_router = APIRouter(prefix="/api/destinations", tags=["destinations"])


# ── Pydantic models ─────────────────────────────────────────────────────────

class YouTubeWatchdogConfig(BaseModel):
    enable_watchdog: bool = True
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3


_ALLOWED_RTMP_SCHEMES = ("rtmp://", "rtmps://")
_ALLOWED_YOUTUBE_PREFIXES = ("https://www.youtube.com/", "https://youtube.com/")


class DestinationCreate(BaseModel):
    name: str
    platform: str
    rtmp_url: str = ""
    stream_key: str = ""
    description: str = ""
    channel_id: Optional[str] = None
    enable_watchdog: bool = True
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3
    # YouTube OAuth fields (plaintext secret from client)
    youtube_oauth_client_id: Optional[str] = None
    youtube_oauth_client_secret: Optional[str] = None
    youtube_oauth_redirect_uri: Optional[str] = None

    @field_validator("rtmp_url")
    @classmethod
    def validate_rtmp_url(cls, v: str) -> str:
        if v and not v.startswith(_ALLOWED_RTMP_SCHEMES):
            raise ValueError("rtmp_url must start with rtmp:// or rtmps://")
        return v

    @field_validator("youtube_watch_url")
    @classmethod
    def validate_youtube_watch_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(_ALLOWED_YOUTUBE_PREFIXES):
            raise ValueError("youtube_watch_url must start with https://www.youtube.com/ or https://youtube.com/")
        return v


class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    rtmp_url: Optional[str] = None
    stream_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    channel_id: Optional[str] = None
    enable_watchdog: Optional[bool] = None
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: Optional[int] = None
    watchdog_enable_frame_probe: Optional[bool] = None
    watchdog_enable_daily_reset: Optional[bool] = None
    watchdog_daily_reset_hour: Optional[int] = None
    # YouTube OAuth fields (plaintext secret from client)
    youtube_oauth_client_id: Optional[str] = None
    youtube_oauth_client_secret: Optional[str] = None
    youtube_oauth_redirect_uri: Optional[str] = None

    @field_validator("rtmp_url")
    @classmethod
    def validate_rtmp_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(_ALLOWED_RTMP_SCHEMES):
            raise ValueError("rtmp_url must start with rtmp:// or rtmps://")
        return v

    @field_validator("youtube_watch_url")
    @classmethod
    def validate_youtube_watch_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(_ALLOWED_YOUTUBE_PREFIXES):
            raise ValueError("youtube_watch_url must start with https://www.youtube.com/ or https://youtube.com/")
        return v


class DestinationResponse(BaseModel):
    id: int
    name: str
    platform: str
    rtmp_url: str
    stream_key: str
    description: str
    channel_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None
    enable_watchdog: bool = True
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3
    # YouTube OAuth (public fields only - never expose secrets/tokens)
    youtube_oauth_connected: bool = False
    youtube_oauth_channel_name: Optional[str] = None
    youtube_oauth_token_expires_at: Optional[datetime] = None
    youtube_oauth_scopes: Optional[str] = None
    youtube_oauth_client_id: Optional[str] = None
    youtube_oauth_redirect_uri: Optional[str] = None

    class Config:
        from_attributes = True


class OAuthStartRequest(BaseModel):
    prompt_consent: bool = True


class CreateBroadcastRequest(BaseModel):
    title: str
    description: str = ""
    privacy_status: str = "unlisted"
    create_stream: bool = True
    frame_rate: str = "30fps"
    resolution: str = "1080p"
    enable_dvr: bool = True


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_dest_or_404(destination_id: int, db: Session) -> StreamingDestination:
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    return dest


def _dest_to_response(dest: StreamingDestination) -> dict:
    """Convert a destination ORM object to a dict safe for DestinationResponse."""
    data = {c.name: getattr(dest, c.name) for c in dest.__table__.columns}
    # Mask encrypted secrets — don't expose raw keys in API responses
    if data.get("stream_key"):
        data["stream_key"] = "••••••••"
    if data.get("youtube_api_key"):
        data["youtube_api_key"] = "••••••••"
    # Strip encrypted fields and add computed response fields
    data.pop("youtube_oauth_client_secret_enc", None)
    data.pop("youtube_oauth_refresh_token_enc", None)
    data["youtube_oauth_scopes"] = (
        "youtube, youtube.upload, youtube.readonly" if dest.youtube_oauth_connected else None
    )
    data.setdefault("youtube_oauth_connected", False)
    data.setdefault("youtube_oauth_channel_name", None)
    data.setdefault("youtube_oauth_token_expires_at", None)
    return data


def _generate_oauth_state(destination_id: int) -> str:
    """Generate an HMAC-signed OAuth state token encoding the destination ID."""
    secret = os.getenv("JWT_SECRET_KEY", "")
    nonce = uuid.uuid4().hex
    payload = f"{destination_id}:{nonce}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _verify_oauth_state(state: str) -> Optional[int]:
    """Verify an HMAC-signed OAuth state token and return the destination ID."""
    secret = os.getenv("JWT_SECRET_KEY", "")
    parts = state.split(":")
    if len(parts) != 3:
        return None
    dest_id_str, nonce, sig = parts
    expected = hmac.new(secret.encode(), f"{dest_id_str}:{nonce}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return int(dest_id_str)
    except ValueError:
        return None


PLATFORM_PRESETS = {
    "youtube": {"name": "YouTube Live", "rtmp_url": "rtmp://a.rtmp.youtube.com/live2", "description": "YouTube Live"},
    "youtube_oauth": {"name": "YouTube (OAuth)", "rtmp_url": "", "description": "YouTube Live via OAuth - auto-creates broadcasts"},
    "facebook": {"name": "Facebook Live", "rtmp_url": "rtmps://live-api-s.facebook.com:443/rtmp", "description": "Facebook Live"},
    "twitch": {"name": "Twitch", "rtmp_url": "rtmp://live.twitch.tv/app", "description": "Twitch"},
    "custom": {"name": "Custom RTMP", "rtmp_url": "", "description": "Custom RTMP server"},
}


# ── Existing CRUD routes ────────────────────────────────────────────────────

@router.get("/presets")
def get_platform_presets():
    return PLATFORM_PRESETS


@router.get("", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db)):
    dests = db.query(StreamingDestination).order_by(StreamingDestination.created_at.desc()).all()
    return [_dest_to_response(d) for d in dests]


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    dest = _get_dest_or_404(destination_id, db)
    return _dest_to_response(dest)


@router.post("", response_model=DestinationResponse)
def create_destination(data: DestinationCreate, db: Session = Depends(get_db)):
    fields = data.model_dump(exclude={"youtube_oauth_client_secret"})
    # Encrypt secrets before storage
    if fields.get("stream_key"):
        fields["stream_key"] = encrypt(fields["stream_key"])
    if fields.get("youtube_api_key"):
        fields["youtube_api_key"] = encrypt(fields["youtube_api_key"])
    secret = data.youtube_oauth_client_secret
    if secret:
        fields["youtube_oauth_client_secret_enc"] = encrypt(secret)
    dest = StreamingDestination(**fields)
    db.add(dest)
    db.commit()
    db.refresh(dest)
    return _dest_to_response(dest)


@router.put("/{destination_id}", response_model=DestinationResponse)
def update_destination(destination_id: int, data: DestinationUpdate, db: Session = Depends(get_db)):
    dest = _get_dest_or_404(destination_id, db)
    updates = data.model_dump(exclude_unset=True)
    # Handle OAuth secret encryption
    # Encrypt secrets before storage (skip masked placeholder values from frontend)
    if "stream_key" in updates and updates["stream_key"] and updates["stream_key"] != "••••••••":
        updates["stream_key"] = encrypt(updates["stream_key"])
    elif "stream_key" in updates and updates["stream_key"] == "••••••••":
        del updates["stream_key"]  # Don't overwrite with mask
    if "youtube_api_key" in updates and updates["youtube_api_key"] and updates["youtube_api_key"] != "••••••••":
        updates["youtube_api_key"] = encrypt(updates["youtube_api_key"])
    elif "youtube_api_key" in updates and updates["youtube_api_key"] == "••••••••":
        del updates["youtube_api_key"]  # Don't overwrite with mask
    secret = updates.pop("youtube_oauth_client_secret", None)
    if secret is not None:
        dest.youtube_oauth_client_secret_enc = encrypt(secret) if secret else None
    for field, value in updates.items():
        setattr(dest, field, value)
    dest.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dest)
    return _dest_to_response(dest)


@router.delete("/{destination_id}")
def delete_destination(destination_id: int, db: Session = Depends(get_db)):
    dest = _get_dest_or_404(destination_id, db)
    db.delete(dest)
    db.commit()
    return {"message": "Destination deleted"}


@router.post("/{destination_id}/mark-used")
def mark_destination_used(destination_id: int, db: Session = Depends(get_db)):
    dest = _get_dest_or_404(destination_id, db)
    dest.last_used = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Marked as used"}


@router.get("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def get_watchdog_config(destination_id: int, db: Session = Depends(get_db)):
    dest = _get_dest_or_404(destination_id, db)
    api_key = None
    if dest.youtube_api_key:
        try:
            api_key = decrypt(dest.youtube_api_key)
        except Exception:
            api_key = dest.youtube_api_key  # fallback for legacy plaintext
    return YouTubeWatchdogConfig(
        enable_watchdog=dest.enable_watchdog or False, youtube_api_key=api_key,
        youtube_stream_id=dest.youtube_stream_id, youtube_broadcast_id=dest.youtube_broadcast_id,
        youtube_watch_url=dest.youtube_watch_url, watchdog_check_interval=dest.watchdog_check_interval or 30,
        watchdog_enable_frame_probe=dest.watchdog_enable_frame_probe or False,
        watchdog_enable_daily_reset=dest.watchdog_enable_daily_reset or False,
        watchdog_daily_reset_hour=dest.watchdog_daily_reset_hour or 3
    )


@router.put("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def update_watchdog_config(destination_id: int, config: YouTubeWatchdogConfig, db: Session = Depends(get_db)):
    dest = _get_dest_or_404(destination_id, db)
    dest.enable_watchdog = config.enable_watchdog
    dest.youtube_api_key = encrypt(config.youtube_api_key) if config.youtube_api_key else None
    dest.youtube_stream_id = config.youtube_stream_id
    dest.youtube_broadcast_id = config.youtube_broadcast_id
    dest.youtube_watch_url = config.youtube_watch_url
    dest.watchdog_check_interval = config.watchdog_check_interval
    dest.watchdog_enable_frame_probe = config.watchdog_enable_frame_probe
    dest.watchdog_enable_daily_reset = config.watchdog_enable_daily_reset
    dest.watchdog_daily_reset_hour = config.watchdog_daily_reset_hour
    dest.updated_at = datetime.now(timezone.utc)
    db.commit()
    return config


# ── YouTube OAuth routes (authenticated) ────────────────────────────────────

@router.post("/{destination_id}/youtube/oauth-start")
def youtube_oauth_start(destination_id: int, body: OAuthStartRequest, db: Session = Depends(get_db)):
    """Generate a YouTube OAuth authorization URL for this destination."""
    from services.youtube_destination_service import get_oauth_url

    dest = _get_dest_or_404(destination_id, db)

    if not dest.youtube_oauth_client_id or not dest.youtube_oauth_client_secret_enc:
        raise HTTPException(status_code=400, detail="YouTube OAuth client credentials not configured on this destination")
    if not dest.youtube_oauth_redirect_uri:
        raise HTTPException(status_code=400, detail="YouTube OAuth redirect URI not configured on this destination")

    client_secret = decrypt(dest.youtube_oauth_client_secret_enc)

    state_token = _generate_oauth_state(dest.id)
    auth_url, code_verifier = get_oauth_url(
        client_id=dest.youtube_oauth_client_id,
        client_secret=client_secret,
        redirect_uri=dest.youtube_oauth_redirect_uri,
        state=state_token,
        prompt_consent=body.prompt_consent,
    )

    # Store code_verifier for the callback to use (PKCE)
    dest.youtube_oauth_code_verifier = code_verifier
    db.commit()

    return {"authorization_url": auth_url}


@router.get("/{destination_id}/youtube/oauth-status")
def youtube_oauth_status(destination_id: int, db: Session = Depends(get_db)):
    """Return the current YouTube OAuth connection status."""
    dest = _get_dest_or_404(destination_id, db)
    return {
        "connected": dest.youtube_oauth_connected or False,
        "channel_name": dest.youtube_oauth_channel_name,
        "expires_at": dest.youtube_oauth_token_expires_at.isoformat() if dest.youtube_oauth_token_expires_at else None,
        "scopes": "youtube, youtube.upload, youtube.readonly" if dest.youtube_oauth_connected else None,
    }


@router.delete("/{destination_id}/youtube/oauth")
def youtube_oauth_disconnect(destination_id: int, db: Session = Depends(get_db)):
    """Disconnect the YouTube OAuth account from this destination."""
    dest = _get_dest_or_404(destination_id, db)
    dest.youtube_oauth_refresh_token_enc = None
    dest.youtube_oauth_connected = False
    dest.youtube_oauth_channel_name = None
    dest.youtube_oauth_token_expires_at = None
    dest.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Disconnected"}


@router.post("/{destination_id}/youtube/create-broadcast")
def youtube_create_broadcast(destination_id: int, body: CreateBroadcastRequest, db: Session = Depends(get_db)):
    """Create a YouTube live broadcast (and optionally a bound stream) using stored OAuth creds."""
    from services.youtube_destination_service import get_credentials, create_broadcast

    dest = _get_dest_or_404(destination_id, db)

    if not dest.youtube_oauth_connected or not dest.youtube_oauth_refresh_token_enc:
        raise HTTPException(status_code=400, detail="YouTube OAuth not connected for this destination")
    if not dest.youtube_oauth_client_id or not dest.youtube_oauth_client_secret_enc:
        raise HTTPException(status_code=400, detail="YouTube OAuth client credentials missing")

    client_secret = decrypt(dest.youtube_oauth_client_secret_enc)
    refresh_token = decrypt(dest.youtube_oauth_refresh_token_enc)

    credentials = get_credentials(
        client_id=dest.youtube_oauth_client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
    )

    try:
        result = create_broadcast(
            credentials=credentials,
            title=body.title,
            description=body.description,
            privacy_status=body.privacy_status,
            create_stream=body.create_stream,
            frame_rate=body.frame_rate,
            resolution=body.resolution,
            enable_dvr=body.enable_dvr,
        )
    except Exception as e:
        logger.error("Failed to create YouTube broadcast: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create broadcast: {e}")

    # Persist broadcast/stream details back to the destination
    dest.youtube_broadcast_id = result.get("broadcast_id")
    dest.youtube_stream_id = result.get("stream_id")
    if result.get("stream_key"):
        dest.stream_key = encrypt(result["stream_key"])
    if result.get("rtmp_url"):
        dest.rtmp_url = result["rtmp_url"]
    if result.get("watch_url"):
        dest.youtube_watch_url = result["watch_url"]
    dest.updated_at = datetime.now(timezone.utc)
    db.commit()

    return result


# ── YouTube OAuth callback (public - no auth) ───────────────────────────────

@public_router.get("/youtube/oauth/callback", response_class=HTMLResponse)
def youtube_oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: Session = Depends(get_db),
):
    """
    Handle the Google OAuth redirect. ``state`` contains the destination ID.
    Returns HTML that posts a message to the opener window and auto-closes.
    """
    from services.youtube_destination_service import exchange_code

    if not state:
        return HTMLResponse(content=_oauth_error_html("Missing state parameter"), status_code=400)

    destination_id = _verify_oauth_state(state)
    if destination_id is None:
        return HTMLResponse(content=_oauth_error_html("Invalid or tampered state parameter"), status_code=400)

    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        return HTMLResponse(content=_oauth_error_html("Destination not found"), status_code=404)

    if not dest.youtube_oauth_client_id or not dest.youtube_oauth_client_secret_enc:
        return HTMLResponse(content=_oauth_error_html("OAuth credentials not configured"), status_code=400)

    try:
        client_secret = decrypt(dest.youtube_oauth_client_secret_enc)
        result = exchange_code(
            code=code,
            client_id=dest.youtube_oauth_client_id,
            client_secret=client_secret,
            redirect_uri=dest.youtube_oauth_redirect_uri or "",
            code_verifier=dest.youtube_oauth_code_verifier,
        )

        # Store encrypted refresh token and mark as connected
        dest.youtube_oauth_refresh_token_enc = encrypt(result["refresh_token"])
        dest.youtube_oauth_connected = True
        dest.youtube_oauth_channel_name = result["channel_name"]
        dest.youtube_oauth_code_verifier = None  # clear temporary value
        dest.updated_at = datetime.now(timezone.utc)
        db.commit()

        return HTMLResponse(content=_oauth_success_html(result["channel_name"]))

    except Exception as e:
        logger.error("YouTube OAuth callback failed for destination %s: %s", destination_id, e)
        return HTMLResponse(content=_oauth_error_html(str(e)), status_code=500)


def _oauth_success_html(channel_name: str) -> str:
    safe_name = html_escape(channel_name)
    return f"""
    <html>
    <body>
        <h1>YouTube Connected!</h1>
        <p>Connected to channel: <strong>{safe_name}</strong></p>
        <p>You can close this window.</p>
        <script>
            window.opener.postMessage('youtube-connected', '*');
            setTimeout(() => window.close(), 2000);
        </script>
    </body>
    </html>
    """


def _oauth_error_html(message: str) -> str:
    safe_message = html_escape(message)
    return f"""
    <html>
    <body>
        <h1>Connection Failed</h1>
        <p>{safe_message}</p>
        <script>
            window.opener.postMessage('youtube-error', '*');
        </script>
    </body>
    </html>
    """
