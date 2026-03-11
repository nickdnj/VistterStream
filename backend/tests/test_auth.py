"""
Tests for authentication endpoints (/api/auth/*).
"""


def _register_user(client, username="testuser", password="testpass123"):
    """Helper: register a user and return the response."""
    return client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )


def _login_user(client, username="testuser", password="testpass123"):
    """Helper: login via OAuth2 form and return the response."""
    return client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_login_success(client):
    _register_user(client)
    resp = _login_user(client)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    _register_user(client)
    resp = _login_user(client, password="wrongpassword")
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_protected_endpoint_with_token(client):
    _register_user(client)
    login_resp = _login_user(client)
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "testuser"
