# VistterStream Remediation Plan

**Date:** March 10, 2026
**Based on:** Full architecture, QA, and legal review
**Current Grade:** B- (Architecture) / D (Security) / D (Test Coverage)
**Target Grade:** A- (Architecture) / B+ (Security) / B (Test Coverage)

---

## Phase 1: Critical Security (Do First)

These must be fixed before any public release or remote deployment.

### 1.1 — Fix Hardcoded JWT Secret
- **File:** `backend/routers/auth.py:25`
- **Issue:** `SECRET_KEY = "your-secret-key-here"` — anyone can forge auth tokens
- **Fix:** Read from `os.getenv("JWT_SECRET_KEY")`, fail startup if not set
- **Also:** Add `JWT_SECRET_KEY` to `env.sample` with generation instructions
- **Effort:** 30 minutes

### 1.2 — Remove .env from Git, Scrub History
- **Issue:** `.env` with real Cloudflare tunnel token is committed
- **Fix:**
  1. Add `.env`, `*.db`, `backend/backend.log`, `frontend/build/`, `.cursor/` to `.gitignore`
  2. `git rm --cached .env`
  3. Use `git filter-repo` to scrub `.env` from all history before any public push
  4. Revoke and regenerate the Cloudflare tunnel token
- **Effort:** 1 hour

### 1.3 — Add Authentication to All Endpoints
- **Issue:** Only `/auth/me` and `/auth/change-password` require auth. Everything else is wide open — including kill-all, delete cameras, change settings.
- **Fix:** Add `current_user: User = Depends(get_current_user)` as a router-level dependency on all routers except `/auth/login` and `/auth/register`
- **Effort:** 2 hours

### 1.4 — Replace Base64 with Real Encryption
- **Files:** `camera_service.py`, `reelforge.py`, `youtube_shorts_service.py`
- **Issue:** Base64 encoding is called "encryption" — it's trivially reversible
- **Fix:** Use `cryptography.fernet.Fernet` with key from env var `ENCRYPTION_KEY`
- **Migration:** Write a one-time script to re-encode existing base64 values
- **Effort:** 3 hours

### 1.5 — Mask Secrets in API Responses
- **Issue:** Stream keys and API keys returned in plaintext from `/api/destinations`
- **Fix:** Add `stream_key_masked` field (last 4 chars), remove full key from default response. Require re-auth for full key retrieval.
- **Effort:** 1 hour

### 1.6 — Remove/Protect Diagnostic Endpoint
- **File:** `backend/routers/auth.py:135-162`
- **Issue:** `/api/auth/diagnose` reveals user existence and password validity without auth
- **Fix:** Remove entirely, or gate behind admin auth
- **Effort:** 15 minutes

### 1.7 — Eliminate Default admin/admin Credentials
- **File:** `backend/start.py`
- **Issue:** Default password is "admin"
- **Fix:** Generate random password on first run, print to console. Or require interactive setup.
- **Effort:** 1 hour

### 1.8 — Redact Credentials from Logs
- **Files:** `camera_service.py:360-371`, `timeline_executor.py:631`
- **Issue:** RTSP URLs with passwords printed via `print()` and `logger.debug()`
- **Fix:** Replace all `print()` with `logger.debug()`. Create `redact_url()` utility that masks passwords.
- **Effort:** 2 hours

**Phase 1 Total: ~1-2 days**

---

## Phase 2: Critical Bugs (Do Second)

### 2.1 — Add Missing `import asyncio` in main.py
- **File:** `backend/main.py:173`
- **Issue:** `asyncio.create_task()` used without importing asyncio — ReelForge scheduler silently fails
- **Fix:** Add `import asyncio` to top of file
- **Effort:** 5 minutes

### 2.2 — Remove Duplicate Snapshot Route
- **File:** `backend/routers/cameras.py:108-175`
- **Issue:** `GET /{camera_id}/snapshot` defined twice. Second uses nonexistent `camera.ip_address` and `camera.password` fields.
- **Fix:** Delete the second duplicate definition entirely
- **Effort:** 15 minutes

### 2.3 — Add LICENSE File
- **Issue:** No license = all rights reserved. Blocks open-source distribution.
- **Fix:** Add MIT LICENSE file to repo root
- **Effort:** 10 minutes

**Phase 2 Total: ~30 minutes**

---

## Phase 3: Architecture Improvements (Do After Port to Beelink)

### 3.1 — Replace Synchronous requests with httpx.AsyncClient
- **File:** `backend/services/camera_service.py`
- **Issue:** Synchronous `requests.get()` in async context blocks the event loop
- **Fix:** Replace all `requests.*` calls with `httpx.AsyncClient` (already imported but unused)
- **Also:** Fix `psutil.cpu_percent(interval=1)` in `status.py` — use `asyncio.to_thread()` or `interval=0`
- **Effort:** 3 hours

### 3.2 — Add Database Migration Framework (Alembic)
- **Issue:** Manual `ALTER TABLE` in `start.py` grows linearly, no rollback, no history
- **Fix:** Initialize Alembic, create initial migration from current models, replace manual patches
- **Effort:** 4 hours

### 3.3 — Update Hardware Detection for Intel N95
- **File:** `backend/services/hardware_detector.py`
- **Issue:** Currently detects Pi 5 (V4L2) and Mac (VideoToolbox) but may not detect Intel QSV/VAAPI
- **Fix:** Add Intel Quick Sync detection (`h264_qsv` primary, `h264_vaapi` fallback), check for `/dev/dri/renderD128`
- **Effort:** 2 hours

### 3.4 — Modernize FastAPI Lifecycle
- **Issue:** Uses deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")`
- **Fix:** Migrate to `lifespan` context manager
- **Effort:** 1 hour

### 3.5 — Fix datetime.utcnow() Deprecation
- **Issue:** `datetime.utcnow()` deprecated in Python 3.12+
- **Fix:** Replace with `datetime.now(UTC)` throughout codebase
- **Effort:** 1 hour

### 3.6 — Fix Frontend Route Duplication
- **File:** `frontend/src/App.tsx`
- **Issue:** Same routes defined at two levels, ambiguous routing
- **Fix:** Restructure to single route definition with Layout wrapper
- **Effort:** 2 hours

**Phase 3 Total: ~2 days**

---

## Phase 4: Frontend Improvements

### 4.1 — Break Up Mega-Components
- **Files:** `TimelineEditor.tsx` (2,143 lines), `ReelForge.tsx` (2,006 lines)
- **Fix:** Extract logical sub-components (timeline cue editor, cue list, preview panel, etc.)
- **Effort:** 1 day per component

### 4.2 — Add Shared State Management
- **Issue:** Every component independently fetches cameras, destinations, etc. via useState + useEffect polling. No cache sharing.
- **Fix:** Add React Query (TanStack Query) for server state. Centralizes caching, deduplication, and background refetching.
- **Effort:** 1-2 days

### 4.3 — Fix Broken App.test.tsx
- **File:** `frontend/src/App.test.tsx`
- **Issue:** Default CRA scaffold test looking for "learn react" — will always fail
- **Fix:** Replace with meaningful smoke test (renders login page when unauthenticated)
- **Effort:** 30 minutes

**Phase 4 Total: ~3-4 days**

---

## Phase 5: Test Coverage

### 5.1 — Test Infrastructure
- Add shared `conftest.py` with in-memory SQLite fixture
- Add `pyproject.toml` with `asyncio_mode = "auto"`
- Fix existing test using on-disk SQLite (`test_stream_status_endpoint.py`)
- **Effort:** 2 hours

### 5.2 — Priority Test Suites

| Priority | Test File | Coverage Target |
|----------|-----------|-----------------|
| P0 | `test_auth.py` — verify_password, create_token, authenticate_user, get_current_user | Auth system |
| P0 | `test_auth_endpoints.py` — login, register, change-password, protected routes | API security |
| P1 | `test_stream_service.py` — start/stop stream, build RTSP URL, error paths | Core streaming |
| P1 | `test_camera_service_crud.py` — create/update/delete, normalize_snapshot_url | Camera management |
| P2 | `test_scheduler_logic.py` — is_schedule_active, overnight windows, day matching | Scheduler |
| P2 | `test_watchdog_health_state.py` — threshold, cooldown, recovery count | Health monitoring |
| P3 | Frontend component tests — AuthContext, ProtectedRoute, api interceptor | UI reliability |

### 5.3 — CI Pipeline
- Add GitHub Actions jobs for `pytest` (backend) and `npm test` (frontend)
- Block merge on test failure
- Add `pytest-cov` with 70% minimum on `services/` and `routers/`
- **Effort:** 2 hours

**Phase 5 Total: ~3-4 days**

---

## Summary Timeline

| Phase | Focus | Effort | When |
|-------|-------|--------|------|
| 1 | Critical Security | 1-2 days | Before any deployment |
| 2 | Critical Bugs | 30 min | Same session as Phase 1 |
| 3 | Architecture | 2 days | After Beelink port works |
| 4 | Frontend | 3-4 days | After architecture cleanup |
| 5 | Testing | 3-4 days | Ongoing, parallel with Phase 4 |

**Total estimated effort: ~2 weeks of focused work**

---

## Trademark & Legal (One-Time)

- [ ] Add MIT LICENSE file
- [ ] Add trademark disclaimer to README (YouTube, Facebook, Twitch)
- [ ] Add operator privacy guidance to docs
- [ ] Audit FFmpeg Docker build for GPL codec attribution
