"""
Tests for the password recovery flow (/api/auth/forgot-password,
/api/auth/reset-password, /api/auth/recovery-email).
"""

from datetime import datetime, timedelta, timezone

from models.database import User
from routers.auth import get_password_hash


def _seed_admin(db_session, recovery_email=None):
    admin = User(
        username="admin",
        password_hash=get_password_hash("adminpass123"),
        recovery_email=recovery_email,
    )
    db_session.add(admin)
    db_session.commit()
    return admin


def _login(client, username="admin", password="adminpass123"):
    return client.post("/api/auth/login", data={"username": username, "password": password})


def _token(client, username="admin", password="adminpass123"):
    return _login(client, username, password).json()["access_token"]


# ------------------------------------------------------------------
# forgot-password
# ------------------------------------------------------------------


def test_forgot_password_unknown_user_is_generic(client, db_session):
    resp = client.post("/api/auth/forgot-password", json={"username": "nobody"})
    assert resp.status_code == 200
    assert "reset code" in resp.json()["message"].lower()


def test_forgot_password_without_recovery_email_sets_no_code(client, db_session):
    admin = _seed_admin(db_session, recovery_email=None)
    resp = client.post("/api/auth/forgot-password", json={"username": "admin"})
    assert resp.status_code == 200
    db_session.refresh(admin)
    assert admin.reset_code_hash is None


def test_forgot_password_with_recovery_email_sets_code(client, db_session):
    admin = _seed_admin(db_session, recovery_email="recover@example.com")
    resp = client.post("/api/auth/forgot-password", json={"username": "admin"})
    assert resp.status_code == 200
    db_session.refresh(admin)
    assert admin.reset_code_hash is not None
    assert admin.reset_code_expires is not None


# ------------------------------------------------------------------
# reset-password
# ------------------------------------------------------------------


def test_full_reset_flow_succeeds(client, db_session, monkeypatch):
    # Pin the generated code so we can submit it.
    monkeypatch.setattr("routers.auth.generate_reset_code", lambda *a, **k: "TESTCODE")
    _seed_admin(db_session, recovery_email="recover@example.com")

    assert client.post("/api/auth/forgot-password", json={"username": "admin"}).status_code == 200

    reset = client.post(
        "/api/auth/reset-password",
        json={"username": "admin", "code": "TESTCODE", "new_password": "NewPass123"},
    )
    assert reset.status_code == 200

    # New password works, old one no longer does.
    assert _login(client, password="NewPass123").status_code == 200
    assert _login(client, password="adminpass123").status_code == 401


def test_reset_code_is_case_insensitive(client, db_session, monkeypatch):
    monkeypatch.setattr("routers.auth.generate_reset_code", lambda *a, **k: "TESTCODE")
    _seed_admin(db_session, recovery_email="recover@example.com")
    client.post("/api/auth/forgot-password", json={"username": "admin"})

    reset = client.post(
        "/api/auth/reset-password",
        json={"username": "admin", "code": "testcode", "new_password": "NewPass123"},
    )
    assert reset.status_code == 200


def test_reset_password_wrong_code_rejected(client, db_session, monkeypatch):
    monkeypatch.setattr("routers.auth.generate_reset_code", lambda *a, **k: "TESTCODE")
    _seed_admin(db_session, recovery_email="recover@example.com")
    client.post("/api/auth/forgot-password", json={"username": "admin"})

    reset = client.post(
        "/api/auth/reset-password",
        json={"username": "admin", "code": "WRONGONE", "new_password": "NewPass123"},
    )
    assert reset.status_code == 400


def test_reset_password_expired_code_rejected(client, db_session):
    admin = _seed_admin(db_session, recovery_email="recover@example.com")
    admin.reset_code_hash = get_password_hash("TESTCODE")
    admin.reset_code_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    reset = client.post(
        "/api/auth/reset-password",
        json={"username": "admin", "code": "TESTCODE", "new_password": "NewPass123"},
    )
    assert reset.status_code == 400


def test_reset_password_no_pending_code_rejected(client, db_session):
    _seed_admin(db_session, recovery_email="recover@example.com")
    reset = client.post(
        "/api/auth/reset-password",
        json={"username": "admin", "code": "TESTCODE", "new_password": "NewPass123"},
    )
    assert reset.status_code == 400


def test_reset_code_cleared_after_use(client, db_session, monkeypatch):
    monkeypatch.setattr("routers.auth.generate_reset_code", lambda *a, **k: "TESTCODE")
    admin = _seed_admin(db_session, recovery_email="recover@example.com")
    client.post("/api/auth/forgot-password", json={"username": "admin"})
    client.post(
        "/api/auth/reset-password",
        json={"username": "admin", "code": "TESTCODE", "new_password": "NewPass123"},
    )
    db_session.refresh(admin)
    assert admin.reset_code_hash is None
    assert admin.reset_code_expires is None


# ------------------------------------------------------------------
# recovery-email management
# ------------------------------------------------------------------


def test_set_recovery_email_requires_auth(client, db_session):
    resp = client.post("/api/auth/recovery-email", json={"recovery_email": "x@y.com"})
    assert resp.status_code == 401


def test_set_and_read_recovery_email(client, db_session):
    _seed_admin(db_session)
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/auth/recovery-email",
        json={"recovery_email": "recover@example.com"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["recovery_email"] == "recover@example.com"

    me = client.get("/api/auth/me", headers=headers)
    assert me.json()["recovery_email"] == "recover@example.com"


def test_set_recovery_email_invalid_rejected(client, db_session):
    _seed_admin(db_session)
    token = _token(client)
    resp = client.post(
        "/api/auth/recovery-email",
        json={"recovery_email": "not-an-email"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_clear_recovery_email(client, db_session):
    _seed_admin(db_session, recovery_email="recover@example.com")
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/auth/recovery-email", json={"recovery_email": ""}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["recovery_email"] is None
