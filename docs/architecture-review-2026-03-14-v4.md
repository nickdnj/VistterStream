# VistterStream Architecture & Security Review v4
**Date:** 2026-03-14 | **Reviewer:** Claude Code Deep Audit v4 (Opus 4.6)
**Scope:** Full codebase read of backend (15,957 LOC), frontend (React/TypeScript), Docker, tests (1,330 LOC across 10 files), and all infrastructure configuration.

---

## 1. Executive Summary

VistterStream has seen substantial security hardening since the v3 review was published earlier today. Many of the critical and high-severity findings from v3 have been addressed in commit `435f90f` ("Security hardening v3: 14 fixes, 103 tests passing"). The CORS regex was tightened to RFC 1918 ranges, the registration endpoint now requires admin auth, HSTS and CSP headers were added, OAuth state tokens include timestamp expiry, password complexity is enforced, `postMessage` target origins were fixed in the destinations OAuth callback, SSRF validation was added to asset creation/update, dependencies were pinned, and the `_dbg_ffmpeg`/`_dbg` debug functions were removed. The audit middleware now extracts user identity from the JWT token.

However, several issues remain, and this v4 review identifies new findings not covered in v3.

### Scorecard

| Category | v3 Grade | v4 Grade | Trend | Notes |
|----------|----------|----------|-------|-------|
| **Architecture** | B | **B** | Stable | Clean modular design, minor debt in schemas monolith and singleton patterns |
| **Security** | C+ | **B-** | Up | Major v3 findings fixed; remaining debt is git history secrets, ReelForge XSS, and exception leakage |
| **Code Quality** | B | **B** | Stable | f-string logging and `print()` in settings.py persist; `.dict()` calls removed |
| **Testing** | C+ | **C+** | Stable | SSRF tests added, but ReelForge, timeline execution, OAuth flow still untested |
| **Deployment** | B+ | **A-** | Up | Resource limits added in rpi compose; multi-stage Docker solid |
| **Overall** | B- | **B** | Up | Good forward progress; the git history secret remains the top priority |

---

## 2. Remediation Verification -- v3 Findings

This section verifies each v3 finding against the current codebase.

### S1. Secrets Remain in Git History -- STILL PRESENT (CRITICAL)

**v3 finding:** `.env` was committed in prior commits with live secrets.
**Current status:** `.env` is in `.gitignore` (line 32), confirmed. However, `git log --all --diff-filter=A -- .env` shows the file was committed in `02c9cd6` (Oct 24, 2025). The early commit does not contain the production JWT/Encryption keys (it only had database URL and CORS origins), but commit `6995c49` ("Production security remediation") added `.env` to `.gitignore`, implying that secrets were present in the working copy at some point. **The git history has NOT been scrubbed** with `git filter-repo` or BFG.

**Verdict:** PARTIALLY FIXED -- `.gitignore` prevents new commits, but history is not clean.

### S2. No CSRF Protection -- ACCEPTABLE (was HIGH)

**v3 finding:** No CSRF tokens, `allow_credentials=True` with broad CORS regex.
**Current status:** CORS regex now restricted to RFC 1918 + localhost + `.local` + `stream.vistter.com`. Bearer tokens in localStorage provide inherent CSRF protection. This is an acceptable posture for a single-user appliance.

**Verdict:** ACCEPTABLE -- no further action needed.

### S3. XSS Risk in OAuth Callback HTML -- FIXED (was MEDIUM)

**v3 finding:** `postMessage` used `'*'` as target origin.
**Current status:** `destinations.py:526` now uses `window.location.origin` for the success callback, and line 542 does the same for the error callback.

**Verdict:** FIXED in destinations router.

**NEW FINDING:** The ReelForge OAuth callback (`reelforge.py:1422`) still uses `window.opener.postMessage('youtube-connected', '*')` -- the wildcard target origin was NOT fixed in this router. See NEW-S1 below.

### S4. OAuth State Token Not Time-Limited -- FIXED (was HIGH)

**v3 finding:** No timestamp in OAuth state payload.
**Current status:** `destinations.py:205` now includes `int(time.time())` in the payload. `_verify_oauth_state()` at line 225 rejects states older than 600 seconds (10 minutes). Four-part splitting (`dest_id:nonce:timestamp:sig`) is correctly implemented.

**Verdict:** FIXED.

### S5. Registration Endpoint Open -- FIXED (was HIGH)

**v3 finding:** `/api/auth/register` was unauthenticated.
**Current status:** `auth.py:101` now requires `current_user: dict = Depends(get_current_user)` and checks `current_user.username != "admin"` at line 103. Tests verify: 401 without auth, 403 for non-admin, 200 for admin.

**Verdict:** FIXED. Test coverage added (4 tests).

### S6. Weak Rate Limiting Configuration -- PARTIALLY FIXED (was MEDIUM)

**v3 finding:** No rate limiting beyond auth endpoints; rate limiter uses `get_remote_address` behind proxy.
**Current status:** Login is 5/5min, register is 3/5min. No rate limiting on password change, destination create/delete, emergency kill-all. SlowAPI still uses `get_remote_address` without `X-Forwarded-For` configuration behind Cloudflare Tunnel.

**Verdict:** PARTIALLY FIXED -- auth endpoints are rate-limited, but other sensitive endpoints remain unprotected.

### S7. No HSTS Header -- FIXED (was MEDIUM)

**v3 finding:** Missing `Strict-Transport-Security` and `Content-Security-Policy` headers.
**Current status:** `main.py:199` adds `Strict-Transport-Security: max-age=31536000; includeSubDomains`. `main.py:200` adds a comprehensive CSP policy: `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.youtube.com https://www.gstatic.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: http: https:; frame-src https://www.youtube.com; connect-src 'self' ws: wss:`.

**Verdict:** FIXED. Note: HSTS is sent unconditionally (not gated on HTTPS), which is fine -- browsers ignore it on plain HTTP.

### S8. Debug Log File with No Rotation -- FIXED (was MEDIUM)

**v3 finding:** `_dbg_ffmpeg()` and `_dbg()` writing to `/data/debug.log` with bare `except: pass`.
**Current status:** Searched for `_dbg_ffmpeg`, `_dbg(`, and `debug.log` across all backend `.py` files -- zero matches in application code. Only matches are in pip packages (`_pytest`).

**Verdict:** FIXED -- debug functions removed.

### S9. Exception Messages Exposed in API Responses -- PARTIALLY FIXED (was MEDIUM)

**v3 finding:** Multiple endpoints expose `str(e)` in HTTP 500 responses.
**Current status:**
- `streams.py:115` -- **FIXED**: now returns `"Failed to create stream"` (generic)
- `timelines.py:197` -- **FIXED**: now returns `"Failed to create timeline"` (generic)
- `timelines.py:283` -- **FIXED**: now returns `"Failed to update timeline"` (generic)
- `timelines.py:404` -- **FIXED**: now returns `"Failed to cleanup orphaned cues"` (generic)
- `assets.py:246` -- **FIXED**: now returns `"Upload failed"` (generic)
- `assets.py:313` -- **FIXED**: now returns `"Failed to fetch asset"` (generic)
- `destinations.py:447` -- **FIXED**: now returns `"Failed to create broadcast"` (generic)
- `timeline_execution.py:105` -- **STILL EXPOSED**: `detail=f"Failed to create YouTube broadcast for {dest.name}: {e}"` -- includes exception text
- `preview.py:74,76,106,151,153` -- **STILL EXPOSED**: Multiple `str(e)` leaks
- `reelforge.py` -- **STILL EXPOSED**: 15+ endpoints expose `str(e)` in error responses (lines 183, 279, 321, 399, 435, 451, 662, 783, 832, 862, 878, 990, 1023, 1060, 1351, 1385, 1536)
- `destinations.py:514` -- OAuth callback error page displays `str(e)` in HTML (mitigated by `html_escape` at line 535)

**Verdict:** PARTIALLY FIXED -- main CRUD endpoints fixed, but ReelForge (entire router), preview, and timeline execution still leak exception details.

### S10. CORS Origin Regex Too Broad -- FIXED (was MEDIUM)

**v3 finding:** Regex matched ANY IPv4 address including public IPs.
**Current status:** `main.py:176` regex now restricts to `192.168`, `10.x`, `172.(16-31).x`, `100.x` (Tailscale CGNAT), localhost, `.local`, and `stream.vistter.com`. The pattern correctly uses RFC 1918 ranges plus 100.64/10 for Tailscale.

**Verdict:** FIXED.

### S11. Unvalidated `api_url` on Asset Creation -- FIXED (was MEDIUM)

**v3 finding:** `create_asset()` and `update_asset()` did not validate `api_url` at creation time.
**Current status:** `assets.py:115-116` calls `_validate_url()` in `create_asset()`. `assets.py:146-147` calls `_validate_url()` in `update_asset()`.

**Verdict:** FIXED. Comprehensive SSRF test suite added (`test_ssrf_validation.py`, 28 tests).

### S12. Plaintext Console Logging of Credentials -- FIXED (was MEDIUM)

**v3 finding:** `Login.tsx:22` logged `{ username, password }` to console. `authService.ts` logged details.
**Current status:** `Login.tsx:21` now logs only `'Login attempt'` (no credentials). `authService.ts:27` logs `'AuthService: Login successful'` (no response data).

**Verdict:** FIXED.

### S13. No Password Complexity Enforcement -- FIXED (was MEDIUM)

**v3 finding:** `UserCreate` only required `min_length=6`, no complexity rules.
**Current status:** `schemas.py:176` requires `min_length=8` for `UserCreate.password`. `schemas.py:178-185` adds `validate_password_complexity` requiring at least one letter and one digit. `PasswordChangeRequest` at line 204 has the same `min_length=8` and `validate_password_complexity` for `new_password`. Test coverage includes: too-short rejection, no-digits rejection, no-letters rejection, valid password acceptance.

**Verdict:** FIXED. Four test cases cover the password complexity rules.

### S14. Audit Log Not Capturing User Identity -- FIXED (was LOW)

**v3 finding:** Audit middleware tried to read `request.state.user`, which is never set.
**Current status:** `middleware/audit.py:60-73` now implements `_extract_user_from_request()` which reads the JWT token from the `Authorization` header and decodes it using `jose_jwt.decode()` to extract the username from the `sub` claim. This no longer depends on `request.state.user`.

**Verdict:** FIXED. Note: `user_id` is still always `None` because the JWT only contains `sub` (username), not a numeric user ID. This is a minor gap -- the username is sufficient for audit purposes.

### S15. `python-jose` Library Unmaintained -- UNCHANGED (LOW)

**Current status:** `requirements.txt` still uses `python-jose[cryptography]==3.5.0`. The `[cryptography]` backend mitigates known CVEs in the default backend, but the library itself remains unmaintained. Migration to `PyJWT` would be ideal long-term.

**Verdict:** UNCHANGED -- low priority.

### S16. SQLite Database Not Encrypted at Rest -- UNCHANGED (LOW)

**Current status:** Still using unencrypted SQLite. Appropriate for a single-user appliance with physical access controls.

**Verdict:** UNCHANGED -- accepted risk.

### S17. `slowapi` and `alembic` Version Not Pinned Exactly -- FIXED (was LOW)

**v3 finding:** Used `>=` instead of `==`.
**Current status:** `requirements.txt:22` pins `slowapi==0.1.9` and line 23 pins `alembic==1.13.0`.

**Verdict:** FIXED.

### S18. No Content-Length Limit on API Requests -- UNCHANGED (LOW)

**Current status:** No global request body size limit. File uploads have a 50MB streaming check.

**Verdict:** UNCHANGED -- low priority.

---

## 3. Architecture Analysis

### 3.1 Directory Structure and Organization -- Grade: B+

The project maintains a clean layered architecture:

```
backend/
  routers/       (16 files, HTTP layer)
  services/      (23 files, business logic)
  models/        (7 files, ORM + Pydantic schemas)
  utils/         (6 utility modules)
  middleware/    (audit logging)
  migrations/   (legacy + Alembic)
  tests/        (10 test files)
```

**Strengths:**
- Clear separation: routers delegate to services, services use models
- Each domain has its own router, model, and service layer
- Utilities are isolated and focused

**Remaining weaknesses:**
- `models/schemas.py` is a 665-line monolith. Splitting by domain would improve maintainability
- `models/database.py` imports all model modules at the bottom (circular dependency managed by placement)
- The `delete/` directory still exists at the project root (appears to be discarded code)

### 3.2 Code Quality -- Grade: B

**Improvements since v3:**
- `.dict()` calls replaced with `.model_dump()` (no instances of `.dict()` found in application code)
- Debug log functions removed
- Credential logging removed from frontend

**Remaining issues:**
- **f-string logging throughout services.** ~30+ instances of `logger.info(f"...")` and `logger.error(f"...")` found in `timeline_executor.py`, `reelforge_capture_service.py`, `emergency.py`, and others. These construct the string even if the log level is disabled. Should use `%s` formatting
- **`print()` call in production code.** `settings.py:110` uses `print(f"Synced location to {len(assets)} asset(s)")` instead of logger
- **Emoji in log messages.** Services still use emoji in log strings (e.g., `"Starting ReelForge capture scheduler..."` but `reelforge_capture_service.py` has `"ReelForge:"` emoji prefixes). These render poorly in log aggregation tools
- **`from_orm()` still used.** `stream_service.py` and `camera_service.py` use the Pydantic v1 `from_orm()` method. While still functional, `model_validate()` is the Pydantic v2 recommended API
- **Inconsistent error handling in emergency router.** `emergency.py:39` uses `logger.info(f"Stopped {len(timeline_ids)} timelines")` with f-string, and the `sleep 2` subprocess call at line 63 (`subprocess.run(['sleep', '2'])`) blocks the async event loop. Should use `asyncio.sleep(2)` instead

### 3.3 Database Design -- Grade: B

Unchanged from v3. Key observations:
- SQLite appropriate for single-user appliance
- Alembic migration framework integrated
- Pool exhaustion monitoring via `@event.listens_for`
- Missing indices on `timeline_cues.track_id` and `reel_posts.status`
- JSON columns for structured data (acceptable for SQLite)

### 3.4 API Design -- Grade: B

**Improvements:**
- Stream create endpoint now returns generic error message
- Timeline create/update now return generic error messages
- Asset create/update now validate SSRF on creation

**Remaining issues:**
- No API versioning (`/api/` without version prefix)
- No pagination on timelines, streams, destinations list endpoints
- `POST /api/settings` should be `PUT` or `PATCH`
- ReelForge router has 15+ endpoints that still leak `str(e)` in error responses

### 3.5 Service Layer -- Grade: B-

Unchanged architectural patterns:
- Multiple state dictionaries in `TimelineExecutor` (6+ dicts without unified lifecycle)
- Singleton pattern via module-level functions
- Background task results not monitored (`asyncio.create_task()` fire-and-forget)
- `timeline_executor.py:25` forces `logger.setLevel(logging.DEBUG)` which overrides the global log level configuration

### 3.6 Frontend Architecture -- Grade: B

**Improvements:**
- Credential logging removed from `Login.tsx` and `authService.ts`

**Remaining issues:**
- Token stored in `localStorage` (inherent SPA tradeoff)
- No token refresh mechanism (30-minute JWT)
- Numerous `console.log` statements remain in production code: `TimelineEditor.tsx` has 12+ console.log calls, `Settings.tsx`, `StreamingDestinations.tsx`, `Dashboard.tsx`, `PreviewWindow.tsx` each have several. These are debug statements, not credential leaks, but still represent unnecessary production noise
- No frontend tests beyond CRA boilerplate

### 3.7 Docker/Deployment -- Grade: A-

**Improvements since v3:**
- **Resource limits added** in `docker-compose.rpi.yml`: backend gets `memory: 2G, cpus: 3.0`, RTMP relay gets `memory: 256M, cpus: 0.5`, preview server gets `memory: 256M, cpus: 0.5`, frontend gets `memory: 128M, cpus: 0.25`, cloudflared gets `memory: 128M, cpus: 0.25`
- Multi-stage build, non-root user, healthcheck, and VA-API GPU support all remain solid

**Remaining issues:**
- RTMP relay port `1935:1935` still exposed to host network in all compose files
- The base `docker/docker-compose.yml` (used for non-RPi setups) does NOT have resource limits -- only `docker-compose.rpi.yml` does
- No Docker Secrets (secrets passed via environment variables, visible in `docker inspect`)

### 3.8 Test Coverage -- Grade: C+

**Current state:** 10 test files, 1,330 lines of test code

| Test File | Coverage Area | Tests |
|-----------|--------------|-------|
| `test_auth.py` | Login, register, token validation, password complexity | ~12 |
| `test_cameras.py` | Camera CRUD | ~2 |
| `test_streams.py` | Stream CRUD | ~6 |
| `test_timelines.py` | Timeline CRUD | ~8 |
| `test_destinations.py` | Destination CRUD + watchdog config | ~8 |
| `test_assets.py` | Asset CRUD + upload + proxy | ~8 |
| `test_oauth_state.py` | HMAC state token generation/verification | 7 |
| `test_audit.py` | Audit middleware | ~3 |
| `test_logging.py` | Secret redaction in logs | ~4 |
| `test_ssrf_validation.py` | SSRF URL validation (NEW since v3) | 28 |

**Improvements:**
- SSRF validation tests added (28 test cases covering all blocked/allowed ranges)
- Registration protection tests added (401 without auth, 403 non-admin, 200 admin)
- Password complexity tests added (short, no digits, no letters, valid)

**Still missing:**
- No tests for ReelForge endpoints (entire feature, ~1,500 LOC untested)
- No tests for timeline execution (the core streaming feature)
- No tests for OAuth flow (exchange_code, callback handling)
- No integration tests (stream start-to-stop lifecycle)
- No concurrent access tests
- No frontend tests
- `test_ffmpeg_manager.py`, `test_camera_service_status.py`, `test_ptz_service_overrides.py`, `test_stream_status_endpoint.py` -- mentioned in v3 but NOT present in current `tests/` directory (only 10 files exist vs 14 in v3). These tests may have been removed or relocated

---

## 4. Security Analysis -- New Findings

### NEW-S1. XSS and postMessage Wildcard in ReelForge OAuth Callback
**Severity:** HIGH

The ReelForge YouTube OAuth callback at `reelforge.py:1416-1437` has two security issues:

1. **postMessage wildcard:** Line 1422 uses `window.opener.postMessage('youtube-connected', '*')` -- the `'*'` target origin allows any page that opened the popup to receive the message. The destinations router fixed this to use `window.location.origin`, but the ReelForge router was not updated.

2. **Unescaped error message in HTML:** Line 1434 injects `str(e)` directly into HTML without escaping: `<p>{str(e)}</p>`. If the exception message contains user-controlled data (e.g., from a malicious OAuth error response), this is a reflected XSS vector. The destinations router fixed this with `html_escape()`, but the ReelForge router was not updated.

3. **No HMAC state verification:** The ReelForge OAuth callback at line 1389 accepts a `code` parameter but does NOT verify an HMAC-signed state token. There is no CSRF protection on this OAuth flow, unlike the destinations OAuth which has full HMAC state verification.

4. **Hardcoded redirect URI:** Line 1375 and 1400 hardcode `http://localhost:8000/api/reelforge/youtube/callback` -- this will not work in production Docker deployments or behind Cloudflare Tunnel.

**Location:** `backend/routers/reelforge.py:1360-1437`

**Fix:** Apply the same security patterns from the destinations OAuth flow: add HMAC state tokens, use `html_escape()`, restrict `postMessage` target origin, and make the redirect URI configurable.

### NEW-S2. Emergency Endpoint Blocking Async Event Loop
**Severity:** MEDIUM

`emergency.py:63` calls `subprocess.run(['sleep', '2'])` which is a synchronous blocking call inside an async handler. This blocks the entire event loop for 2 seconds during an emergency kill-all operation. During this time, no other HTTP requests can be processed.

**Location:** `backend/routers/emergency.py:63`

**Fix:** Replace with `await asyncio.sleep(2)`.

### NEW-S3. Exception Message Leakage in ReelForge (Systematic)
**Severity:** MEDIUM

The ReelForge router (`reelforge.py`) has 15+ endpoints that expose raw Python exception messages via `detail=f"Failed to ...: {str(e)}"`. These leak internal implementation details, database errors, and third-party API error messages to clients.

**Affected endpoints:** Template CRUD (lines 399, 435, 451), capture queue (662, 990, 1023, 1060), post delete (783), target CRUD (832, 862, 878), export update (1351), YouTube auth (1385, 1536), and the OAuth callback error page (1434).

**Fix:** Log the full exception with `logger.error()`, return generic messages in HTTP responses.

### NEW-S4. Exception Message Leakage in Preview Router
**Severity:** MEDIUM

`preview.py` has 5 endpoints that expose `str(e)` or `f"Failed to ...: {str(e)}"` in error responses (lines 74, 76, 106, 151, 153).

**Fix:** Same as NEW-S3.

### NEW-S5. Missing Test Files
**Severity:** LOW (quality concern)

The v3 review documented 14 test files totaling 1,766 LOC. The current codebase has only 10 test files totaling 1,330 LOC. The following test files mentioned in v3 are missing:
- `test_ffmpeg_manager.py` (~12 tests)
- `test_camera_service_status.py` (~4 tests)
- `test_ptz_service_overrides.py` (~6 tests)
- `test_stream_status_endpoint.py` (~5 tests)

These may have been lost during a refactor. This represents a regression of ~27 tests.

### NEW-S6. Timeline Execution Leaks Broadcast Error to Client
**Severity:** MEDIUM

`timeline_execution.py:105` exposes the full exception when broadcast creation fails:
```python
raise HTTPException(status_code=500, detail=f"Failed to create YouTube broadcast for {dest.name}: {e}")
```

This can reveal YouTube API error details, token errors, or internal service information to the client.

**Fix:** Log the exception, return `detail="Failed to create YouTube broadcast"`.

### NEW-S7. Forced DEBUG Log Level in Timeline Executor
**Severity:** LOW

`timeline_executor.py:25` sets `logger.setLevel(logging.DEBUG)` which overrides the global log level configuration from `configure_logging()`. This means the timeline executor always logs at DEBUG level regardless of the `LOG_LEVEL` environment variable, potentially logging sensitive data to stdout in production.

**Fix:** Remove the `setLevel` override and rely on the root logger configuration.

---

## 5. Positive Findings -- What's Done Well

These represent improvements verified in this v4 review:

1. **CORS regex properly restricted to RFC 1918.** The regex at `main.py:176` only allows `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, `100.x.x.x` (Tailscale), localhost, `.local`, and the Cloudflare tunnel domain. This correctly blocks arbitrary public IPs.

2. **Registration endpoint protected.** Requires admin authentication with explicit username check and test coverage.

3. **OAuth state tokens time-limited.** 10-minute expiry window properly implemented with timing-safe HMAC comparison.

4. **HSTS and CSP headers added.** Comprehensive CSP policy allows YouTube embeds while restricting script/style sources.

5. **SSRF validation comprehensive.** `_validate_url()` applied at asset creation, update, proxy, and test endpoints. 28 test cases cover all scenarios.

6. **Password complexity enforced.** Minimum 8 characters, requires at least one letter and one digit. Both `UserCreate` and `PasswordChangeRequest` use the same validator.

7. **postMessage origin fixed in destinations.** Uses `window.location.origin` instead of `'*'`.

8. **Audit middleware captures user identity from JWT.** Properly decodes the token from the Authorization header.

9. **Dependencies pinned exactly.** All packages in `requirements.txt` use `==` pinning.

10. **Docker resource limits in production compose.** Backend limited to 2GB RAM / 3 CPUs, preventing runaway FFmpeg from exhausting the mini PC.

11. **Fernet encryption for all secrets at rest.** Camera passwords, stream keys, YouTube API keys, OAuth client secrets, and refresh tokens are all encrypted.

12. **Multi-stage Docker build with non-root execution.** Builder stage compiles C extensions, runtime stage runs as `appuser:1000`.

13. **Structured JSON logging with secret redaction.** Five regex patterns mask RTSP credentials, API keys, Bearer tokens, and Fernet tokens.

14. **RTMP relay restricted to Docker bridge + localhost.** nginx-rtmp config uses `allow publish 172.16.0.0/12; deny publish all`.

15. **Mandatory environment variables.** `JWT_SECRET_KEY` and `ENCRYPTION_KEY` raise `RuntimeError` at import time. Docker Compose uses `${VAR:?error message}`.

---

## 6. Prioritized Action Items

### Phase 1: Critical -- Do Immediately

| # | Action | Severity | Effort | Status |
|---|--------|----------|--------|--------|
| 1 | **Scrub `.env` from git history** with `git filter-repo --path .env --invert-paths` | CRITICAL | 15 min | Carryover from v3 |
| 2 | **Rotate ALL secrets** if they were ever in .env in git (JWT_SECRET_KEY, ENCRYPTION_KEY, Cloudflare tunnel token) | CRITICAL | 30 min | Carryover from v3 |
| 3 | **Fix ReelForge OAuth XSS** -- add `html_escape()` to error page, restrict `postMessage` origin, add HMAC state token | HIGH | 1 hr | NEW-S1 |
| 4 | **Fix ReelForge hardcoded redirect URI** -- make configurable like destinations OAuth | HIGH | 15 min | NEW-S1 |

### Phase 2: High Priority -- This Week

| # | Action | Severity | Effort |
|---|--------|----------|--------|
| 5 | Sanitize exception messages in ReelForge router (15+ endpoints) | MEDIUM | 1 hr |
| 6 | Sanitize exception messages in preview router (5 endpoints) | MEDIUM | 30 min |
| 7 | Fix `timeline_execution.py:105` exception leakage | MEDIUM | 5 min |
| 8 | Replace `subprocess.run(['sleep', '2'])` with `await asyncio.sleep(2)` in emergency.py | MEDIUM | 5 min |
| 9 | Remove `logger.setLevel(logging.DEBUG)` from timeline_executor.py | LOW | 2 min |
| 10 | Replace `print()` with logger in settings.py:110 | LOW | 2 min |
| 11 | Add rate limiting on password change and emergency kill-all endpoints | MEDIUM | 15 min |

### Phase 3: Quality -- Next Sprint

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 12 | Replace f-string logging with `%s` formatting (30+ instances across services) | LOW | 1 hr |
| 13 | Replace `from_orm()` with `model_validate()` in stream_service.py and camera_service.py | LOW | 15 min |
| 14 | Add refresh token mechanism (extends session without re-login) | HIGH | 4 hr |
| 15 | Split `models/schemas.py` into domain-specific schema files | LOW | 2 hr |
| 16 | Add pagination to timelines, streams, and destinations list endpoints | LOW | 1 hr |
| 17 | Add Docker resource limits to base `docker-compose.yml` (not just rpi compose) | LOW | 10 min |
| 18 | Remove `console.log` statements from frontend production code (20+ instances) | LOW | 30 min |
| 19 | Clean up the `delete/` directory at project root | LOW | 5 min |

### Phase 4: Testing -- Ongoing

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 20 | Restore missing test files (ffmpeg_manager, camera_service_status, ptz_service_overrides, stream_status) | HIGH | 2 hr |
| 21 | Add ReelForge endpoint tests (entire feature untested) | MEDIUM | 4 hr |
| 22 | Add timeline execution integration tests | HIGH | 4 hr |
| 23 | Add OAuth callback flow tests (mock Google API) | MEDIUM | 2 hr |
| 24 | Add concurrent access tests for FFmpeg manager | MEDIUM | 2 hr |
| 25 | Add frontend component tests | LOW | 4 hr |
| 26 | Set up `pip-audit` in CI for dependency vulnerability scanning | LOW | 30 min |

---

## 7. Changes Since v3 -- Remediation Tracker

| v3 Finding | Status | Notes |
|------------|--------|-------|
| S1. Secrets in git history | **PARTIALLY FIXED** | `.gitignore` added, history NOT scrubbed |
| S2. No CSRF protection | **ACCEPTABLE** | Bearer tokens + restricted CORS |
| S3. XSS in OAuth callback HTML (destinations) | **FIXED** | `html_escape()` + `window.location.origin` |
| S4. OAuth state not time-limited | **FIXED** | 10-minute expiry with timestamp |
| S5. Registration endpoint open | **FIXED** | Admin auth required + test coverage |
| S6. Weak rate limiting | **PARTIALLY FIXED** | Auth endpoints covered, others not |
| S7. No HSTS header | **FIXED** | HSTS + CSP added |
| S8. Debug log file | **FIXED** | `_dbg_*` functions removed |
| S9. Exception messages exposed | **PARTIALLY FIXED** | Main CRUD fixed, ReelForge/preview not |
| S10. CORS regex too broad | **FIXED** | RFC 1918 ranges only |
| S11. Unvalidated asset URL | **FIXED** | SSRF check on create/update |
| S12. Console credential logging | **FIXED** | Only `'Login attempt'` logged |
| S13. No password complexity | **FIXED** | 8+ chars, letter + digit required |
| S14. Audit user identity | **FIXED** | JWT extraction from Authorization header |
| S15. python-jose unmaintained | UNCHANGED | Low priority |
| S16. SQLite unencrypted | UNCHANGED | Accepted risk |
| S17. Dependencies not pinned | **FIXED** | All `==` pinning |
| S18. No content-length limit | UNCHANGED | Low priority |

### New v4 Findings

| Finding | Severity | Description |
|---------|----------|-------------|
| NEW-S1 | HIGH | ReelForge OAuth: XSS, no HMAC state, wildcard postMessage, hardcoded redirect URI |
| NEW-S2 | MEDIUM | Emergency endpoint blocks async event loop with synchronous sleep |
| NEW-S3 | MEDIUM | ReelForge: 15+ endpoints leak exception messages |
| NEW-S4 | MEDIUM | Preview: 5 endpoints leak exception messages |
| NEW-S5 | LOW | 4 test files from v3 are missing (~27 tests lost) |
| NEW-S6 | MEDIUM | Timeline execution leaks broadcast error to client |
| NEW-S7 | LOW | Forced DEBUG log level in timeline executor |

---

## 8. Summary of Outstanding Debt

### Security Debt (ordered by severity)

1. **CRITICAL:** Git history still contains `.env` -- needs `git filter-repo` scrub and secret rotation
2. **HIGH:** ReelForge OAuth flow lacks HMAC state, has XSS in error page, wildcard postMessage
3. **MEDIUM:** 20+ endpoints across ReelForge/preview/timeline_execution still leak `str(e)` to clients
4. **MEDIUM:** Synchronous sleep blocking event loop in emergency kill
5. **LOW:** Rate limiting only on auth, not on other sensitive operations

### Architecture Debt

1. `schemas.py` monolith (665 lines)
2. f-string logging throughout services
3. Singleton pattern makes unit testing harder
4. No token refresh mechanism (30-min JWT)
5. Multiple state dictionaries in `TimelineExecutor` without unified lifecycle

### Test Debt

1. ReelForge entirely untested (~1,500 LOC)
2. Timeline execution untested
3. OAuth flow untested
4. 4 test files appear to have been lost
5. No frontend tests

---

*Review generated by Claude Code Deep Audit v4 (Opus 4.6). Based on full read of 15,957 lines of backend code, 10 test files (1,330 LOC), frontend React/TypeScript source, Docker configuration, and infrastructure files.*
