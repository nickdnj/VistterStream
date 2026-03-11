"""
Tests for camera endpoints (/api/cameras/*).
"""


def _get_auth_header(client):
    """Register + login a test user and return an Authorization header dict."""
    client.post(
        "/api/auth/register",
        json={"username": "camuser", "password": "testpass123"},
    )
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "camuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_cameras_unauthenticated(client):
    resp = client.get("/api/cameras")
    assert resp.status_code == 401


def test_get_cameras_authenticated(client):
    headers = _get_auth_header(client)
    resp = client.get("/api/cameras", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
