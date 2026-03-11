"""
YouTube Destination Service

Handles OAuth authentication and broadcast/stream creation for YouTube Live
streaming destinations. Reuses OAuth patterns from youtube_shorts_service.py.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


logger = logging.getLogger(__name__)

YOUTUBE_DESTINATION_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

_CLIENT_CONFIG_TEMPLATE = {
    "web": {
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def _build_client_config(client_id: str, client_secret: str) -> dict:
    """Build the Google OAuth client config dict."""
    config = {
        "web": {
            **_CLIENT_CONFIG_TEMPLATE["web"],
            "client_id": client_id,
            "client_secret": client_secret,
        }
    }
    return config


def get_oauth_url(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    state: str = "",
    prompt_consent: bool = True,
) -> Tuple[str, Optional[str]]:
    """
    Generate an OAuth authorization URL for YouTube.

    Args:
        client_id: Google OAuth Client ID
        client_secret: Google OAuth Client Secret
        redirect_uri: Callback URL after authorization
        state: Opaque state value (destination ID) passed through the OAuth flow
        prompt_consent: If True, always show the consent screen

    Returns:
        Authorization URL to redirect the user to
    """
    flow = Flow.from_client_config(
        _build_client_config(client_id, client_secret),
        scopes=YOUTUBE_DESTINATION_SCOPES,
        redirect_uri=redirect_uri,
    )

    kwargs = {
        "access_type": "offline",
        "include_granted_scopes": "true",
        "state": state,
    }
    if prompt_consent:
        kwargs["prompt"] = "consent"

    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url, getattr(flow, "code_verifier", None)


def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code_verifier: Optional[str] = None,
) -> Dict:
    """
    Exchange an authorization code for tokens and fetch channel info.

    Returns:
        Dict with ``refresh_token`` and ``channel_name``.
    """
    flow = Flow.from_client_config(
        _build_client_config(client_id, client_secret),
        scopes=YOUTUBE_DESTINATION_SCOPES,
        redirect_uri=redirect_uri,
    )
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Fetch channel info
    youtube = build("youtube", "v3", credentials=credentials)
    channel_response = youtube.channels().list(part="snippet", mine=True).execute()

    channel_name = "Unknown"
    if channel_response.get("items"):
        channel_name = channel_response["items"][0]["snippet"]["title"]

    return {
        "refresh_token": credentials.refresh_token,
        "channel_name": channel_name,
    }


def get_credentials(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> Credentials:
    """Create a ``Credentials`` object from stored tokens."""
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=YOUTUBE_DESTINATION_SCOPES,
    )


def create_broadcast(
    credentials: Credentials,
    title: str,
    description: str = "",
    privacy_status: str = "unlisted",
    create_stream: bool = True,
    frame_rate: str = "30fps",
    resolution: str = "1080p",
    enable_dvr: bool = True,
) -> Dict:
    """
    Create a YouTube live broadcast (and optionally a bound stream).

    Returns a dict with broadcast_id, video_id, stream_id, stream_key,
    rtmp_url, studio_url, and watch_url.
    """
    youtube = build("youtube", "v3", credentials=credentials)

    # --- Create the broadcast ---
    broadcast_body = {
        "snippet": {
            "title": title,
            "description": description,
            "scheduledStartTime": (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat(),
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
        "contentDetails": {
            "enableDvr": enable_dvr,
            "enableAutoStart": True,
            "enableAutoStop": True,
        },
    }

    broadcast = (
        youtube.liveBroadcasts()
        .insert(part="snippet,status,contentDetails", body=broadcast_body)
        .execute()
    )

    broadcast_id = broadcast["id"]
    video_id = broadcast_id  # broadcast ID is the video ID for live broadcasts

    result: Dict = {
        "broadcast_id": broadcast_id,
        "video_id": video_id,
        "stream_id": None,
        "stream_key": None,
        "rtmp_url": None,
        "studio_url": f"https://studio.youtube.com/video/{video_id}/livestreaming",
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
    }

    if create_stream:
        # --- Create a stream ---
        stream_body = {
            "snippet": {
                "title": f"{title} - stream",
            },
            "cdn": {
                "frameRate": frame_rate,
                "resolution": resolution,
                "ingestionType": "rtmp",
            },
        }

        stream = (
            youtube.liveStreams()
            .insert(part="snippet,cdn", body=stream_body)
            .execute()
        )

        stream_id = stream["id"]
        ingestion = stream.get("cdn", {}).get("ingestionInfo", {})

        result["stream_id"] = stream_id
        result["stream_key"] = ingestion.get("streamName", "")
        result["rtmp_url"] = ingestion.get("ingestionAddress", "")

        # --- Bind stream to broadcast ---
        youtube.liveBroadcasts().bind(
            part="id,contentDetails",
            id=broadcast_id,
            streamId=stream_id,
        ).execute()

        logger.info(
            "Created broadcast %s with stream %s (key=%s)",
            broadcast_id,
            stream_id,
            result["stream_key"],
        )
    else:
        logger.info("Created broadcast %s (no stream)", broadcast_id)

    return result


def get_broadcast_status(credentials: Credentials, broadcast_id: str) -> Dict:
    """
    Check the lifecycle status of a broadcast.

    Returns a dict with ``status`` and ``life_cycle_status``.
    """
    youtube = build("youtube", "v3", credentials=credentials)
    response = (
        youtube.liveBroadcasts()
        .list(part="status", id=broadcast_id)
        .execute()
    )

    if not response.get("items"):
        return {"status": "not_found", "life_cycle_status": None}

    item = response["items"][0]
    return {
        "status": item["status"].get("recordingStatus", "unknown"),
        "life_cycle_status": item["status"].get("lifeCycleStatus", "unknown"),
    }
