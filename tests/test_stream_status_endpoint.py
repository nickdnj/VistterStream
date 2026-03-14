"""Tests for the stream status endpoint"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

for path in {ROOT_DIR, BACKEND_DIR}:
    if path not in sys.path:
        sys.path.insert(0, path)

from models.database import Base, Stream, Camera, get_db
from models.destination import StreamingDestination
from routers import streams as streams_router
from routers.auth import get_current_user


app = FastAPI()
app.include_router(streams_router.router, prefix="/api/streams")


TEST_DATABASE_URL = "sqlite:///./test_stream_status.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "test"}
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def cleanup_database_file():
    yield
    if os.path.exists("test_stream_status.db"):
        os.remove("test_stream_status.db")


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _create_destination(session, name: str = "Test Dest", platform: str = "youtube") -> StreamingDestination:
    dest = StreamingDestination(
        name=name,
        platform=platform,
        rtmp_url="rtmp://example.com/live",
        stream_key="abc123",
        is_active=True,
    )
    session.add(dest)
    session.commit()
    session.refresh(dest)
    return dest


def _create_camera(session, name: str = "Test Camera") -> Camera:
    camera = Camera(
        name=name,
        type="stationary",
        protocol="rtsp",
        address="192.168.1.100",
        username="admin",
        password_enc=None,
        port=554,
        stream_path="/stream1",
        is_active=True,
    )
    session.add(camera)
    session.commit()
    session.refresh(camera)
    return camera


def test_get_stream_status_running(client):
    session = TestingSessionLocal()
    camera = _create_camera(session)
    dest = _create_destination(session, name="YouTube", platform="youtube")

    started_at = datetime.utcnow() - timedelta(seconds=90)
    stream = Stream(
        name="Live Stream",
        camera_id=camera.id,
        destination_id=dest.id,
        resolution="1920x1080",
        bitrate="4500k",
        framerate=30,
        status="running",
        started_at=started_at,
        last_error=None,
    )
    session.add(stream)
    session.commit()
    session.refresh(stream)
    # Capture all values before closing session (avoids DetachedInstanceError)
    stream_id = stream.id
    camera_id = camera.id
    dest_id = dest.id
    session.close()

    response = client.get(f"/api/streams/{stream_id}/status")
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == stream_id
    assert payload["name"] == "Live Stream"
    assert payload["camera_id"] == camera_id
    assert payload["destination_id"] == dest_id
    assert payload["destination"]["platform"] == "youtube"
    assert payload["status"] == "running"
    assert payload["last_error"] is None
    assert payload["is_live"] is True

    expected_uptime = int((datetime.utcnow() - started_at).total_seconds())
    assert abs(payload["uptime_seconds"] - expected_uptime) <= 2


def test_get_stream_status_error(client):
    session = TestingSessionLocal()
    camera = _create_camera(session, name="Error Camera")
    dest = _create_destination(session, name="Twitch", platform="twitch")

    started_at = datetime.utcnow() - timedelta(minutes=10)
    stopped_at = started_at + timedelta(minutes=1)
    stream = Stream(
        name="Errored Stream",
        camera_id=camera.id,
        destination_id=dest.id,
        resolution="1280x720",
        bitrate="2500k",
        framerate=30,
        status="error",
        started_at=started_at,
        stopped_at=stopped_at,
        last_error="Authentication failed",
    )
    session.add(stream)
    session.commit()
    session.refresh(stream)
    # Capture all values before closing session (avoids DetachedInstanceError)
    stream_id = stream.id
    camera_id = camera.id
    dest_id = dest.id
    session.close()

    response = client.get(f"/api/streams/{stream_id}/status")
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == stream_id
    assert payload["name"] == "Errored Stream"
    assert payload["camera_id"] == camera_id
    assert payload["destination_id"] == dest_id
    assert payload["destination"]["platform"] == "twitch"
    assert payload["status"] == "error"
    assert payload["last_error"] == "Authentication failed"
    assert payload["is_live"] is False
    assert payload["uptime_seconds"] == int((stopped_at - started_at).total_seconds())
