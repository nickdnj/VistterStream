"""
Pytest fixtures for VistterStream backend tests.

Sets required environment variables, creates an in-memory SQLite database,
and provides a FastAPI TestClient wired to the test database.
"""

import os

# Environment variables MUST be set before any application imports because
# modules like routers/auth.py and utils/crypto.py read them at import time.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault(
    "ENCRYPTION_KEY",
    # A valid Fernet key (base64-encoded 32 bytes)
    "K9c_x2B0Gvt-ArEZK3JM4FxjYBhDA7eRmG1Ph8ILyIA=",
)
os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ["RATELIMIT_ENABLED"] = "false"  # Disable rate limiting in tests

import pytest
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models.database import Base, get_db
from main import app

# Disable rate limiting in tests — all requests come from "testclient" IP
# which hits the per-IP limits very quickly.
from routers import auth as _auth_module
_auth_module.limiter.enabled = False

# Import audit middleware for session patching (done per-test in db_session fixture)
from middleware import audit as _audit_module


# ---------------------------------------------------------------------------
# In-memory SQLite engine shared across a test session.
# StaticPool ensures every checkout returns the *same* connection, which is
# required for in-memory SQLite (otherwise each connection would get its own
# empty database).
# ---------------------------------------------------------------------------
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Replace the app lifespan so startup/shutdown services (camera health
# monitor, RTMP relay, scheduler, etc.) are never started in tests.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def _test_lifespan(app):
    yield

app.router.lifespan_context = _test_lifespan


@pytest.fixture(autouse=True)
def db_session():
    """
    Create all tables before each test and drop them afterwards so every
    test starts with a clean database.
    """
    Base.metadata.create_all(bind=engine)
    # Patch audit middleware to use test database
    _audit_module._session_factory = TestingSessionLocal
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        _audit_module._session_factory = TestingSessionLocal  # reset


@pytest.fixture()
def client(db_session):
    """
    FastAPI TestClient that uses the test database session instead of the
    production one.
    """

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
