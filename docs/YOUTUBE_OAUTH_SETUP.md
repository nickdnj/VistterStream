# YouTube OAuth Setup for VistterStream

This guide walks through connecting a YouTube channel to VistterStream using OAuth so the watchdog can transition broadcasts automatically.

## 1. Create Google Cloud credentials

1. Sign in to [Google Cloud Console](https://console.cloud.google.com/) with the Gmail account that owns the target YouTube channel or brand account.
2. Create a new project (or reuse an existing one dedicated to VistterStream).
3. Enable the **YouTube Data API v3** for the project.
4. Configure the OAuth consent screen:
   - User type: **External**
   - App name/logo can be internal only while testing.
   - Add your Gmail address (and any teammate accounts) as test users.
   - Add the following scopes: `https://www.googleapis.com/auth/youtube`, `https://www.googleapis.com/auth/youtube.readonly`, and `https://www.googleapis.com/auth/youtubepartner`.
5. Create OAuth client credentials:
   - Application type: **Web application**.
   - Authorized redirect URI: `https://<your-backend-domain>/api/destinations/youtube/oauth/callback` (or the HTTPS tunnel you use during development).
   - Note the generated client ID and client secret.

## 2. Configure environment variables

Update the deployment `.env` file (or set variables in your container orchestrator):

```
YOUTUBE_OAUTH_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
YOUTUBE_OAUTH_CLIENT_SECRET=xxxxxxx
YOUTUBE_OAUTH_REDIRECT_URI=https://your-domain.example.com/api/destinations/youtube/oauth/callback
```

The legacy `YOUTUBE_API_KEY` can stay in place for backwards compatibility, but OAuth will be used for any destinations that complete the handshake.
If you still depend on the watchdog's API-key polling, toggle **Enable Watchdog Monitoring** inside the Streaming Destination dialog and paste the key into the **YouTube API Key** field that appears. Leaving the field blank disables API-key polling for that destination.

## 3. Run the database migration

After pulling the latest code, execute the new migration to add OAuth columns:

```
python backend/migrations/add_youtube_oauth_fields.py
```

This script is idempotent—if the columns already exist it will skip them safely.

## 4. Connect a destination

1. Open the **Streaming Destinations** page in the VistterStream UI.
2. For a YouTube destination, click **Connect OAuth** (or **Reconnect OAuth**) to start the flow.
3. Grant access in the Google window. After Google redirects back to the backend, the UI will poll the `/youtube/oauth-status` endpoint for up to a minute. Click **Refresh Status** if you want to update manually.
4. Once connected, the card shows a green “Connected” badge and the access token expiry time.
5. Use the **Disconnect** button to revoke stored tokens if you ever rotate credentials.

## 5. Trigger broadcast actions

With OAuth connected and the broadcast/stream IDs configured, you can now drive YouTube lifecycle changes directly from VistterStream:

* `GET /api/destinations/{id}/youtube/broadcast-status` – current broadcast lifecycle state.
* `GET /api/destinations/{id}/youtube/stream-health` – ingestion health and configuration issues.
* `POST /api/destinations/{id}/youtube/transition` – transition a broadcast to `testing`, `live`, or `complete`.
* `POST /api/destinations/{id}/youtube/reset` – cycle through complete → testing → live as a recovery measure.

These endpoints rely on the stored refresh token and will automatically refresh access tokens when they expire.

## 6. Operational tips

* Only the refresh token is persisted; access tokens are short-lived and refreshed automatically.
* If Google ever returns an `invalid_grant` error (usually after a password or 2FA reset), click **Reconnect OAuth** with `prompt_consent` (the UI enforces this) to obtain a fresh refresh token.
* Keep the redirect URI served over HTTPS. When testing locally, use an HTTPS tunnel (ngrok, Cloudflared) that forwards to your development server.
* Monitor the new OAuth-related logs in the backend service for early warnings about refresh failures.
