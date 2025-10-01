import base64
import os
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from backend.models.database import Base, Camera
from backend.services import camera_service


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _MockResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.headers = {}
        self.content = b""


@pytest.mark.anyio("asyncio")
async def test_check_camera_status_quick_probe_success(monkeypatch, db_session):
    camera = Camera(
        name="Test Cam",
        type="stationary",
        protocol="rtsp",
        address="127.0.0.1",
        username="user",
        password_enc=base64.b64encode(b"pass").decode(),
        port=554,
        stream_path="/stream",
        snapshot_url="http://example.com/snapshot.jpg",
        last_seen=datetime.utcnow() - timedelta(minutes=10),
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    calls = []

    class _MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url, **kwargs):
            calls.append(("HEAD", url))
            return _MockResponse(200)

    monkeypatch.setattr(camera_service.httpx, "AsyncClient", _MockAsyncClient)

    service = camera_service.CameraService(db_session)
    result = await service._check_camera_status(camera)

    assert result["status"] == "online"
    assert calls == [("HEAD", camera.snapshot_url)]

    db_session.refresh(camera)
    assert camera.last_seen > datetime.utcnow() - timedelta(minutes=1)


@pytest.mark.anyio("asyncio")
async def test_check_camera_status_quick_probe_failure(monkeypatch, db_session):
    camera = Camera(
        name="Test Cam",
        type="stationary",
        protocol="rtsp",
        address="127.0.0.1",
        port=554,
        stream_path="/stream",
        snapshot_url="http://example.com/snapshot.jpg",
        last_seen=datetime.utcnow() - timedelta(minutes=10),
    )
    db_session.add(camera)
    db_session.commit()
    db_session.refresh(camera)

    class _MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url, **kwargs):
            request = camera_service.httpx.Request("HEAD", url)
            raise camera_service.httpx.RequestError("boom", request=request)

    monkeypatch.setattr(camera_service.httpx, "AsyncClient", _MockAsyncClient)

    service = camera_service.CameraService(db_session)
    result = await service._check_camera_status(camera)

    assert result["status"] == "offline"
    assert "boom" in result["error"]

    db_session.refresh(camera)
    # last_seen should remain the stale timestamp
    assert camera.last_seen < datetime.utcnow() - timedelta(minutes=5)
