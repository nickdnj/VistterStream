# VistterStream & TempestWeather - Deep Architectural & Security Review
**Date:** 2026-03-14 | **Reviewer:** Claude Code Security Audit v2

---

## Executive Summary

Both projects have been through a previous security pass (issues #22-31, #33-40), but significant vulnerabilities remain. VistterStream has **3 critical, 6 high, 7 medium** findings. TempestWeather has **2 critical, 4 high, 5 medium** findings. The most urgent issues are secrets in git history and SSRF vectors.

---

# PART 1: VistterStream

## CRITICAL

### 1. Secrets Exposed in Git History
**Location:** `.env` (committed to repo)
- JWT_SECRET_KEY, ENCRYPTION_KEY, CLOUDFLARE_TUNNEL_TOKEN all in git history
- Anyone with repo access can extract live secrets
- **Fix:** Rotate ALL secrets immediately, scrub git history with bfg-repo-cleaner, ensure `.env` is gitignored

### 2. SQL Injection Risk in start.py
**Location:** `backend/start.py:267`
- f-string SQL construction in migration functions
- Column names are currently controlled but pattern is dangerous if extended
- **Fix:** Use parameterized queries with explicit column mappings

### 3. OAuth State Timing
**Location:** `backend/routers/destinations.py:199-221`
- HMAC-SHA256 state is good but not time-limited
- code_verifier not cleared on failure
- **Fix:** Add expiry timestamp to state token

## HIGH

### 4. SSRF via Asset API URLs
**Location:** `backend/routers/assets.py:206-219`
- Authenticated users can set asset api_url to internal services (localhost, 169.254.169.254, Docker host)
- No URL validation beyond basic fetch
- **Fix:** Whitelist allowed URL prefixes, validate resolved IP is not private

### 5. Weak Rate Limiting on Auth
**Location:** `backend/routers/auth.py`
- 10 attempts per 15 minutes is too generous
- No account lockout, no CAPTCHA
- **Fix:** 3-5 attempts per 5 minutes with exponential backoff

### 6. Missing CSRF Protection
- No CSRF tokens on state-changing endpoints
- SameSite cookie attribute not set
- **Fix:** Add CSRF middleware, SameSite=Strict cookies

### 7. Insecure JWT Configuration
- 30-min token lifetime with no refresh tokens
- No token revocation on logout
- No JTI claim for tracking
- **Fix:** Add refresh token mechanism, token blacklist

### 8. XSS in OAuth Callback HTML
**Location:** `backend/routers/destinations.py:508-521`
- YouTube channel name rendered unescaped in HTML response
- **Fix:** `from html import escape; escape(channel_name)`

### 9. Encryption Key Fallback
**Location:** `backend/utils/crypto.py:31-40`
- Failed Fernet decrypt falls back to base64 decode (plaintext)
- **Fix:** Remove fallback, handle migration separately

## MEDIUM

### 10. Path Traversal in Asset Storage
- File extension from user filename not validated
- **Fix:** Whitelist extensions (.png, .jpg, .gif, .webp)

### 11. No Rate Limit on Asset Upload
- Disk exhaustion via repeated uploads
- **Fix:** Add per-user rate limit (10/hour)

### 12. FFmpeg Command Construction
- User-supplied RTSP/RTMP URLs in command args
- URL validation exists but FFmpeg URI parsing has history of issues
- **Fix:** Validate camera IPs against whitelist

### 13. No Input Validation on Timeline Variables
- FFmpeg filter expressions use numeric overlay coordinates without strict validation
- **Fix:** Validate all parameters are proper floats/ints

### 14. Audit Log Not Immutable
- Same database as app data, can be modified
- **Fix:** Append-only log file with signing

### 15. Missing Security Headers
- No CSP, X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy
- **Fix:** Add security headers middleware

### 16. Docker Secrets Handling
- Env vars visible via `docker inspect`
- **Fix:** Use Docker Secrets

## LOW

### 17. Weak Password Requirements (no minimum length)
### 18. Debug logging bypasses structured logger
### 19. No secrets rotation mechanism
### 20. Overly permissive CORS regex (any local IP)
### 21. SQLite has no auth/encryption

## INFO

### 22. Broad exception handling in background service init
### 23. Database session leaks in background tasks
### 24. ~58 tests but missing OAuth, SSRF, concurrent stream tests
### 25. Hardcoded paths and ports
### 26. Dependencies pinned but not security-scanned

---

# PART 2: TempestWeather

## CRITICAL

### 1. Secrets Exposed in .env
**Location:** `.env`
- TEMPEST_API_KEY and STATION_ID committed to repo
- Station ID reveals physical location
- **Fix:** Rotate API key at tempestwx.com, scrub git history

### 2. No SSL Certificate Verification on External APIs
**Location:** `tide_client.py`, `water_temp_client.py`, `astronomy_client.py`, `overlay_forecast.py`
- All `requests.get()` calls don't explicitly set `verify=True`
- MITM could inject false weather data
- **Fix:** Add explicit `verify=True` to all API calls

## HIGH

### 3. Path Traversal in Icon Loading
**Location:** `tempest_overlay_image.py:513-535`
- Icon names from Tempest API used directly in `os.path.join(ICONS_DIR, name)`
- No sanitization — `../../../etc/passwd` possible
- **Fix:** Regex validate icon names, verify resolved path stays in ICONS_DIR

### 4. No Validation on Station IDs (SSRF Vector)
**Location:** `flask_overlay_server.py:227-231`
- `/overlay/tides?station=` parameter used directly in NOAA API URL
- No numeric validation
- **Fix:** Regex validate `^\d{1,10}$`

### 5. Unbounded Image Cache (Memory Exhaustion)
**Location:** `tempest_overlay_image.py:63-65`
- Dict-based cache with no size limit
- Each unique (width, height, theme) combo cached (1-4MB each)
- On RPi with 1-2GB RAM, trivial to exhaust
- **Fix:** LRU cache with max_size=100

### 6. UDP Socket Never Closed
**Location:** `tempest_listener.py:80-93`
- Socket not in try/finally, leaked on OSError
- Eventually hits ulimit
- **Fix:** Wrap in try/finally, add timeout

## MEDIUM

### 7. No Rate Limiting
- Image rendering is CPU-intensive, no protection against flooding
- **Fix:** Flask-Limiter, 5 requests/minute per client

### 8. Flask Debug Mode Not Explicitly Disabled
- Default is False but should be explicit
- **Fix:** `app.run(debug=False)`

### 9. Location Parameter Not Validated
- User-supplied `?location=` rendered on image without length/char limits
- **Fix:** Limit to 100 chars, alphanumeric + basic punctuation

### 10. No Timeout on Image Generation
- Large dimensions can block CPU indefinitely
- **Fix:** Signal-based 5-second timeout

### 11. Broad CORS (`origins: "*"`)
- Any website can fetch weather data
- **Fix:** Whitelist known origins

## LOW

### 12. No Version Pinning in requirements.txt
### 13. No Explicit HTTP Status Codes on errors
### 14. Bare exception catching masks real errors
### 15. Docker runs as root, no healthcheck

## TESTING

### Zero tests exist for TempestWeather
- No test files found in the repository
- Recommend minimum: endpoint tests, rendering tests, API client mocking

---

# PRIORITY ACTION ITEMS

## Immediate (Today)

| # | Action | Project | Severity |
|---|--------|---------|----------|
| 1 | Rotate ALL secrets (.env) | Both | CRITICAL |
| 2 | Scrub .env from git history | Both | CRITICAL |
| 3 | Fix XSS in OAuth callback HTML | VistterStream | HIGH |
| 4 | Add path traversal protection to icon loading | TempestWeather | HIGH |
| 5 | Validate asset API URLs (SSRF) | VistterStream | HIGH |
| 6 | Add SSL verify=True to all API calls | TempestWeather | CRITICAL |

## This Week

| # | Action | Project | Severity |
|---|--------|---------|----------|
| 7 | Implement LRU image cache (bounded) | TempestWeather | HIGH |
| 8 | Add security headers middleware | VistterStream | MEDIUM |
| 9 | Remove encryption fallback to base64 | VistterStream | HIGH |
| 10 | Validate station IDs (numeric only) | TempestWeather | HIGH |
| 11 | Tighten rate limiting on auth (3/5min) | VistterStream | HIGH |
| 12 | Pin TempestWeather dependencies | TempestWeather | LOW |
| 13 | Add CSRF protection | VistterStream | HIGH |
| 14 | Fix UDP socket resource leak | TempestWeather | HIGH |

## Next Sprint

| # | Action | Project | Severity |
|---|--------|---------|----------|
| 15 | JWT refresh token mechanism | VistterStream | HIGH |
| 16 | Immutable audit logging | VistterStream | MEDIUM |
| 17 | Rate limiting on all endpoints | TempestWeather | MEDIUM |
| 18 | Upload rate limiting + quotas | VistterStream | MEDIUM |
| 19 | FFmpeg input validation hardening | VistterStream | MEDIUM |
| 20 | TempestWeather test suite | TempestWeather | INFO |
| 21 | Docker non-root + healthcheck | TempestWeather | LOW |
| 22 | pip-audit / dependabot setup | Both | LOW |

---

# SCORECARD

## VistterStream

| Category | Grade | Notes |
|----------|-------|-------|
| **Architecture** | B- | Good modular design, clean separation. Background task init could be more robust. |
| **Security** | C | Previous hardening pass helped but SSRF, CSRF, XSS remain. Secrets in git history. |
| **Code Quality** | B | Structured logging, typed models, consistent patterns. Some debug prints remain. |
| **Testing** | C+ | 58 tests but missing critical paths (OAuth, SSRF, concurrent streams). |
| **Deployment** | B | Multi-stage Docker, VA-API GPU, Cloudflare tunnel. Secrets handling needs Docker Secrets. |
| **Overall** | C+ | Functional and improving. Needs another security pass focused on input validation. |

## TempestWeather

| Category | Grade | Notes |
|----------|-------|-------|
| **Architecture** | B | Clean modular design, good separation of concerns. Simple and effective. |
| **Security** | D+ | No auth, no rate limiting, unbounded caches, path traversal, no SSL verification. |
| **Code Quality** | B- | Good docstrings, some type hints. Bare exceptions mask errors. |
| **Testing** | F | Zero tests. |
| **Deployment** | C | Works in Docker but runs as root, no healthcheck, no resource limits. |
| **Overall** | C- | Functional for local use but not hardened for internet exposure. |
