"""
Tests for timeline endpoints (/api/timelines/*).
"""


from models.database import User
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="tluser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "tluser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_timeline(client, headers, **overrides):
    """Create a timeline and return the response."""
    data = {
        "name": "Test Timeline",
        "description": "A test timeline",
        "duration": 120.0,
        "fps": 30,
        "resolution": "1920x1080",
        "loop": True,
        "tracks": [],
        **overrides,
    }
    return client.post("/api/timelines", json=data, headers=headers)


# ------------------------------------------------------------------
# CRUD Tests
# ------------------------------------------------------------------

def test_get_timelines_unauthenticated(client):
    resp = client.get("/api/timelines")
    assert resp.status_code == 401


def test_create_and_list_timelines(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = _create_timeline(client, headers)
    assert create_resp.status_code == 200
    tl = create_resp.json()
    assert tl["name"] == "Test Timeline"
    assert tl["duration"] == 120.0
    assert tl["loop"] is True

    list_resp = client.get("/api/timelines", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_get_timeline_by_id(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = _create_timeline(client, headers)
    tl_id = create_resp.json()["id"]

    resp = client.get(f"/api/timelines/{tl_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == tl_id


def test_update_timeline(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = _create_timeline(client, headers)
    tl_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/timelines/{tl_id}",
        json={"name": "Updated Timeline", "duration": 180.0},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Timeline"


def test_delete_timeline(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = _create_timeline(client, headers)
    tl_id = create_resp.json()["id"]

    resp = client.delete(f"/api/timelines/{tl_id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/timelines/{tl_id}", headers=headers)
    assert resp.status_code == 404


def test_timeline_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.get("/api/timelines/99999", headers=headers)
    assert resp.status_code == 404


# ------------------------------------------------------------------
# Timeline with Tracks and Cues
# ------------------------------------------------------------------

def test_create_timeline_with_tracks(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = _create_timeline(
        client,
        headers,
        tracks=[
            {
                "track_type": "video",
                "layer": 0,
                "is_enabled": True,
                "cues": [
                    {
                        "cue_order": 0,
                        "start_time": 0.0,
                        "duration": 60.0,
                        "action_type": "camera_view",
                        "action_params": {"camera_id": 1, "preset_id": 1},
                    },
                    {
                        "cue_order": 1,
                        "start_time": 60.0,
                        "duration": 60.0,
                        "action_type": "camera_view",
                        "action_params": {"camera_id": 1, "preset_id": 2},
                    },
                ],
            },
        ],
    )
    assert resp.status_code == 200
    tl = resp.json()
    assert len(tl["tracks"]) == 1
    assert len(tl["tracks"][0]["cues"]) == 2
    assert tl["tracks"][0]["cues"][0]["action_type"] == "camera_view"


# ------------------------------------------------------------------
# Copy Timeline
# ------------------------------------------------------------------

def test_copy_timeline(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = _create_timeline(
        client,
        headers,
        tracks=[
            {
                "track_type": "video",
                "layer": 0,
                "is_enabled": True,
                "cues": [
                    {
                        "cue_order": 0,
                        "start_time": 0.0,
                        "duration": 60.0,
                        "action_type": "camera_view",
                        "action_params": {"camera_id": 1},
                    },
                ],
            },
        ],
    )
    tl_id = create_resp.json()["id"]

    copy_resp = client.post(f"/api/timelines/{tl_id}/duplicate", headers=headers)
    assert copy_resp.status_code == 200
    copy = copy_resp.json()
    assert copy["id"] != tl_id
    assert "Copy" in copy["name"]
    assert len(copy["tracks"]) == 1


# ------------------------------------------------------------------
# Broadcast Metadata
# ------------------------------------------------------------------

def test_timeline_broadcast_metadata(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = _create_timeline(
        client,
        headers,
        broadcast_title="Live from the Marina",
        broadcast_description="24/7 marina cam",
        broadcast_tags="marina,live,webcam",
        broadcast_privacy="public",
        broadcast_category_id="19",
    )
    assert resp.status_code == 200
    tl = resp.json()
    assert tl["broadcast_title"] == "Live from the Marina"
    assert tl["broadcast_privacy"] == "public"
