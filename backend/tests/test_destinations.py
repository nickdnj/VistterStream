"""
Tests for destination endpoints (/api/destinations/*).
"""

from utils.crypto import encrypt


def _get_auth_header(client):
    """Register + login a test user and return an Authorization header dict."""
    client.post(
        "/api/auth/register",
        json={"username": "destuser", "password": "testpass123"},
    )
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "destuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_destination(client, headers, **overrides):
    """Create a destination and return the response."""
    data = {
        "name": "Test YouTube",
        "platform": "youtube",
        "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
        "stream_key": "test-key-123",
        **overrides,
    }
    return client.post("/api/destinations", json=data, headers=headers)


# ------------------------------------------------------------------
# CRUD Tests
# ------------------------------------------------------------------

def test_get_destinations_unauthenticated(client):
    resp = client.get("/api/destinations")
    assert resp.status_code == 401


def test_create_and_list_destinations(client):
    headers = _get_auth_header(client)
    create_resp = _create_destination(client, headers)
    assert create_resp.status_code == 200
    dest = create_resp.json()
    assert dest["name"] == "Test YouTube"
    assert dest["platform"] == "youtube"
    # stream_key should be masked
    assert dest["stream_key"] == "••••••••"

    # List
    list_resp = client.get("/api/destinations", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_get_destination_by_id(client):
    headers = _get_auth_header(client)
    create_resp = _create_destination(client, headers)
    dest_id = create_resp.json()["id"]

    resp = client.get(f"/api/destinations/{dest_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == dest_id


def test_update_destination(client):
    headers = _get_auth_header(client)
    create_resp = _create_destination(client, headers)
    dest_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/destinations/{dest_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_delete_destination(client):
    headers = _get_auth_header(client)
    create_resp = _create_destination(client, headers)
    dest_id = create_resp.json()["id"]

    resp = client.delete(f"/api/destinations/{dest_id}", headers=headers)
    assert resp.status_code == 200

    # Should be gone
    resp = client.get(f"/api/destinations/{dest_id}", headers=headers)
    assert resp.status_code == 404


def test_update_with_mask_does_not_overwrite(client):
    """Sending the masked placeholder should not overwrite the real key."""
    headers = _get_auth_header(client)
    create_resp = _create_destination(client, headers)
    dest_id = create_resp.json()["id"]

    # Update with masked value — should be ignored
    resp = client.put(
        f"/api/destinations/{dest_id}",
        json={"stream_key": "••••••••"},
        headers=headers,
    )
    assert resp.status_code == 200
    # Key should still be masked (not overwritten with dots)
    assert resp.json()["stream_key"] == "••••••••"


# ------------------------------------------------------------------
# URL Validation Tests (Issue #39)
# ------------------------------------------------------------------

def test_reject_invalid_rtmp_scheme(client):
    headers = _get_auth_header(client)
    resp = _create_destination(client, headers, rtmp_url="file:///etc/passwd")
    assert resp.status_code == 422


def test_reject_invalid_youtube_watch_url(client):
    headers = _get_auth_header(client)
    resp = _create_destination(
        client, headers,
        youtube_watch_url="javascript:alert(1)"
    )
    assert resp.status_code == 422


def test_accept_valid_rtmps_url(client):
    headers = _get_auth_header(client)
    resp = _create_destination(
        client, headers,
        rtmp_url="rtmps://live-api-s.facebook.com:443/rtmp",
    )
    assert resp.status_code == 200


def test_accept_valid_youtube_watch_url(client):
    headers = _get_auth_header(client)
    resp = _create_destination(
        client, headers,
        youtube_watch_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    assert resp.status_code == 200


def test_accept_empty_rtmp_url(client):
    """OAuth destinations can have empty rtmp_url."""
    headers = _get_auth_header(client)
    resp = _create_destination(client, headers, platform="youtube_oauth", rtmp_url="")
    assert resp.status_code == 200


# ------------------------------------------------------------------
# Platform Presets
# ------------------------------------------------------------------

def test_get_platform_presets(client):
    headers = _get_auth_header(client)
    resp = client.get("/api/destinations/presets", headers=headers)
    assert resp.status_code == 200
    presets = resp.json()
    assert "youtube" in presets
    assert "facebook" in presets
