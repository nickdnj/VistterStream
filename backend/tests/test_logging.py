"""
Tests for structured logging with secret redaction (Issue #37).
"""

import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("ENCRYPTION_KEY", "K9c_x2B0Gvt-ArEZK3JM4FxjYBhDA7eRmG1Ph8ILyIA=")

from utils.logging_config import _redact, JSONFormatter, SecretRedactionFilter
import json
import logging


def test_redact_rtsp_password():
    msg = "Connecting to rtsp://admin:secretpass@192.168.1.10:554/stream"
    result = _redact(msg)
    assert "secretpass" not in result
    assert "****" in result
    assert "192.168.1.10" in result


def test_redact_password_param():
    msg = "password=sOKDKxsV&channel=0"
    result = _redact(msg)
    assert "sOKDKxsV" not in result
    assert "****" in result


def test_redact_api_key():
    msg = "api_key=AIzaSyB123456789"
    result = _redact(msg)
    assert "AIzaSyB123456789" not in result


def test_redact_bearer_token():
    msg = "Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature"
    result = _redact(msg)
    assert "eyJhbGciOiJIUzI1NiJ9" not in result


def test_redact_fernet_token():
    msg = "Key is gAAAAABhQ2xhcmVhZGVyVGVzdFRva2VuVGhhdElzTG9uZw=="
    result = _redact(msg)
    assert "gAAAAABhQ2xhcmVhZGVyVGVzdFRva2VuVGhhdElzTG9uZw==" not in result


def test_safe_message_unchanged():
    msg = "Starting stream on port 1935"
    assert _redact(msg) == msg


def test_json_formatter_output():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Test message", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed


def test_redaction_filter():
    filt = SecretRedactionFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="password=secret123", args=(), exc_info=None,
    )
    filt.filter(record)
    assert "secret123" not in record.msg
