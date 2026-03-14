"""
Tests for stream endpoints (/api/streams/*).
"""

from models.database import Camera, User
from models.destination import StreamingDestination
from utils.crypto import encrypt
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="streamuser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "streamuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_camera_and_dest(db_session):
    """Insert a camera and destination for stream tests."""
    camera = Camera(
        name="Test Cam",
        type="stationary",
        protocol="rtsp",
        address="192.168.1.100",
        port=554,
        stream_path="/stream1",
    )
    db_session.add(camera)
    db_session.flush()

    dest = StreamingDestination(
        name="Test YT",
        platform="youtube",
        rtmp_url="rtmp://a.rtmp.youtube.com/live2",
        stream_key=encrypt("test-key"),
    )
    db_session.add(dest)
    db_session.flush()
    db_session.commit()
    return camera.id, dest.id


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_get_streams_unauthenticated(client):
    resp = client.get("/api/streams")
    assert resp.status_code == 401


def test_create_stream(client, db_session):
    headers = _get_auth_header(client, db_session)
    cam_id, dest_id = _seed_camera_and_dest(db_session)

    resp = client.post(
        "/api/streams",
        json={
            "name": "Test Stream",
            "camera_id": cam_id,
            "destination_id": dest_id,
            "resolution": "1920x1080",
            "bitrate": "2500k",
            "framerate": 30,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    stream = resp.json()
    assert stream["name"] == "Test Stream"
    assert stream["status"] == "stopped"


def test_list_streams(client, db_session):
    headers = _get_auth_header(client, db_session)
    cam_id, dest_id = _seed_camera_and_dest(db_session)

    client.post(
        "/api/streams",
        json={
            "name": "Stream 1",
            "camera_id": cam_id,
            "destination_id": dest_id,
        },
        headers=headers,
    )

    resp = client.get("/api/streams", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_stream_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.get("/api/streams/99999", headers=headers)
    assert resp.status_code == 404


def test_delete_stream(client, db_session):
    headers = _get_auth_header(client, db_session)
    cam_id, dest_id = _seed_camera_and_dest(db_session)

    create_resp = client.post(
        "/api/streams",
        json={
            "name": "To Delete",
            "camera_id": cam_id,
            "destination_id": dest_id,
        },
        headers=headers,
    )
    stream_id = create_resp.json()["id"]

    resp = client.delete(f"/api/streams/{stream_id}", headers=headers)
    assert resp.status_code == 200
