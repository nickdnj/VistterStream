"""
Tests for OAuth state CSRF protection (Issue #34).
"""

import os
import time
from unittest.mock import patch

import pytest
from fastapi import HTTPException

# Ensure JWT_SECRET_KEY is set before importing
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-only")

from routers.destinations import _generate_oauth_state, _verify_oauth_state


def test_generate_and_verify_state():
    """State token should round-trip correctly."""
    state = _generate_oauth_state(42)
    result = _verify_oauth_state(state)
    assert result == 42


def test_verify_rejects_tampered_state():
    """Tampered state should be rejected."""
    state = _generate_oauth_state(42)
    # Tamper with the nonce
    parts = state.split(":")
    parts[1] = "tampered_nonce"
    tampered = ":".join(parts)
    assert _verify_oauth_state(tampered) is None


def test_verify_rejects_wrong_signature():
    """Wrong signature should be rejected."""
    state = _generate_oauth_state(42)
    parts = state.split(":")
    parts[2] = "0" * 64  # fake signature
    bad_sig = ":".join(parts)
    assert _verify_oauth_state(bad_sig) is None


def test_verify_rejects_plain_int():
    """Plain integer (old format) should be rejected."""
    assert _verify_oauth_state("42") is None


def test_verify_rejects_empty_string():
    assert _verify_oauth_state("") is None


def test_state_includes_destination_id():
    """The destination ID should be recoverable from the state."""
    for dest_id in [1, 100, 9999]:
        state = _generate_oauth_state(dest_id)
        assert _verify_oauth_state(state) == dest_id


def test_states_are_unique():
    """Each generated state should be unique (nonce)."""
    states = {_generate_oauth_state(1) for _ in range(10)}
    assert len(states) == 10


# ------------------------------------------------------------------
# Timestamp-based expiry tests (pending feature — Issue #34 follow-up)
#
# The current _generate_oauth_state / _verify_oauth_state do not embed
# a timestamp.  These tests are written against the expected behaviour
# once the timestamp feature is merged:
#   - State tokens include a Unix timestamp.
#   - _verify_oauth_state rejects tokens older than 10 minutes.
# ------------------------------------------------------------------

def _has_timestamp_support() -> bool:
    """Check whether the current implementation supports timestamps.

    The timestamp feature will change the state format from
    ``dest_id:nonce:sig`` (3 parts) to ``dest_id:nonce:timestamp:sig``
    (4 parts).
    """
    state = _generate_oauth_state(1)
    return len(state.split(":")) >= 4


_skip_no_timestamp = pytest.mark.skipif(
    not _has_timestamp_support(),
    reason="Pending OAuth state timestamp feature (state format is still 3-part)",
)


@_skip_no_timestamp
def test_fresh_state_is_valid():
    """A freshly generated state should verify successfully."""
    state = _generate_oauth_state(99)
    assert _verify_oauth_state(state) == 99


@_skip_no_timestamp
def test_expired_state_rejected():
    """A state token older than 10 minutes should be rejected."""
    # Generate a state, then pretend 11 minutes have passed.
    real_time = time.time

    # Step 1: generate at "now"
    state = _generate_oauth_state(7)

    # Step 2: verify at "now + 11 minutes" -- the implementation raises
    # HTTPException(400) for expired states rather than returning None.
    with patch("routers.destinations.time.time", return_value=real_time() + 660):
        with pytest.raises(HTTPException) as exc_info:
            _verify_oauth_state(state)
        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()


@_skip_no_timestamp
def test_state_just_within_window():
    """A state token just under 10 minutes old should still be valid."""
    real_time = time.time

    state = _generate_oauth_state(7)

    # Verify at "now + 9 minutes 59 seconds"
    with patch("routers.destinations.time.time", return_value=real_time() + 599):
        result = _verify_oauth_state(state)
    assert result == 7, "State within 10-min window should still be valid"
