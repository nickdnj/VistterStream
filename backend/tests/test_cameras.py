"""
Tests for camera endpoints (/api/cameras/*).
"""


from models.database import User
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="camuser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "camuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_cameras_unauthenticated(client):
    resp = client.get("/api/cameras")
    assert resp.status_code == 401


def test_get_cameras_authenticated(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.get("/api/cameras", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
