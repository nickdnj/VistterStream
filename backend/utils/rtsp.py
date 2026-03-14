"""Shared RTSP URL builder with proper credential encoding.

All services that construct RTSP URLs should use this utility to ensure
credentials containing special characters (e.g. @, :, /) are properly
URL-encoded.
"""

from urllib.parse import quote


def build_rtsp_url(
    address: str,
    port: int,
    username: str | None,
    password: str | None,
    stream_path: str,
) -> str:
    """Build an RTSP URL with properly URL-encoded credentials.

    Args:
        address: Camera IP or hostname.
        port: RTSP port (typically 554).
        username: Camera username (may be None for unauthenticated cameras).
        password: Camera password in plaintext (may be None).
        stream_path: Path portion of the RTSP URL (e.g. ``/stream1``).

    Returns:
        A fully-formed ``rtsp://`` URL.
    """
    if username and password:
        encoded_user = quote(username, safe="")
        encoded_pass = quote(password, safe="")
        return f"rtsp://{encoded_user}:{encoded_pass}@{address}:{port}{stream_path}"
    return f"rtsp://{address}:{port}{stream_path}"
