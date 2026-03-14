"""
Tests for authentication endpoints (/api/auth/*).
"""

import pytest
from models.database import User
from routers.auth import get_password_hash


def _seed_admin(db_session):
    """Directly seed an 'admin' user into the database."""
    admin = User(
        username="admin",
        password_hash=get_password_hash("adminpass123"),
    )
    db_session.add(admin)
    db_session.commit()
    return admin


def _seed_user(db_session, username="testuser", password="testpass123"):
    """Directly seed a regular user into the database."""
    user = User(
        username=username,
        password_hash=get_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _login_user(client, username="testuser", password="testpass123"):
    """Helper: login via OAuth2 form and return the response."""
    return client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )


def _get_token(client, username, password):
    """Login and return the bearer token string."""
    resp = _login_user(client, username=username, password=password)
    return resp.json()["access_token"]


def _auth_header(token):
    """Build an Authorization header dict from a token."""
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# Login Tests
# ------------------------------------------------------------------


def test_login_success(client, db_session):
    _seed_user(db_session)
    resp = _login_user(client)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, db_session):
    _seed_user(db_session)
    resp = _login_user(client, password="wrongpassword")
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_protected_endpoint_with_token(client, db_session):
    _seed_user(db_session)
    token = _get_token(client, "testuser", "testpass123")

    resp = client.get(
        "/api/auth/me",
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "testuser"


# ------------------------------------------------------------------
# Registration protection tests
#
# The /register endpoint requires authentication and is restricted
# to the "admin" user (hardcoded username check).
# ------------------------------------------------------------------


def test_register_without_auth_returns_401(client):
    """POST /api/auth/register without auth should return 401."""
    resp = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "newpass123"},
    )
    assert resp.status_code == 401


def test_register_non_admin_returns_403(client, db_session):
    """POST /api/auth/register with a non-admin user should return 403."""
    _seed_user(db_session, username="regularuser", password="regularpass123")
    token = _get_token(client, "regularuser", "regularpass123")

    resp = client.post(
        "/api/auth/register",
        json={"username": "another_user", "password": "anotherpass123"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 403


def test_register_admin_succeeds(client, db_session):
    """POST /api/auth/register with the admin user should succeed."""
    _seed_admin(db_session)
    token = _get_token(client, "admin", "adminpass123")

    resp = client.post(
        "/api/auth/register",
        json={"username": "new_user_by_admin", "password": "newpass123"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "new_user_by_admin"


def test_register_duplicate_username_returns_400(client, db_session):
    """Registering an existing username should return 400."""
    _seed_admin(db_session)
    _seed_user(db_session, username="existing", password="existpass123")
    token = _get_token(client, "admin", "adminpass123")

    resp = client.post(
        "/api/auth/register",
        json={"username": "existing", "password": "newpass456"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


# ------------------------------------------------------------------
# Password complexity tests
# ------------------------------------------------------------------


def test_password_too_short_rejected(client, db_session):
    """Password shorter than 8 characters should be rejected."""
    _seed_admin(db_session)
    token = _get_token(client, "admin", "adminpass123")
    resp = client.post(
        "/api/auth/register",
        json={"username": "shortpw", "password": "Ab1cde"},
        headers=_auth_header(token),
    )
    assert resp.status_code in (400, 422)


def test_password_without_digits_rejected(client, db_session):
    """Password without any digits should be rejected."""
    _seed_admin(db_session)
    token = _get_token(client, "admin", "adminpass123")
    resp = client.post(
        "/api/auth/register",
        json={"username": "nodigits", "password": "abcdefghi"},
        headers=_auth_header(token),
    )
    assert resp.status_code in (400, 422)


def test_password_without_letters_rejected(client, db_session):
    """Password without any letters should be rejected."""
    _seed_admin(db_session)
    token = _get_token(client, "admin", "adminpass123")
    resp = client.post(
        "/api/auth/register",
        json={"username": "noletters", "password": "12345678"},
        headers=_auth_header(token),
    )
    assert resp.status_code in (400, 422)


def test_valid_complex_password_accepted(client, db_session):
    """A password with letters + digits and 8+ chars should be accepted."""
    _seed_admin(db_session)
    token = _get_token(client, "admin", "adminpass123")
    resp = client.post(
        "/api/auth/register",
        json={"username": "goodpw", "password": "SecurePass1"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "goodpw"
