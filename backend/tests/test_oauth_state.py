"""
Tests for OAuth state CSRF protection (Issue #34).
"""

import os

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
