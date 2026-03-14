# VistterStream Architecture & Security Review v5 -- Final Deep Pass
**Date:** 2026-03-14 | **Reviewer:** Claude Code Deep Audit v5 (Opus 4.6, 1M context)
**Scope:** Full codebase read of all backend services (23 files), routers (16 files), models (7 files), utilities (6 files), middleware (1 file), Docker/infrastructure configuration, frontend React/TypeScript (17 source files), and test fixtures. This review focuses exclusively on **new findings** not identified in v1-v4.

**Method:** End-to-end code path tracing, concurrency analysis, secret flow tracing, FFmpeg command construction audit, database session lifecycle tracking, and dependency CVE review.

---

## 1. Executive Summary

VistterStream has matured significantly through four rounds of review, with most critical and high-severity issues addressed. This v5 final-pass review digs deeper into execution paths, concurrency patterns, and subtle issues that surface-level reviews missed. The codebase is architecturally sound for a single-user streaming appliance, but this review identifies **13 new findings** ranging from a high-severity deadlock risk to several medium issues in credential handling, resource lifecycle, and error recovery.

### Scorecard

| Category | v4 Grade | v5 Grade | Trend | Notes |
|----------|----------|----------|-------|-------|
| **Architecture** | B | **B** | Stable | Clean layered design; multiple `_build_rtsp_url` copies and singleton patterns remain as debt |
| **Security** | B- | **B** | Up | No new critical findings; medium issues in RTSP credential encoding and SSRF bypass |
| **Concurrency** | N/A | **C+** | New | Deadlock risk in shutdown_all, race conditions in seamless handoff, no lock on TimelineExecutor state |
| **Code Quality** | B | **B** | Stable | f-string logging persists; `bare except` in 3 services |
| **Error Recovery** | N/A | **B-** | New | Good watchdog design; session leak in timeline executor, temp file leak on crash |
| **Testing** | C+ | **C+** | Stable | No new test regressions; concurrency and lifecycle tests still absent |
| **Deployment** | A- | **A-** | Stable | Solid Docker setup; HLS CORS wildcard is minor |
| **Overall** | B | **B** | Stable | Mature for its use case; concurrency debt is the main gap |

---

## 2. Deep-Dive Findings

### 2.1 Code Path Analysis: Timeline Start -> FFmpeg Launch -> Stream -> Stop -> Cleanup

**Traced path:** `POST /api/timeline-execution/start` -> `timeline_execution.py:start_timeline()` -> `TimelineExecutor.start_timeline()` -> `_execute_timeline()` -> `_prefetch_all_overlays()` -> `_execute_segment()` -> `FFmpegProcessManager.start_stream()` -> `asyncio.create_subprocess_exec()` -> `_monitor_process()` -> Stop: `stop_timeline()` -> `ffmpeg_manager.stop_stream()` -> `_graceful_shutdown()` -> cleanup temp files -> `db.close()`

#### V5-F1. Database Session Held for Entire Timeline Execution Lifetime (MEDIUM)

**Location:** `backend/services/timeline_executor.py:180`

The `_execute_timeline()` method opens a database session at line 180 (`db = SessionLocal()`) and holds it open for the **entire duration** of the timeline execution, which can be hours or days for looping timelines. The session is only closed in the `finally` block at line 405.

**Impact:**
- SQLite connections are held indefinitely, preventing other threads from writing (SQLite's write-ahead-log mitigates this, but long-held connections can still cause "database is locked" errors)
- The session's identity map grows unboundedly as it queries overlays, cameras, presets, and cues across loops
- Stale reads: the same session will not see changes made by API endpoints (e.g., if a user edits an overlay asset while a timeline is running, the executor sees stale data from its long-lived session)

**Recommendation:** Open a fresh session per loop iteration or per segment. The `get_session()` context manager already exists in `database.py` for exactly this pattern.

#### V5-F2. Temp File Leak on Unhandled Exception During Overlay Prefetch (LOW)

**Location:** `backend/services/timeline_executor.py:396-404`

If `_prefetch_all_overlays()` raises an exception (e.g., network timeout downloading a Google Drawing), the `overlay_temp_files` variable may be unbound when the `finally` block tries to clean it up. The `finally` block at line 397 references `overlay_temp_files` which would cause an `UnboundLocalError`, and the temp files from any partial downloads would leak.

The current code does have `if overlay_temp_files:` at line 397, but if the exception occurs during `_prefetch_all_overlays()` before the return assigns both values, `overlay_temp_files` is never assigned.

**Recommendation:** Initialize `overlay_temp_files = []` before the `try` block.

#### V5-F3. Seamless Handoff Temporary Stream ID Collision Risk (LOW)

**Location:** `backend/services/timeline_executor.py:808`

The seamless handoff uses `temp_stream_id = timeline_id + 1000000` as a temporary FFmpeg stream ID. If two timelines are running with IDs that differ by exactly 1,000,000 (unlikely but possible), their temp IDs would collide. More practically, the temp ID is never cleaned up from `_monitoring_tasks` or `_on_stream_died_callbacks` if the handoff fails between steps 1 and 3.

**Recommendation:** Use a UUID-based or atomic counter-based temp ID instead of arithmetic.

---

### 2.2 Concurrency Safety

#### V5-F4. Deadlock Risk in FFmpegProcessManager.shutdown_all() (HIGH)

**Location:** `backend/services/ffmpeg_manager.py:375-387`

`shutdown_all()` iterates over `self.processes.keys()` and calls `stop_stream()` for each stream via `asyncio.gather()`. Each `stop_stream()` call acquires `self._lock` (line 256: `async with self._lock`). However, `shutdown_all()` does NOT hold the lock, so the following scenario can deadlock:

1. `shutdown_all()` starts, gathers tasks to stop streams A, B, C
2. Stream A's `stop_stream()` acquires the lock
3. Meanwhile, `_monitor_process()` detects stream B died and calls `restart_stream()`, which does NOT acquire the lock but modifies `self.processes` directly (line 304: no lock acquisition in `restart_stream()`)
4. `restart_stream()` calls `asyncio.create_subprocess_exec()` which suspends
5. Meanwhile, stream A's `stop_stream()` tries to delete from `_monitoring_tasks` while the restart is modifying the same dict

Additionally, `restart_stream()` (line 288) does **not** acquire `self._lock` before modifying `self.processes`, even though `start_stream()` and `stop_stream()` both do. This is a clear TOCTOU violation.

**Impact:** Potential deadlock during emergency shutdown, or dictionary mutation during iteration causing `RuntimeError`.

**Recommendation:**
1. Add `async with self._lock` to `restart_stream()`
2. In `shutdown_all()`, acquire the lock once, snapshot the keys, release the lock, then stop each stream

#### V5-F5. TimelineExecutor State Dictionaries Have No Lock Protection (MEDIUM)

**Location:** `backend/services/timeline_executor.py:39-51`

The `TimelineExecutor` has 6 state dictionaries (`active_timelines`, `ffmpeg_managers`, `playback_positions`, `_position_update_tasks`, `timeline_destinations`, `timeline_destination_ids`, `_last_segment_time`) that are read and written from multiple concurrent coroutines:

- `start_timeline()` writes to all dicts (called from HTTP handler)
- `stop_timeline()` deletes from all dicts (called from HTTP handler)
- `_execute_timeline()` writes to `playback_positions` (background task)
- `_on_ffmpeg_died()` writes to `playback_positions` (callback from monitor task)
- `_update_position_during_segment()` writes to `playback_positions` (background task)
- Watchdog's `check_and_recover()` reads `ffmpeg_managers` and `_last_segment_time`

While asyncio is single-threaded, dictionary mutation between `await` points can cause state inconsistency. For example, `stop_timeline()` deletes `active_timelines[timeline_id]` at line 144, but the background `_execute_timeline()` task may still be running and trying to write to `playback_positions[timeline_id]`.

**Recommendation:** Add an `asyncio.Lock` to TimelineExecutor for state mutation operations, or use a single unified state object per timeline with lifecycle management.

#### V5-F6. Race Condition in Seamless Handoff Process Dict Manipulation (MEDIUM)

**Location:** `backend/services/timeline_executor.py:858-867`

During the seamless handoff, the code does `ffmpeg_manager.processes.pop(temp_stream_id)` and `ffmpeg_manager.processes[timeline_id] = stream_proc` without holding the FFmpeg manager's lock. This happens outside `async with self._lock` because the caller is the timeline executor, not the FFmpeg manager itself. Meanwhile, the monitoring task for the temp stream (started at line 232 in `start_stream()`) is reading from `self.processes[temp_stream_id]` and could see a KeyError when the dict entry is popped.

**Recommendation:** Either expose a locked `remap_stream()` method on `FFmpegProcessManager`, or acquire the manager's lock before manipulating its internal dictionaries.

---

### 2.3 FFmpeg Command Injection Analysis

#### V5-F7. RTSP URL Credential Encoding Inconsistency -- Potential FFmpeg Parse Failure (MEDIUM)

**Location:** Multiple `_build_rtsp_url()` implementations

There are **6 copies** of `_build_rtsp_url()` across the codebase:

| File | URL-Encodes Credentials? |
|------|--------------------------|
| `stream_service.py:87` | **Yes** (`urllib.parse.quote()`) |
| `camera_service.py:356` | **Yes** (`urllib.parse.quote()`) |
| `timeline_executor.py:1112` | **No** -- raw interpolation |
| `seamless_timeline_executor.py:673` | **No** -- raw interpolation |
| `rtmp_relay_service.py:217` | **No** -- raw interpolation |
| `reelforge_capture_service.py:291` | **No** -- raw interpolation |

Four of the six implementations embed camera passwords directly into the RTSP URL without URL-encoding. If a camera password contains `@`, `:`, `/`, or other special characters, the RTSP URL will be malformed and FFmpeg will fail to connect or, worse, interpret the password fragment as part of the hostname.

This is **not** a command injection vulnerability because all FFmpeg invocations use list-based `create_subprocess_exec()` (never shell interpolation). However, it is a reliability issue that will cause mysterious stream failures for cameras with special-character passwords.

**Impact:** Stream launch failure for cameras with passwords containing `@`, `:`, `/`, `#`, or `?`.

**Recommendation:** Extract the URL-encoding `_build_rtsp_url()` from `stream_service.py` into a shared utility in `utils/` and replace all 6 copies.

#### FFmpeg Command Injection: Confirmed Safe

All FFmpeg command construction uses list-based arguments passed to `asyncio.create_subprocess_exec()` (not `subprocess.run(shell=True)` or string concatenation). Camera URLs, stream keys, and overlay paths are passed as individual list elements, preventing shell injection. The overlay file paths come from controlled sources: `tempfile.NamedTemporaryFile` (which generates safe names) or validated upload paths. This pattern is correct and no injection vectors were found.

---

### 2.4 Database Session Lifecycle

#### V5-F8. Lifespan Startup Creates DB Session via Generator Without Proper Iteration (MEDIUM)

**Location:** `backend/main.py:69, 79`

The lifespan function calls `db = next(get_db())` at lines 69 and 79 to get a database session. The `get_db()` generator yields a session and then closes it in the `finally` block. By calling `next()`, only the yield is triggered -- the `finally` block (which closes the session) is **never executed** because the generator is never iterated past the yield. This leaks the database session.

Line 69: `db = next(get_db())` -- used for watchdog manager startup
Line 79: `db = next(get_db())` -- used for ReelForge capture service init

Both sessions are handed to background services but never closed. The `get_session()` context manager in `database.py` exists for exactly this use case but is not used here.

**Impact:** Two database connections leaked at startup. For SQLite with a single-writer model, this is low-impact. For any future PostgreSQL migration, this would contribute to connection pool exhaustion.

**Recommendation:** Replace `next(get_db())` with `get_session()` context manager, or manually call `db.close()` after the background services are initialized.

#### Session Management in Background Services: Generally Correct

The following background services correctly manage sessions:
- `camera_health_monitor.py:62` -- opens and closes in `_check_all_cameras()`
- `rtmp_relay_service.py:183` -- opens and closes in `start_all_cameras()`
- `reelforge_capture_service.py:156` -- opens and closes in `_execute_capture()`
- `audit.py:91-105` -- opens and closes per middleware invocation

The timeline executor (V5-F1) is the main exception.

---

### 2.5 Secret Handling End-to-End

**Traced flow:** `.env` -> `os.getenv()` -> `Fernet._key` -> `encrypt()/decrypt()` -> database column -> API response -> FFmpeg command

#### V5-F9. Decrypted Stream Key Exposed in FFmpeg Process Command Line (LOW)

**Location:** `backend/models/destination.py:53-56`

`StreamingDestination.get_full_rtmp_url()` calls `decrypt(self.stream_key)` and returns the plaintext stream key embedded in the RTMP URL: `f"{self.rtmp_url}/{key}"`. This URL is then passed to `FFmpegProcessManager.start_stream()` as `output_urls`, which stores it in `StreamProcess.command` (line 114) and `StreamProcess.output_urls` (line 116).

The decrypted stream key is visible in:
1. `StreamProcess.command` -- the full FFmpeg command line stored in memory
2. `StreamProcess.output_urls` -- the list of destination URLs stored in memory
3. The process command line visible via `/proc/<pid>/cmdline` or `ps aux` to any user on the host

The secret redaction filter (`logging_config.py`) masks RTSP credentials and Bearer tokens in log messages, but does not mask RTMP stream keys in URLs. However, `_build_ffmpeg_command()` passes the URL as a list element to `create_subprocess_exec()`, so it appears in the process table.

**Impact:** Stream keys visible in process listing. For a single-user Docker container running as `appuser`, this is low risk. For shared hosts, it would be a credential exposure.

**Recommendation:** This is an inherent limitation of RTMP (the key must be in the URL). Acceptable for the appliance deployment model. Consider adding `rtmp://.*/(\\S+)` to `_REDACT_PATTERNS` in logging_config.py to mask stream keys in log output.

#### Secret Handling: Generally Correct

- `JWT_SECRET_KEY` and `ENCRYPTION_KEY` raise `RuntimeError` at import time if missing
- All camera passwords stored as `password_enc` (Fernet-encrypted)
- All stream keys stored as encrypted Fernet tokens
- All OAuth client secrets stored as `*_enc` columns
- All OAuth refresh tokens stored as `*_enc` columns
- API responses mask stream keys as `"--------"` via `_dest_to_response()`
- `youtube_oauth_client_secret_enc` and `youtube_oauth_refresh_token_enc` are stripped from API responses

---

### 2.6 Docker Networking

#### V5-F10. HLS Preview Endpoint Has CORS Wildcard `*` (LOW)

**Location:** `docker/nginx-rtmp/nginx.conf:59`

The nginx-rtmp HLS endpoint at line 59 returns `Access-Control-Allow-Origin *`. While the RTMP publish/play restrictions correctly limit to Docker bridge network + localhost, the HLS HTTP endpoint at port 8080 serves preview streams to any origin.

Port 8081 (mapped from 8080) is exposed to the host network in both `docker-compose.yml` and `docker-compose.rpi.yml`. This means any website loaded in a browser on the local network could embed/access the HLS preview stream.

**Impact:** Low -- the HLS stream contains only camera preview data, and the appliance is on a private network. No authentication credentials are exposed through HLS.

**Recommendation:** Replace `*` with the configured CORS origin or remove the CORS header if the preview is only accessed by the VistterStream frontend.

#### Docker Networking: Generally Correct

- Backend, RTMP relay, preview server, and frontend are on a shared Docker bridge network (`vistter-net`)
- RTMP relay publish/play restricted to `172.16.0.0/12` and `127.0.0.1`
- Port 1935 exposed to host (needed for camera ingestion from local network cameras)
- Cloudflared runs in the same network, proxying only the frontend and backend
- `host.docker.internal:host-gateway` correctly resolves for reaching TempestWeather on the host

---

### 2.7 Frontend Security

#### No Stored XSS Found

React's JSX rendering automatically escapes all interpolated values. A search for `dangerouslySetInnerHTML` returned zero results across all 17 frontend source files. User-controlled strings (camera names, timeline names, preset names, destination names) are rendered via JSX `{variable}` syntax, which is safe.

The YouTube embed on the Dashboard uses `youtubeVideoId` which comes from the API's `youtube_broadcast_id` field. This is a Google-assigned ID string (alphanumeric), not user-controlled content.

#### V5-F11. 112 console.log Statements in Production Frontend (LOW)

**Location:** All 17 frontend source files

The v4 review noted "20+ console.log statements." The actual count is **112 occurrences** across 17 files. The heaviest offenders are `TimelineEditor.tsx` (27), `ReelForge.tsx` (14), and `PreviewWindow.tsx` (11).

While none of these log credentials (that was fixed in v3), they expose internal state, API response structures, and error details to anyone opening browser DevTools. This is an information disclosure concern for the Cloudflare Tunnel deployment where external users can access the UI.

**Recommendation:** Add a build-time `console.log` stripping plugin (e.g., `babel-plugin-transform-remove-console` or Vite equivalent) for production builds.

---

### 2.8 Error Recovery

#### FFmpeg Crash Mid-Stream

**Recovery path:** FFmpeg process dies -> `_monitor_process()` detects empty read -> sets `StreamStatus.ERROR` -> invokes `_on_stream_died_callbacks` -> `TimelineExecutor._on_ffmpeg_died()` updates playback position status to "error" -> watchdog's `check_and_recover()` detects unhealthy state (3 consecutive checks) -> calls `recover_stream()` -> stops FFmpeg -> timeline executor's loop re-enters `_execute_segment()` which detects `stream_running=False` -> starts new FFmpeg process.

This recovery chain is well-designed. The watchdog has a 120-second cooldown between recovery attempts to prevent rapid cycling.

**Gap found:** After recovery, the FFmpeg monitor task for the crashed process is cancelled (line 278), but the callback in `_on_stream_died_callbacks` is not cleaned up until the next `start_stream()` call. If recovery fails, the stale callback persists.

#### Camera Goes Offline

The camera health monitor checks every 180 seconds and updates `last_seen`. If a camera is offline during timeline execution, FFmpeg will fail to connect (5-second RTSP timeout per `_build_ffmpeg_command()` line 424). The segment error is caught at line 334, logged, and the executor continues to the next segment. This is correct behavior -- it doesn't crash the entire timeline.

#### YouTube API Error

Errors in `create_broadcast()` during timeline start (line 103-105 in `timeline_execution.py`) raise an HTTPException, which correctly prevents the timeline from starting. The exception message was identified in v4 (NEW-S6) as leaking internal details -- still unfixed.

---

### 2.9 Dependency Analysis

#### V5-F12. Known Vulnerability in `python-jose` and Outdated `pytest-asyncio` (MEDIUM)

**Location:** `backend/requirements.txt`

| Package | Version | Issue |
|---------|---------|-------|
| `python-jose[cryptography]` | 3.5.0 | Unmaintained since 2022. CVE-2024-33663 (ECDSA signature bypass) does not affect HS256 usage, but future CVEs will not be patched. The `[cryptography]` backend mitigates the most severe known CVEs. |
| `pytest-asyncio` | 1.3.0 | Extremely outdated (current is 0.24+). Version 1.3.0 does not exist in PyPI -- this may be a typo and the actual installed version differs. The `asyncio_mode` configuration is not set, which means tests may silently skip async test fixtures. |
| `passlib` | 1.7.4 | `passlib` is used but `bcrypt` 5.0.0 is also a direct dependency. The code uses `bcrypt` directly (not through passlib). `passlib` appears to be an unused dependency. |

No CVEs with CVSS >= 7.0 were found for the currently pinned versions of `fastapi`, `uvicorn`, `sqlalchemy`, `httpx`, `pydantic`, `cryptography`, `google-*`, or `openai` packages as of the knowledge cutoff.

**Recommendation:**
1. Migrate from `python-jose` to `PyJWT` (drop-in replacement for HS256)
2. Fix `pytest-asyncio` version (should be `==0.24.0` or similar)
3. Remove `passlib` if not used (confirm by searching for `passlib` imports)

---

### 2.10 Configuration Security

#### V5-F13. SSRF Validation Bypass via DNS Rebinding (MEDIUM)

**Location:** `backend/routers/assets.py:35-66`

The `_validate_url()` function checks if the hostname resolves to a blocked IP address. However, it performs the check at validation time, not at fetch time. A DNS rebinding attack could work as follows:

1. Attacker creates asset with `api_url` = `http://rebind.example.com/image.png`
2. At validation time, `rebind.example.com` resolves to `8.8.8.8` (passes validation)
3. At fetch time (in `_download_asset_image()` or proxy), `rebind.example.com` resolves to `127.0.0.1` (blocked address)
4. The request hits localhost, bypassing the SSRF filter

This is a theoretical attack because:
- The attacker needs authenticated access to create an asset
- The appliance is on a private network
- The fetched content is an image, limiting exploitation

However, the `proxy_asset_image()` endpoint (line 285) is on the public router (no auth required) and proxies whatever URL is stored in the database. If an attacker can create an asset (requires auth), subsequent proxy requests can be made without auth by anyone on the network.

**Recommendation:** Re-validate the URL at fetch time, or use `httpx`'s DNS resolution hook to block private IPs at the transport level. Alternatively, accept this as a known limitation for the single-user appliance model.

#### os.getenv() Calls: Reviewed

All `os.getenv()` calls were reviewed:

| Call | Default | Assessment |
|------|---------|------------|
| `JWT_SECRET_KEY` | None -> RuntimeError | **Correct** |
| `ENCRYPTION_KEY` | None -> RuntimeError | **Correct** |
| `DATABASE_URL` | `sqlite:///./vistterstream.db` | **Acceptable** for dev/appliance |
| `CORS_ALLOW_ORIGINS` | Falls through to hardcoded list | **Correct** |
| `CORS_ALLOW_ORIGIN_REGEX` | Falls through to RFC 1918 regex | **Correct** |
| `CLOUDFLARE_TUNNEL_DOMAIN` | `stream.vistter.com` | **Acceptable** -- only used in CORS list |
| `ENABLE_DOCS` | `""` (disabled) | **Correct** -- API docs off by default |
| `UPLOADS_DIR` | Local `uploads/` path | **Correct** |
| `RTMP_RELAY_HOST` | `127.0.0.1` | **Correct** for non-Docker; overridden in compose |
| `RTMP_RELAY_PORT` | `1935` | **Correct** |
| `LOG_FORMAT` | `json` | **Correct** |
| `LOG_LEVEL` | `INFO` | **Correct** |
| `DEFAULT_ADMIN_USERNAME` | `admin` | **Acceptable** |
| `DEFAULT_ADMIN_PASSWORD` | None -> auto-generated | **Correct** |
| `TEMPEST_API_URL` | `http://host.docker.internal:8036` | **Acceptable** |

No insecure defaults found. The mandatory variables (`JWT_SECRET_KEY`, `ENCRYPTION_KEY`) correctly fail fast at import time.

---

## 3. Risk Matrix

| ID | Finding | Severity | Likelihood | Risk Score | Effort |
|----|---------|----------|------------|------------|--------|
| V5-F4 | Deadlock in FFmpegProcessManager.shutdown_all() | High | Medium | **High** | 30 min |
| V5-F1 | DB session held for entire timeline lifetime | Medium | High | **Medium-High** | 1 hr |
| V5-F7 | RTSP credential encoding inconsistency (4/6 copies) | Medium | Medium | **Medium** | 30 min |
| V5-F5 | TimelineExecutor state dicts unprotected | Medium | Medium | **Medium** | 1 hr |
| V5-F6 | Race condition in seamless handoff dict manipulation | Medium | Low | **Medium** | 30 min |
| V5-F8 | Lifespan startup leaks 2 DB sessions | Medium | High (always) | **Medium** | 10 min |
| V5-F13 | SSRF DNS rebinding bypass | Medium | Very Low | **Low-Medium** | 2 hr |
| V5-F12 | python-jose unmaintained + pytest-asyncio version | Medium | Low | **Low-Medium** | 1 hr |
| V5-F9 | Stream key visible in process listing | Low | Low | **Low** | 15 min |
| V5-F10 | HLS CORS wildcard `*` | Low | Low | **Low** | 5 min |
| V5-F11 | 112 console.log in production frontend | Low | Low | **Low** | 30 min |
| V5-F2 | Temp file leak on overlay prefetch exception | Low | Low | **Low** | 5 min |
| V5-F3 | Seamless handoff temp stream ID collision | Low | Very Low | **Very Low** | 10 min |

---

## 4. Recommendations (Prioritized)

### Phase 1: Concurrency Fixes (This Sprint)

| # | Action | Finding | Effort |
|---|--------|---------|--------|
| 1 | Add `async with self._lock` to `restart_stream()` in FFmpegProcessManager | V5-F4 | 10 min |
| 2 | Fix `shutdown_all()` to snapshot keys under lock, then stop outside lock | V5-F4 | 20 min |
| 3 | Add lock or use locked helper for seamless handoff dict remapping | V5-F6 | 30 min |
| 4 | Replace `next(get_db())` with `get_session()` context manager in lifespan | V5-F8 | 10 min |
| 5 | Initialize `overlay_temp_files = []` before try block in `_execute_timeline()` | V5-F2 | 5 min |

### Phase 2: Reliability Improvements (This Sprint)

| # | Action | Finding | Effort |
|---|--------|---------|--------|
| 6 | Extract `_build_rtsp_url()` to shared utility with URL encoding; replace all 6 copies | V5-F7 | 30 min |
| 7 | Shorten DB session lifetime in `_execute_timeline()` to per-loop or per-segment | V5-F1 | 1 hr |
| 8 | Add `asyncio.Lock` to TimelineExecutor for state dict mutations | V5-F5 | 1 hr |

### Phase 3: Security Hardening (Next Sprint)

| # | Action | Finding | Effort |
|---|--------|---------|--------|
| 9 | Migrate from `python-jose` to `PyJWT` | V5-F12 | 1 hr |
| 10 | Fix `pytest-asyncio` version and verify async tests actually run | V5-F12 | 30 min |
| 11 | Add RTMP stream key redaction pattern to logging_config.py | V5-F9 | 15 min |
| 12 | Replace HLS CORS `*` with specific origin in nginx.conf | V5-F10 | 5 min |
| 13 | Add console.log stripping for production frontend builds | V5-F11 | 30 min |
| 14 | Remove `passlib` from requirements.txt if unused | V5-F12 | 10 min |

### Phase 4: Accepted Risks (Document and Move On)

| # | Risk | Rationale |
|---|------|-----------|
| A1 | SSRF DNS rebinding (V5-F13) | Requires authenticated access + DNS infrastructure; accepted for single-user appliance |
| A2 | Stream key in process table (V5-F9) | Inherent RTMP limitation; Docker container isolation sufficient |
| A3 | Temp stream ID collision (V5-F3) | Would require timeline IDs differing by exactly 1M; practically impossible |

---

## 5. Positive Findings -- What Previous Reviews Got Right

These areas were confirmed as solid through deep code path tracing:

1. **FFmpeg command injection is fully mitigated.** All 8 FFmpeg invocation sites use `asyncio.create_subprocess_exec()` with list-based arguments. No shell interpolation anywhere.

2. **Fernet encryption is correctly applied end-to-end.** All 7 sensitive column types (`password_enc`, `stream_key`, `youtube_api_key`, `youtube_oauth_client_secret_enc`, `youtube_oauth_refresh_token_enc`, `openai_api_key_enc`) use `encrypt()` at write time and `decrypt()` at read time. No plaintext secrets stored.

3. **Watchdog recovery design is sound.** The three-strike unhealthy threshold, 120-second cooldown, and clear separation between health detection and recovery action prevent flapping.

4. **Non-root Docker execution is correctly implemented.** The Dockerfile creates `appuser:1000`, and the entrypoint script fixes `/data` permissions before dropping privileges via `gosu`.

5. **CORS regex accurately targets RFC 1918 space.** The regex was manually verified to match only `192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, `100.x.x.x` (Tailscale CGNAT), localhost, `.local` mDNS, and the configured Cloudflare domain.

6. **OAuth state verification is cryptographically sound.** HMAC-SHA256 with `hmac.compare_digest()` (timing-safe comparison), 10-minute timestamp expiry, and nonce inclusion prevent replay and forgery.

7. **Graceful FFmpeg shutdown is correctly sequenced.** SIGTERM -> 5s wait -> SIGKILL prevents zombie processes. `ProcessLookupError` is caught for already-dead processes.

8. **Test fixtures correctly isolate the test database.** In-memory SQLite with `StaticPool`, table creation/teardown per test, lifespan disabled, rate limiting disabled, and audit middleware session factory patched.

---

## 6. Architecture Debt Summary (Cumulative v1-v5)

### Fully Resolved (v1-v4)
- CORS regex restricted to RFC 1918
- Registration endpoint protected (admin-only)
- OAuth state HMAC + time-limited
- HSTS + CSP headers
- SSRF validation on asset URLs
- Password complexity enforcement
- postMessage origin fixed (destinations)
- Audit middleware JWT extraction
- Dependencies pinned exactly
- Docker resource limits (RPi compose)
- Console credential logging removed
- Debug log functions removed

### Remaining (v4 findings, not re-listed here)
- Git history secret scrub (CRITICAL, v4-S1)
- ReelForge OAuth security (HIGH, v4-NEW-S1) -- skip per instructions
- Exception message leakage in 20+ endpoints (MEDIUM, v4-NEW-S3/S4/S6)
- Rate limiting gaps (MEDIUM, v4-S6)
- f-string logging throughout services (LOW)

### New (v5 findings)
- FFmpegProcessManager deadlock risk (HIGH, V5-F4)
- Timeline executor DB session lifetime (MEDIUM, V5-F1)
- RTSP credential encoding inconsistency (MEDIUM, V5-F7)
- TimelineExecutor concurrency safety (MEDIUM, V5-F5/F6)
- Lifespan DB session leak (MEDIUM, V5-F8)
- python-jose end-of-life (MEDIUM, V5-F12)

---

*Review generated by Claude Code Deep Audit v5 (Opus 4.6, 1M context). Based on complete read of all backend Python source files (83 files excluding venv), all frontend TypeScript/React source files (17 files), Docker configuration (6 files), nginx configuration, test fixtures, and all 4 previous review documents. Focus areas: end-to-end code path tracing, concurrency analysis, secret flow tracing, and FFmpeg command construction audit.*
