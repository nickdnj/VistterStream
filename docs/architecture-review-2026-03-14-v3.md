# VistterStream Architecture & Security Review v3
**Date:** 2026-03-14 | **Reviewer:** Claude Code Deep Audit v3
**Scope:** Full codebase read of backend (15,927 LOC), frontend (React/TypeScript), Docker, CI, tests

---

## 1. Executive Summary

VistterStream has matured significantly since the v1 review. Two prior security passes (v1, v2) drove major improvements: CORS was tightened, preview endpoints gained authentication, Fernet encryption replaced plaintext secrets, HMAC-signed OAuth state tokens were added, a multi-stage Dockerfile with non-root user was introduced, structured JSON logging with secret redaction was implemented, audit logging middleware was added, and rate limiting was applied. This v3 review finds the critical security posture substantially improved but identifies several remaining issues, including one critical finding and a number of high-severity items.

### Scorecard

| Category | Grade | Trend | Notes |
|----------|-------|-------|-------|
| **Architecture** | **B** | Up from C+ | Clean modular design, Alembic added, lifecycle management improved |
| **Security** | **C+** | Up from D+ | Major hardening done, but secrets in git history, CSRF gaps, and missing HSTS remain |
| **Code Quality** | **B** | Stable | Consistent patterns, Pydantic validation, some legacy debug code |
| **Testing** | **C+** | Up from C | ~1,766 LOC of tests across 14 files, but critical paths still untested |
| **Deployment** | **B+** | Up from B | Multi-stage Docker, non-root user, healthcheck, VA-API GPU support |
| **Overall** | **B-** | Up from C+ | Solid appliance software with remaining security debt |

---

## 2. Architecture Analysis

### 2.1 Directory Structure and Organization — Grade: B+

The project follows a clean layered architecture:

```
backend/
  routers/       (15 router files — HTTP layer)
  services/      (18 service files — business logic)
  models/        (7 model files — ORM + Pydantic schemas)
  utils/         (5 utility modules)
  middleware/    (audit logging)
  migrations/   (legacy + Alembic)
  tests/        (9 test files)
```

**Strengths:**
- Clear separation of concerns: routers delegate to services, services use models
- Each domain (cameras, streams, timelines, destinations, reelforge) has its own router, model, and service layer
- Utilities are isolated and focused (crypto, logging, Google Drive URL parsing)

**Weaknesses:**
- `models/schemas.py` is a 647-line monolith containing Pydantic schemas for every domain. Should be split per domain (e.g., `schemas/camera.py`, `schemas/reelforge.py`)
- `models/database.py` imports all model modules at the bottom to register with SQLAlchemy — a circular dependency managed by placement rather than by design
- The `delete/` directory exists at the project root (appears to be discarded code)

### 2.2 Code Quality — Grade: B

**Strengths:**
- Consistent naming conventions (snake_case for Python, camelCase for TypeScript)
- Good docstrings on most service methods and router endpoints
- Pydantic Field validators with ranges (ge, le, min_length, max_length) on schemas
- Type hints on function signatures
- `from_attributes = True` config on Pydantic models for ORM compatibility

**Weaknesses:**
- **Debug logging left in production code.** `ffmpeg_manager.py` and `timeline_executor.py` both contain `_dbg_ffmpeg()` / `_dbg()` helper functions that write raw JSON to `/data/debug.log` with bare `except: pass`. This bypasses the structured logging system and creates unmanaged files on the persistent volume.
- **Mixed print() and logger calls.** `start.py:85` uses `print(f"...")` for an error, `settings.py:110` uses `print(f"...")` for success. These bypass structured logging.
- **Emoji in log messages.** While less of an issue with JSON logging, several services use emoji in log messages (e.g., `logger.warning("...")`). These render poorly in log aggregation tools.
- **f-string logging.** `routers/auth.py` uses f-string formatting in logger calls (e.g., `logger.info(f"Login attempt for username: '{form_data.username}'")`). This constructs the string even if the log level is disabled. Should use `%s` formatting: `logger.info("Login attempt for username: '%s'", form_data.username)`.
- **Deprecated Pydantic methods.** `camera_service.py:139` and `stream_service.py:68` use `.dict()` (Pydantic v1 API) instead of `.model_dump()` (Pydantic v2 API).

### 2.3 Database Design — Grade: B

**Strengths:**
- SQLAlchemy ORM with proper relationships (one-to-many, cascading deletes)
- Alembic migration framework now integrated (replacing 11+ ad-hoc migration functions)
- Legacy `ensure_*` functions kept as no-ops for backward compatibility
- Context manager (`get_session()`) for background services
- Pool exhaustion monitoring via `@event.listens_for(engine, "checkout")`

**Weaknesses:**
- **SQLite in production.** While appropriate for a single-user appliance, SQLite has limitations: no concurrent write transactions (affects background services writing simultaneously), no built-in encryption at rest, no auth. The pool configuration code handles this with `check_same_thread=False`, but concurrent write contention from background services (health monitor, watchdog, scheduler, reelforge capture) can cause `database is locked` errors.
- **No database indices beyond primary keys.** Tables like `audit_log` have indices on `timestamp`, `user_id`, and `action`, which is good. But `timeline_cues` has no index on `track_id` (queried by FK), and `reel_posts` has no index on `status` (queried for pending items).
- **JSON columns for structured data.** `Schedule.days_of_week`, `Schedule.destination_ids`, `TimelineCue.action_params`, `ReelTemplate.ai_config`, and others use JSON columns. This works for SQLite but prevents querying or indexing individual fields.

### 2.4 API Design — Grade: B

**Strengths:**
- RESTful resource naming (`/api/cameras`, `/api/timelines`, `/api/destinations`)
- Proper HTTP methods (GET, POST, PUT, DELETE)
- Consistent error responses with HTTPException
- Rate limiting on auth endpoints (5/5min for login, 3/5min for register)
- API docs conditionally disabled in production (`ENABLE_DOCS` env var)
- `redirect_slashes=False` to prevent 307 redirects behind reverse proxy

**Weaknesses:**
- **No API versioning.** All routes are under `/api/` without a version prefix. Adding `/api/v1/` would allow non-breaking evolution.
- **Inconsistent response formats.** Some endpoints return `{"message": "..."}`, others return resource objects, and `create_stream` returns an enriched dict. No standard envelope.
- **Internal exceptions leak in error responses.** `streams.py:113` raises `HTTPException(status_code=500, detail=str(e))` which exposes Python exception messages to the client. Similarly `timelines.py:192`, `timelines.py:277`, `assets.py:239`, `destinations.py:439`. These should return generic error messages.
- **No pagination on list endpoints.** `get_timelines()`, `get_streams()`, `get_destinations()` return all records. `get_assets()` has `skip`/`limit` parameters, which is good. Other list endpoints should follow suit.
- **POST used for settings update.** `settings.py:60` uses `POST` for updating settings. Should be `PUT` or `PATCH`.

### 2.5 Service Layer — Grade: B-

**Strengths:**
- `FFmpegProcessManager` has `asyncio.Lock` protecting the processes dictionary
- Stream lifecycle management with graceful shutdown (SIGTERM then SIGKILL)
- Auto-restart with exponential backoff (2s to 60s, max 10 retries)
- Hardware detection for encoder selection (VA-API, VideoToolbox, QSV, libx264)
- `ReelForgeProcessor` uses processing lock to prevent duplicate processing

**Weaknesses:**
- **Multiple state dictionaries without unified lifecycle management.** `TimelineExecutor` maintains 6 separate dictionaries: `active_timelines`, `ffmpeg_managers`, `playback_positions`, `_position_update_tasks`, `timeline_destinations`, `timeline_destination_ids`, `_last_segment_time`. These must all be kept in sync manually.
- **Singleton pattern via module-level functions.** `get_timeline_executor()`, `get_ptz_service()`, `get_watchdog_manager()`, etc. use module-level singletons. This makes testing harder and creates implicit global state.
- **Background task results not monitored.** In `main.py:88`, `asyncio.create_task(reelforge_scheduler.start())` is fire-and-forget. If the task crashes, nothing detects or restarts it.
- **Database session management in background services.** `timeline_executor.py:191` creates `db = SessionLocal()` at the start of `_execute_timeline()` and holds it open for the entire timeline execution (potentially hours). This ties up a connection for the duration.

### 2.6 Frontend Architecture — Grade: B

**Strengths:**
- React 19 with TypeScript, functional components, hooks
- AuthContext for centralized authentication state
- ProtectedRoute component for route guarding
- Axios interceptors for automatic token injection and 401 handling
- Dynamic API base URL resolution (handles Cloudflare Tunnel HTTPS automatically)
- Tailwind CSS for consistent styling

**Weaknesses:**
- **Token stored in localStorage.** `localStorage.getItem('token')` is accessible to any JavaScript on the page. An XSS vulnerability would allow token theft. HttpOnly cookies would be more secure, though this is a common tradeoff for SPAs.
- **No token refresh.** 30-minute JWT with no refresh mechanism means the user is logged out every 30 minutes. The 401 interceptor redirects to login, which is abrupt.
- **Debug console.log statements in production.** `Login.tsx:22` logs `{ username, password }` to the console. `authService.ts:17` logs "Starting login for username" and line 29 logs the full response.
- **Single test file.** `App.test.tsx` exists but appears to be the default CRA test. No component tests, no integration tests.

### 2.7 Docker/Deployment — Grade: B+

**Strengths:**
- **Multi-stage build.** Builder stage installs `build-essential`, runtime stage only has runtime libs. Build tools are not in the production image (fixing a v1 finding).
- **Non-root user.** `appuser` (UID 1000) created with `render` group (GID 993) for VA-API GPU access.
- **Entrypoint drops privileges.** `entrypoint.sh` starts as root to fix `/data` ownership, then uses `gosu` to drop to `appuser`.
- **Healthcheck.** `HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1`
- **Compose uses `env_file`** with required variable syntax `${JWT_SECRET_KEY:?...}`.
- **GPU passthrough.** `/dev/dri` device mapping with render group for Intel VA-API hardware encoding.
- **Uvicorn hardening.** `timeout_keep_alive=5` (Slowloris mitigation), `limit_max_requests=10000` (leak prevention).

**Weaknesses:**
- **No resource limits.** Docker Compose does not set `mem_limit`, `cpus`, or `pids_limit`. On a mini PC with limited resources, a runaway FFmpeg process could exhaust the system.
- **RTMP relay port exposed to host.** `ports: "1935:1935"` on the RTMP relay container exposes it to the local network. Should only be mapped if external cameras need to push to it (currently cameras use RTSP pull, not RTMP push).
- **No Docker Secrets.** Secrets are passed via environment variables, which are visible via `docker inspect`. Docker Secrets would keep them out of the container metadata.

### 2.8 Test Coverage — Grade: C+

**Current state:** 14 test files, ~1,766 lines of test code

| Test File | Coverage Area | Tests |
|-----------|--------------|-------|
| `test_auth.py` | Login, register, token validation | 4 |
| `test_cameras.py` | Camera CRUD | ~2 |
| `test_streams.py` | Stream CRUD | ~6 |
| `test_timelines.py` | Timeline CRUD | ~8 |
| `test_destinations.py` | Destination CRUD + watchdog config | ~8 |
| `test_assets.py` | Asset CRUD + upload + proxy | ~8 |
| `test_oauth_state.py` | HMAC state token generation/verification | 7 |
| `test_audit.py` | Audit middleware | ~3 |
| `test_logging.py` | Secret redaction in logs | ~4 |
| `test_ffmpeg_manager.py` | FFmpeg command building, lifecycle | ~12 |
| `test_camera_service_status.py` | Camera status probing | ~4 |
| `test_ptz_service_overrides.py` | PTZ service env overrides | ~6 |
| `test_stream_status_endpoint.py` | Stream status API | ~5 |

**Strengths:**
- Good test infrastructure: in-memory SQLite, dependency overrides, disabled rate limiting, no-op lifespan
- OAuth state token tests are thorough (tampered, wrong sig, plain int, empty, uniqueness)
- Logging redaction tests verify sensitive data is masked

**Gaps:**
- No tests for ReelForge endpoints (entire feature untested)
- No tests for scheduler service
- No tests for timeline execution (the core feature)
- No tests for OAuth flow (exchange_code, callback handling)
- No tests for SSRF URL validation in assets
- No integration tests (stream start-to-stop lifecycle)
- No frontend tests beyond the CRA boilerplate
- No concurrent access tests

---

## 3. Security Analysis

### CRITICAL

#### S1. Secrets Remain in Git History
**Severity:** CRITICAL | **Status:** Partially remediated

`.env` is now in `.gitignore` (good), but it was committed in at least 3 prior commits. The file contains live production secrets:
- `JWT_SECRET_KEY=18fa6f1d55c86fe2d022f5eeac54d7f4c083b32997c6b588f75d9dfeb8b6b6c7`
- `ENCRYPTION_KEY=f-umbBdvlhgOa5YT0CE1PpwUM9IKSJYuiXLedQl7BFw=`
- `CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiMmY1OTdiYWFj...`

Anyone with repo read access (including GitHub if the repo is public, or any collaborator) can extract these from git history.

**Impact:** An attacker with these keys can forge JWT tokens (full admin access), decrypt all stored secrets (stream keys, OAuth tokens, camera passwords), and access the Cloudflare tunnel.

**Fix:**
1. Rotate ALL secrets immediately: generate new JWT_SECRET_KEY, ENCRYPTION_KEY, and Cloudflare tunnel token
2. Re-encrypt all database secrets with the new ENCRYPTION_KEY (the `ensure_destination_secrets_encrypted()` migration handles this on restart)
3. Scrub git history with `git filter-repo` or BFG Repo Cleaner
4. Verify `.env` is in `.gitignore` (confirmed: it is)

### HIGH

#### S2. No CSRF Protection on State-Changing Endpoints
**Severity:** HIGH

The application uses JWT Bearer tokens for authentication, which are not automatically sent by browsers (unlike cookies). This provides some CSRF protection inherently. However:
- CORS allows credentials (`allow_credentials=True`) with a regex that matches any local IP
- The `SameSite` attribute is not set on any cookies
- There is no CSRF token mechanism

The risk is reduced because tokens are in localStorage (not cookies), but if any XSS vulnerability exists, the token can be stolen and replayed.

**Fix:** Consider adding SameSite=Strict if cookies are ever used. The current Bearer token approach provides adequate CSRF protection if XSS is prevented.

#### S3. XSS Risk in OAuth Callback HTML (Partially Fixed)
**Severity:** MEDIUM (downgraded from HIGH in v2)

The v2 review flagged unescaped channel names in OAuth callback HTML. This has been fixed: `destinations.py:510` now uses `html_escape(channel_name)` and `html_escape(message)`.

However, the `postMessage` in the callback uses `'*'` as the target origin:
```javascript
window.opener.postMessage('youtube-connected', '*');
```
This should be restricted to the known origin (e.g., `https://stream.vistter.com` or the app's origin) to prevent message interception by malicious pages.

#### S4. OAuth State Token Not Time-Limited
**Severity:** HIGH

The HMAC-signed OAuth state (`_generate_oauth_state()`) includes a destination ID and nonce but no timestamp. A captured state token remains valid forever.

**Location:** `backend/routers/destinations.py:200-222`

**Fix:** Add a timestamp to the payload: `payload = f"{destination_id}:{nonce}:{int(time.time())}"` and reject states older than 10 minutes in `_verify_oauth_state()`.

#### S5. Registration Endpoint Open
**Severity:** HIGH

`/api/auth/register` is rate-limited (3/5min) but has no access control. Any unauthenticated user can create accounts. For a single-user appliance, registration should be disabled or require admin authentication.

**Location:** `backend/routers/auth.py:99-122`

**Fix:** Either remove the register endpoint entirely (admin is created by `ensure_default_admin()`), or require the current admin user to be authenticated to create new users.

#### S6. Weak Rate Limiting Configuration
**Severity:** MEDIUM (downgraded from HIGH)

Login rate limiting is now 5/5min (improved from 10/15min in v1). Registration is 3/5min. However:
- No rate limiting on other sensitive endpoints (password change, destination create/delete, emergency kill-all)
- No account lockout mechanism after repeated failures
- The rate limiter key is `get_remote_address`, which behind Cloudflare Tunnel may always be the tunnel IP unless `X-Forwarded-For` is configured

**Fix:** Add `app.add_middleware(TrustedHostMiddleware)` and configure SlowAPI to use `X-Forwarded-For` behind reverse proxies.

#### S7. No HSTS Header
**Severity:** MEDIUM

The `SecurityHeadersMiddleware` adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `X-XSS-Protection`. Missing:
- `Strict-Transport-Security` (HSTS) — important when served via Cloudflare Tunnel over HTTPS
- `Content-Security-Policy` — would prevent XSS by restricting script sources

**Location:** `backend/main.py:192-199`

**Fix:** Add HSTS and a basic CSP:
```python
if request.url.scheme == "https":
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
```

#### S8. Debug Log File with No Rotation or Access Control
**Severity:** MEDIUM

`ffmpeg_manager.py:31` and `timeline_executor.py:34` write to `/data/debug.log` with bare `except: pass`. This file:
- Grows unbounded (no rotation)
- May contain sensitive FFmpeg command arguments (including stream keys in RTMP URLs)
- Is on the persistent `/data` volume
- Bypasses the structured logging system and its redaction filters

**Fix:** Remove the `_dbg_ffmpeg()` and `_dbg()` functions. Use the standard logger with DEBUG level instead. If a separate debug file is needed, use Python's `RotatingFileHandler`.

### MEDIUM

#### S9. Exception Messages Exposed in API Responses
**Severity:** MEDIUM

Multiple endpoints expose raw Python exception messages to clients:
- `streams.py:113`: `detail=str(e)` on stream creation failure
- `timelines.py:192`: `detail=f"Failed to create timeline: {str(e)}"`
- `timelines.py:277`: `detail=f"Failed to update timeline: {str(e)}"`
- `timelines.py:396`: `detail=f"Failed to cleanup orphaned cues: {str(e)}"`
- `assets.py:239`: `detail=f"Upload failed: {str(e)}"`
- `assets.py:305`: `detail=f"Failed to fetch asset: {e}"`
- `destinations.py:439`: `detail=f"Failed to create broadcast: {e}"`
- `timeline_execution.py:105`: `detail=f"Failed to create YouTube broadcast for {dest.name}: {e}"`

These can reveal internal implementation details, database structure, file paths, and third-party API error messages.

**Fix:** Log the full exception with `logger.error()` and return generic messages like `detail="Internal server error"` or domain-specific messages like `detail="Failed to create stream"`.

#### S10. CORS Origin Regex Too Broad
**Severity:** MEDIUM

The default CORS regex allows any HTTP origin with an IP address:
```python
r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\d{1,3}(?:\.\d{1,3}){3}|...)"
```

The `\d{1,3}(?:\.\d{1,3}){3}` pattern matches ANY IPv4 address, not just private networks. This means `http://1.2.3.4:3000` (a public IP) would be allowed.

**Fix:** Restrict to RFC 1918 ranges: `(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})`

#### S11. Unvalidated `api_url` on Asset Creation
**Severity:** MEDIUM

While the proxy endpoint (`/api/assets/{id}/proxy`) and the test endpoint (`/api/assets/{id}/test`) both call `_validate_url()` to block SSRF, the `create_asset()` and `update_asset()` endpoints accept `api_url` without validation. The URL is only validated when it is fetched.

This means a user could store an internal URL like `http://169.254.169.254/latest/meta-data/` as an asset, and it would only fail at render time. However, since the SSRF validation happens before any fetch, the actual risk is limited to storing the URL (no data exfiltration occurs at creation time).

**Fix:** Validate `api_url` in `create_asset()` and `update_asset()` as well, to fail fast with a clear error.

#### S12. Plaintext Console Logging of Credentials
**Severity:** MEDIUM

`Login.tsx:22` logs `{ username, password }` to the browser console:
```javascript
console.log('Login form submitted with:', { username, password });
```

`authService.ts:17` logs the username and response data. While browser console logs are only visible to the user, this is still a bad practice — shoulder surfing, browser extensions, or dev tools left open on shared machines could expose credentials.

**Fix:** Remove all `console.log` statements containing credentials. Use `console.log('Login attempt...')` without the payload.

#### S13. No Password Complexity Enforcement
**Severity:** MEDIUM

`UserCreate` requires `min_length=6` for passwords. There is no requirement for uppercase, lowercase, digits, or special characters. `PasswordChangeRequest` requires `min_length=6` for `new_password` but only `min_length=1` for `current_password`.

**Fix:** Increase minimum to 8 characters and consider requiring at least one digit and one letter.

#### S14. Audit Log Not Capturing User Identity Reliably
**Severity:** LOW

The `AuditMiddleware` tries to extract user identity from `request.state.user`, but FastAPI's `Depends(get_current_user)` sets the user as a function return value, not on `request.state`. This means `user_id` and `username` are likely always `None` in audit records.

**Location:** `backend/middleware/audit.py:57-63`

**Fix:** Either set `request.state.user` in the `get_current_user` dependency, or extract the user from the JWT token directly in the middleware.

### LOW

#### S15. `python-jose` Library Unmaintained
The JWT library `python-jose` has known CVEs and is no longer actively maintained. The recommended replacement is `PyJWT` or `python-jose[cryptography]` (which is used here, mitigating some issues).

#### S16. SQLite Database Not Encrypted at Rest
The database file on the Docker volume is unencrypted. Physical access to the host or volume gives full access to all data including encrypted secrets (and the ENCRYPTION_KEY in the `.env` history would decrypt them).

#### S17. `slowapi` Version Not Pinned Exactly
`requirements.txt` has `slowapi>=0.1.9` and `alembic>=1.13.0` — these should use exact pinning (`==`) like the other dependencies to prevent supply chain surprises.

#### S18. No Content-Length Limit on API Requests
The API does not set a maximum request body size (except for file uploads which check 50MB). A large JSON payload to a CRUD endpoint could consume memory.

---

## 4. Positive Findings — What's Done Well

These represent genuine improvements since v1/v2 and strong engineering decisions:

1. **Fernet encryption for secrets at rest.** Camera passwords, stream keys, YouTube API keys, OAuth client secrets, and refresh tokens are all encrypted with `cryptography.fernet` before storage. The fallback-to-base64 decode (flagged in v2) has been removed. The `decrypt()` function now raises `ValueError` on invalid tokens.

2. **HMAC-signed OAuth state tokens.** CSRF protection for the OAuth flow uses `hmac.new()` with SHA-256 and `hmac.compare_digest()` for timing-safe comparison. Each state includes a UUID nonce for uniqueness. Comprehensive test coverage with 7 test cases.

3. **Structured JSON logging with secret redaction.** The `SecretRedactionFilter` masks RTSP credentials, API keys, Bearer tokens, and Fernet tokens in log output. Five regex patterns cover common sensitive data formats. JSON formatter produces machine-parseable log lines.

4. **Multi-stage Docker build with non-root execution.** Builder stage compiles C extensions, runtime stage runs as `appuser:1000`. The `entrypoint.sh` uses `gosu` to fix volume permissions before dropping privileges. Healthcheck endpoint ensures container orchestration works.

5. **CORS properly configured.** Origins are now explicit (not `*`), methods are whitelisted (`GET, POST, PUT, DELETE, OPTIONS`), and headers are restricted to `Content-Type` and `Authorization`. The regex allows local network IPs for development while the explicit list includes the Cloudflare tunnel domain.

6. **Preview endpoints now require authentication.** All preview router endpoints use `dependencies=[Depends(get_current_user)]`.

7. **API docs disabled in production.** Controlled by `ENABLE_DOCS` environment variable, defaulting to disabled.

8. **Secrets masked in API responses.** `_dest_to_response()` replaces stream keys and API keys with `"........"` before returning destination data. Encrypted fields are stripped from responses.

9. **RTMP relay access restricted.** nginx-rtmp config now uses `allow publish 172.16.0.0/12; allow publish 127.0.0.1; deny publish all;` instead of the previous `allow publish all`.

10. **Mandatory environment variables.** `JWT_SECRET_KEY` and `ENCRYPTION_KEY` raise `RuntimeError` at import time if not set, preventing the app from starting with insecure defaults. Docker Compose uses `${VAR:?error message}` syntax.

11. **Secure admin password generation.** `ensure_default_admin()` generates a random `secrets.token_urlsafe(16)` password if no env var is set and no admin exists. The old hardcoded `admin/admin` reset script pattern has been replaced.

12. **SSRF protection on asset URLs.** The `_validate_url()` function blocks loopback, link-local, 10.x.x.x, and `host.docker.internal`, while allowing 192.168.x.x for local services like TempestWeather.

13. **File upload validation.** Content-type whitelist, 50MB size limit with streaming check, UUID-based filenames to prevent path traversal.

14. **Pydantic input validation.** RTMP URLs validated for `rtmp://` or `rtmps://` prefix. YouTube watch URLs validated for `https://www.youtube.com/` prefix. Camera names, presets, and assets all have field constraints.

15. **Uvicorn hardening.** `timeout_keep_alive=5` mitigates Slowloris attacks. `limit_max_requests=10000` prevents slow memory leaks from accumulating.

---

## 5. Detailed Architecture Notes

### 5.1 FFmpeg Command Building Security

The FFmpeg command in `_build_ffmpeg_command()` uses list-based `create_subprocess_exec()` (not shell expansion), which prevents shell injection. Input URLs come from the database (camera RTSP URLs and destination RTMP URLs), not directly from user input. Overlay file paths come from the uploads directory.

However, the `input_url` parameter contains camera credentials embedded in the RTSP URL (e.g., `rtsp://user:pass@host/path`). While the URL is URL-encoded (via `quote()`), the credentials are visible in:
- FFmpeg process arguments (visible via `ps aux` or `/proc/{pid}/cmdline`)
- The `StreamProcess.command` list stored in memory
- FFmpeg stderr output (parsed by `_monitor_process`)

The `SecretRedactionFilter` in the logging system handles log output redaction, and `redact_url()` is used when logging URLs explicitly. Process argument visibility is an inherent limitation of FFmpeg.

### 5.2 Background Service Lifecycle

The lifespan manager (`main.py:48-125`) starts 5 background services:
1. Camera health monitor
2. RTMP relay service
3. Scheduler service
4. YouTube watchdog manager
5. ReelForge capture scheduler

Each has a try/except that logs warnings but continues if a service fails to start. Shutdown is handled in reverse. The ReelForge scheduler uses `asyncio.create_task()` without storing or monitoring the task reference — if it crashes silently, no recovery occurs.

### 5.3 Database Session Lifecycle in Background Tasks

The `main.py:69` lifespan creates `db = next(get_db())` for the watchdog manager startup. This is a generator-based session that is never properly closed in this context. The `get_db()` generator expects to be used as a FastAPI dependency (which calls `next()` and then `close()` on request completion), not consumed directly.

Similarly, `timeline_executor.py:191` creates `db = SessionLocal()` at the start of `_execute_timeline()` and holds it for the entire execution (potentially hours of continuous streaming).

### 5.4 State Consistency

The timeline executor maintains parallel state in:
- `self.active_timelines` (dict of asyncio Tasks)
- `self.ffmpeg_managers` (dict of FFmpegProcessManager instances)
- `self.timeline_destinations` (dict of destination name lists)
- `self.timeline_destination_ids` (dict of destination ID lists)
- `self.playback_positions` (dict of position info)
- `self._last_segment_time` (dict of timestamps)

If any cleanup path misses one of these dictionaries, state becomes inconsistent. The `stop_timeline()` method cleans up most of these, but edge cases (like a crash during startup) could leave orphaned entries.

---

## 6. Prioritized Action Items

### Phase 1: Critical — Do Immediately

| # | Action | Severity | Effort |
|---|--------|----------|--------|
| 1 | **Rotate ALL secrets** (JWT_SECRET_KEY, ENCRYPTION_KEY, Cloudflare tunnel token) and update production `.env` | CRITICAL | 30 min |
| 2 | **Scrub `.env` from git history** with `git filter-repo --path .env --invert-paths` or BFG | CRITICAL | 15 min |
| 3 | **Disable or protect `/api/auth/register`** — require admin auth or remove entirely | HIGH | 15 min |
| 4 | **Remove debug log functions** (`_dbg_ffmpeg`, `_dbg`) from `ffmpeg_manager.py` and `timeline_executor.py` | MEDIUM | 10 min |
| 5 | **Remove `console.log` with credentials** from `Login.tsx:22` and `authService.ts` | MEDIUM | 5 min |

### Phase 2: High Priority — This Week

| # | Action | Severity | Effort |
|---|--------|----------|--------|
| 6 | Add timestamp expiry to OAuth state tokens (10-minute window) | HIGH | 30 min |
| 7 | Replace generic exception messages in HTTP 500 responses with safe messages | MEDIUM | 1 hr |
| 8 | Add HSTS header for HTTPS connections | MEDIUM | 10 min |
| 9 | Restrict `postMessage` target origin in OAuth callback HTML | MEDIUM | 5 min |
| 10 | Add SSRF validation to `create_asset()` and `update_asset()` | MEDIUM | 15 min |
| 11 | Tighten CORS regex to RFC 1918 ranges only | MEDIUM | 15 min |
| 12 | Fix audit middleware to capture user identity from JWT | LOW | 30 min |
| 13 | Pin `slowapi` and `alembic` to exact versions | LOW | 5 min |

### Phase 3: Quality — Next Sprint

| # | Action | Severity | Effort |
|---|--------|----------|--------|
| 14 | Add refresh token mechanism (extends session without re-login) | HIGH | 4 hr |
| 15 | Replace f-string logging with `%s` formatting in `auth.py` | LOW | 15 min |
| 16 | Replace `.dict()` with `.model_dump()` in camera and stream services | LOW | 10 min |
| 17 | Remove `print()` calls from `start.py:85` and `settings.py:110` | LOW | 5 min |
| 18 | Split `models/schemas.py` into domain-specific schema files | LOW | 2 hr |
| 19 | Add pagination to timelines, streams, and destinations list endpoints | LOW | 1 hr |
| 20 | Add Docker Compose resource limits (mem_limit, cpus) | LOW | 15 min |

### Phase 4: Testing — Ongoing

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 21 | Add SSRF validation tests for `_validate_url()` | HIGH | 1 hr |
| 22 | Add timeline execution integration tests | HIGH | 4 hr |
| 23 | Add ReelForge endpoint tests | MEDIUM | 2 hr |
| 24 | Add OAuth callback flow tests (mock Google API) | MEDIUM | 2 hr |
| 25 | Add concurrent access tests for FFmpeg manager | MEDIUM | 2 hr |
| 26 | Add frontend component tests for Login, Dashboard | LOW | 4 hr |
| 27 | Set up `pip-audit` in CI for dependency vulnerability scanning | LOW | 30 min |

---

## 7. Changes Since v1/v2 Reviews — Remediation Tracker

| v1/v2 Finding | Status | Notes |
|---------------|--------|-------|
| Preview endpoints unprotected | **FIXED** | `dependencies=[Depends(get_current_user)]` added |
| CORS allows CSRF | **FIXED** | Methods/headers whitelisted, origins restricted |
| Stream keys stored in plaintext | **FIXED** | Fernet encryption, masked in API responses |
| YouTube API key unencrypted | **FIXED** | Fernet encryption applied |
| Default admin reset script | **FIXED** | Random password generated, env var override |
| .env in git | **PARTIALLY FIXED** | `.gitignore` added, but history not scrubbed |
| No rate limiting on login | **FIXED** | 5/5min via SlowAPI |
| OAuth state predictable | **FIXED** | HMAC-SHA256 with nonce |
| RTMP relay allows all | **FIXED** | Restricted to Docker bridge + localhost |
| API docs publicly accessible | **FIXED** | Disabled by default (ENABLE_DOCS) |
| Docker runs as root | **FIXED** | Non-root appuser with entrypoint |
| No audit logging | **FIXED** | AuditMiddleware for POST/PUT/DELETE |
| No request timeout | **FIXED** | `timeout_keep_alive=5`, `limit_max_requests=10000` |
| Build tools in production image | **FIXED** | Multi-stage build |
| No structured logging | **FIXED** | JSON formatter with secret redaction |
| XSS in OAuth callback HTML | **FIXED** | `html_escape()` applied |
| Encryption key fallback to base64 | **FIXED** | Fallback removed, raises ValueError |
| No security headers | **FIXED** | X-Content-Type-Options, X-Frame-Options, Referrer-Policy |
| Dependency versions not pinned | **FIXED** | All deps pinned with `==` (except slowapi, alembic) |
| No database migration framework | **FIXED** | Alembic integrated |
| SSRF via asset API URLs | **FIXED** | `_validate_url()` with SSRF blocklist |
| SQL injection risk in start.py | **LOW RISK** | Legacy migrations are no-ops after Alembic; column names are hardcoded, not user input |

---

*Review generated by Claude Code Deep Audit v3. Based on full read of 15,927 lines of backend code, 14 test files (1,766 LOC), frontend React/TypeScript source, Docker configuration, and CI pipeline.*
