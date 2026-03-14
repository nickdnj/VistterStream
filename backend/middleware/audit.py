"""Audit logging middleware for state-changing operations.

Records user, action, timestamp, and IP for POST/PUT/DELETE requests.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from models.database import SessionLocal as _DefaultSessionLocal
from models.audit import AuditLog

# Module-level session factory — can be overridden in tests
_session_factory = _DefaultSessionLocal

logger = logging.getLogger(__name__)

# Only audit state-changing methods
_AUDITED_METHODS = {"POST", "PUT", "DELETE"}

# Skip high-frequency or non-sensitive paths
_SKIP_PREFIXES = (
    "/api/health",
    "/api/status",
    "/api/preview/playback-position",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _classify_action(method: str, path: str) -> str:
    """Derive a short action name from the HTTP method and path."""
    # Auth actions
    if "/auth/login" in path:
        return "auth.login"
    if "/auth/register" in path:
        return "auth.register"
    if "/auth/change-password" in path:
        return "auth.change_password"

    # Extract resource from path: /api/<resource>/...
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "api":
        resource = parts[1].replace("-", "_")
        verb = {"POST": "create", "PUT": "update", "DELETE": "delete"}.get(method, method.lower())
        # Special sub-actions
        if len(parts) >= 4:
            sub = parts[3].replace("-", "_")
            return f"{resource}.{sub}"
        return f"{resource}.{verb}"

    return f"{method.lower()} {path}"


def _extract_user_from_request(request: Request):
    """Try to extract user info from the request state (set by auth dependency)."""
    # FastAPI auth dependencies set request.state.user after authentication
    user = getattr(request.state, "user", None)
    if user:
        return getattr(user, "id", None), getattr(user, "username", None)
    return None, None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in _AUDITED_METHODS:
            return await call_next(request)

        if any(request.url.path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        response = await call_next(request)

        try:
            user_id, username = _extract_user_from_request(request)
            action = _classify_action(request.method, request.url.path)
            ip = request.client.host if request.client else None

            db = _session_factory()
            try:
                entry = AuditLog(
                    user_id=user_id,
                    username=username,
                    action=action,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    ip_address=ip,
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception:
            logger.debug("Audit log write failed", exc_info=True)

        return response
