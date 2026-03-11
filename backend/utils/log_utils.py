"""Logging utilities for VistterStream."""

import re
from urllib.parse import urlparse, urlunparse


def redact_url(url: str) -> str:
    """Redact credentials from RTSP/HTTP/RTMP URLs.

    rtsp://user:pass@host:554/path -> rtsp://***:***@host:554/path
    """
    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            clean_netloc = f"***:***@{parsed.hostname}"
            if parsed.port:
                clean_netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=clean_netloc))
    except Exception:
        pass
    # Fallback regex for edge cases
    return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)
