"""Structured JSON logging with secret redaction.

Provides a JSON log formatter and a filter that masks sensitive data
(passwords in RTSP URLs, API keys, tokens) before they reach the log output.

Usage:
    from utils.logging_config import configure_logging
    configure_logging()  # Call once at startup
"""

import json
import logging
import os
import re
from datetime import datetime, timezone


# Patterns to redact in log messages
_REDACT_PATTERNS = [
    # RTSP URLs with embedded credentials: rtsp://user:pass@host
    (re.compile(r"(rtsp://[^:]+:)[^@]+(@)"), r"\1****\2"),
    # Generic password= in query strings or config
    (re.compile(r"(password[=:]\s*)([^\s&,;]+)", re.IGNORECASE), r"\1****"),
    # API keys (common patterns)
    (re.compile(r"(api[_-]?key[=:]\s*)([^\s&,;]+)", re.IGNORECASE), r"\1****"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)\S+", re.IGNORECASE), r"\1****"),
    # Fernet tokens (gAAAAA...)
    (re.compile(r"gAAAAA[A-Za-z0-9_-]{20,}"), "****"),
    # RTMP/RTMPS stream keys: rtmp(s)://host/app/<stream_key>
    (re.compile(r'(rtmps?://[^/]+/[^/]+/)([^\s"\']+)'), r"\1****"),
]


def _redact(message: str) -> str:
    """Apply all redaction patterns to a log message."""
    for pattern, replacement in _REDACT_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


class SecretRedactionFilter(logging.Filter):
    """Log filter that redacts sensitive data from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _redact(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(_redact(str(a)) if isinstance(a, str) else a for a in record.args)
        return True


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def configure_logging() -> None:
    """Configure structured logging for the application.

    Reads LOG_FORMAT (json|text, default: json) and LOG_LEVEL (default: INFO)
    from environment variables.
    """
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove any existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

    # Add secret redaction filter
    handler.addFilter(SecretRedactionFilter())
    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
