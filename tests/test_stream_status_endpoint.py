"""Tests for the stream status endpoint"""

import os
import sys
from datetime import datetime, timedelta

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
from routers import streams as streams_router


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

    started_at = datetime.utcnow() - timedelta(seconds=90)
    stream = Stream(
        name="Live Stream",
        camera_id=camera.id,
        destination="youtube",
        stream_key="abc123",
        rtmp_url="rtmp://youtube.com/live",
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
    session.close()

    response = client.get(f"/api/streams/{stream.id}/status")
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == stream.id
    assert payload["name"] == stream.name
    assert payload["camera_id"] == stream.camera_id
    assert payload["destination"] == stream.destination
    assert payload["status"] == stream.status
    assert payload["last_error"] is None
    assert payload["started_at"] == stream.started_at.isoformat()
    assert payload["is_live"] is True

    expected_uptime = int((datetime.utcnow() - started_at).total_seconds())
    assert abs(payload["uptime_seconds"] - expected_uptime) <= 2


def test_get_stream_status_error(client):
    session = TestingSessionLocal()
    camera = _create_camera(session, name="Error Camera")

    started_at = datetime.utcnow() - timedelta(minutes=10)
    stopped_at = started_at + timedelta(minutes=1)
    stream = Stream(
        name="Errored Stream",
        camera_id=camera.id,
        destination="twitch",
        stream_key="xyz789",
        rtmp_url="rtmp://twitch.tv/live",
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
    session.close()

    response = client.get(f"/api/streams/{stream.id}/status")
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == stream.id
    assert payload["name"] == stream.name
    assert payload["camera_id"] == stream.camera_id
    assert payload["destination"] == stream.destination
    assert payload["status"] == stream.status
    assert payload["last_error"] == stream.last_error
    assert payload["started_at"] == stream.started_at.isoformat()
    assert payload["stopped_at"] == stream.stopped_at.isoformat()
    assert payload["is_live"] is False
    assert payload["uptime_seconds"] == int((stopped_at - started_at).total_seconds())
