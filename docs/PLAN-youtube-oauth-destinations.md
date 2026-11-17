# YouTube OAuth for Streaming Destinations

## Current State

The frontend UI for YouTube OAuth destinations is **already built** in `StreamingDestinations.tsx`:
- Platform type `youtube_oauth` is recognized
- OAuth Client ID, Secret, Redirect URI fields exist
- "Connect OAuth" button, status display, "Create Broadcast" button all wired up
- Calls backend endpoints that **don't exist yet**

The ReelForge module has a **working OAuth implementation** we can reuse:
- Token exchange, refresh, encryption — all in `youtube_shorts_service.py`
- OAuth flow endpoints in `reelforge.py` (lines 1354-1465)

**Gap:** 4 backend routes + OAuth fields on the Destination model.

---

## Phase 1: Database — Add OAuth Fields to Destination Model

**File:** `backend/models/destination.py`

Add to `StreamingDestination`:
```python
youtube_oauth_client_id = Column(String, nullable=True)
youtube_oauth_client_secret_enc = Column(String, nullable=True)  # encrypted
youtube_oauth_redirect_uri = Column(String, nullable=True)
youtube_oauth_refresh_token_enc = Column(String, nullable=True)  # encrypted
youtube_oauth_connected = Column(Boolean, default=False)
youtube_oauth_channel_name = Column(String, nullable=True)
youtube_oauth_token_expires_at = Column(DateTime, nullable=True)
```

**Migration:** Alembic or manual ALTER TABLE (SQLite).

---

## Phase 2: Backend — YouTube OAuth Destination Service

**File:** `backend/services/youtube_destination_service.py` (new, ~120 LOC)

Reuse patterns from `youtube_shorts_service.py`:
- `get_oauth_url(client_id, client_secret, redirect_uri)` → authorization URL
- `exchange_code(code, client_id, client_secret, redirect_uri)` → refresh token + channel info
- `get_credentials(destination)` → `google.oauth2.credentials.Credentials`
- `create_broadcast(destination, title)` → creates broadcast + stream, binds them, returns broadcast_id + stream_key + RTMP URL
- `get_broadcast_status(destination)` → checks broadcast lifecycle state

**Scopes:** `youtube`, `youtube.upload`, `youtube.readonly`

---

## Phase 3: Backend — 4 API Routes

**File:** `backend/routers/destinations.py` (add ~100 LOC)

| Endpoint | Purpose |
|----------|---------|
| `POST /destinations/{id}/youtube/oauth-start` | Save client_id/secret, return auth URL |
| `GET /destinations/youtube/oauth-callback` | Exchange code, store refresh token, update destination |
| `GET /destinations/{id}/youtube/oauth-status` | Return connected, channel_name, token_expires_at |
| `DELETE /destinations/{id}/youtube/oauth` | Clear tokens, set connected=false |
| `POST /destinations/{id}/youtube/create-broadcast` | Create broadcast via API, store broadcast_id + stream_key on destination, return RTMP URL |

The `create-broadcast` endpoint is the key one — it:
1. Creates a YouTube broadcast (title = destination name, privacy = unlisted/public)
2. Creates a YouTube live stream (bound to broadcast)
3. Extracts RTMP URL + stream key from the stream resource
4. Stores `youtube_broadcast_id`, `youtube_stream_id`, `rtmp_url`, `stream_key` on the destination
5. Returns the broadcast ID so the frontend can embed the player

---

## Phase 4: Frontend — Minor Wiring

The frontend is mostly done. Small changes needed:

1. **Save OAuth credentials** — `POST /destinations/{id}` already saves all fields; just need to include `youtube_oauth_client_id`, `youtube_oauth_client_secret`, `youtube_oauth_redirect_uri` in the update payload
2. **OAuth callback handler** — The popup window needs to POST to the callback URL and relay the result via `postMessage`
3. **Auto-populate RTMP** — After "Create Broadcast", auto-fill the RTMP URL and stream key fields

---

## Phase 5: Timeline Editor — Live Preview with Broadcast ID

Once OAuth creates a broadcast, `youtube_broadcast_id` is populated on the destination. The existing code in `TimelineEditor.tsx` (lines 1704-1722) already renders the YouTube embed when `isRunning && hasYoutubeDestination && youtubeVideoId`. This will work automatically.

---

## Effort Estimate

| Phase | Files | LOC |
|-------|-------|-----|
| 1 — DB model | 1 | ~10 |
| 2 — Service | 1 (new) | ~120 |
| 3 — Routes | 1 | ~100 |
| 4 — Frontend | 1 | ~30 |
| **Total** | **4** | **~260** |

## Reference Files

- `backend/services/youtube_shorts_service.py` — OAuth patterns to reuse
- `backend/routers/reelforge.py:1354-1465` — Working OAuth flow example
- `frontend/src/components/StreamingDestinations.tsx:471-538` — Frontend OAuth handlers
- `backend/models/destination.py` — Current model
