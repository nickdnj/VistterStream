"""YouTube OAuth management helpers"""

from __future__ import annotations

import asyncio
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import requests
from fastapi import HTTPException
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.destination import StreamingDestination


OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtubepartner"
]

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class YouTubeOAuthError(Exception):
    """Raised when OAuth configuration or token refresh fails."""


class YouTubeOAuthManager:
    """Manage YouTube OAuth flows and token lifecycle."""

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("YOUTUBE_OAUTH_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("YOUTUBE_OAUTH_REDIRECT_URI")
        self.scopes = scopes or OAUTH_SCOPES

        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise YouTubeOAuthError(
                "YouTube OAuth environment variables are not fully configured. "
                "Set YOUTUBE_OAUTH_CLIENT_ID, YOUTUBE_OAUTH_CLIENT_SECRET, and "
                "YOUTUBE_OAUTH_REDIRECT_URI."
            )

    def _build_flow(self, state: Optional[str] = None) -> Flow:
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": TOKEN_ENDPOINT,
                "redirect_uris": [self.redirect_uri],
            }
        }

        flow = Flow.from_client_config(client_config, scopes=self.scopes, redirect_uri=self.redirect_uri)
        if state:
            flow.state = state
        return flow

    def generate_authorization_url(self, destination: StreamingDestination, *, prompt_consent: bool = False) -> Tuple[str, str]:
        """Create an authorization URL and store the state on the destination."""

        state = secrets.token_urlsafe(32)
        flow = self._build_flow(state=state)

        authorization_kwargs = {
            "access_type": "offline",
            "include_granted_scopes": "true",
            "state": state,
        }
        if prompt_consent:
            authorization_kwargs["prompt"] = "consent"

        authorization_url, _ = flow.authorization_url(**authorization_kwargs)

        destination.youtube_oauth_state = state
        return authorization_url, state

    def exchange_code(self, db: Session, destination: StreamingDestination, *, code: str, state: str) -> None:
        """Exchange an authorization code for tokens and persist them."""

        if not destination.youtube_oauth_state or destination.youtube_oauth_state != state:
            raise HTTPException(status_code=400, detail="OAuth state mismatch. Please restart the authorization flow.")

        flow = self._build_flow(state=state)
        try:
            flow.fetch_token(code=code)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Failed to exchange OAuth code: {exc}") from exc

        credentials = flow.credentials

        # Persist tokens
        destination.youtube_access_token = credentials.token
        if credentials.refresh_token:
            destination.youtube_refresh_token = credentials.refresh_token
        elif not destination.youtube_refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token returned. Re-run authorization with prompt=consent.")

        destination.youtube_token_expiry = credentials.expiry
        destination.youtube_oauth_scope = " ".join(credentials.scopes or []) or None
        destination.youtube_oauth_state = None

        db.add(destination)
        db.commit()

    def clear_tokens(self, db: Session, destination: StreamingDestination) -> None:
        """Remove OAuth credentials from the destination."""

        destination.youtube_access_token = None
        destination.youtube_refresh_token = None
        destination.youtube_token_expiry = None
        destination.youtube_oauth_scope = None
        destination.youtube_oauth_state = None
        db.add(destination)
        db.commit()

    def ensure_valid_access_token(
        self,
        db: Session,
        destination: StreamingDestination,
        *,
        force_refresh: bool = False,
    ) -> str:
        """Return a valid access token, refreshing if necessary."""

        if not destination.youtube_refresh_token:
            raise HTTPException(status_code=400, detail="Destination is not connected to YouTube via OAuth.")

        now = datetime.utcnow()
        if (
            not force_refresh
            and destination.youtube_access_token
            and destination.youtube_token_expiry
            and destination.youtube_token_expiry - timedelta(seconds=60) > now
        ):
            return destination.youtube_access_token

        response = requests.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": destination.youtube_refresh_token,
            },
            timeout=15,
        )

        if response.status_code != 200:
            detail = response.text
            raise HTTPException(status_code=400, detail=f"Failed to refresh YouTube token: {detail}")

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in", 3600)
        scope = payload.get("scope")

        if not access_token:
            raise HTTPException(status_code=400, detail="YouTube token refresh response missing access_token")

        destination.youtube_access_token = access_token
        destination.youtube_token_expiry = datetime.utcnow() + timedelta(seconds=int(expires_in))
        if scope:
            destination.youtube_oauth_scope = scope

        db.add(destination)
        db.commit()
        return access_token


class DatabaseYouTubeTokenProvider:
    """Async helper that hands out valid access tokens from the database."""

    def __init__(self, destination_id: int) -> None:
        self.destination_id = destination_id
        self.manager = YouTubeOAuthManager()

    def _refresh_sync(self, force_refresh: bool) -> str:
        session = SessionLocal()
        try:
            destination = (
                session.query(StreamingDestination)
                .filter(StreamingDestination.id == self.destination_id)
                .first()
            )
            if not destination:
                raise HTTPException(status_code=404, detail="Destination not found")
            token = self.manager.ensure_valid_access_token(session, destination, force_refresh=force_refresh)
            session.refresh(destination)
            return token
        finally:
            session.close()

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        return await asyncio.to_thread(self._refresh_sync, force_refresh)

    async def invalidate(self) -> None:
        def _invalidate() -> None:
            session = SessionLocal()
            try:
                destination = (
                    session.query(StreamingDestination)
                    .filter(StreamingDestination.id == self.destination_id)
                    .first()
                )
                if not destination:
                    return
                destination.youtube_token_expiry = datetime.utcnow() - timedelta(minutes=5)
                session.add(destination)
                session.commit()
            finally:
                session.close()

        await asyncio.to_thread(_invalidate)
