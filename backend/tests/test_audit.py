"""
Tests for audit logging middleware.
"""

from models.audit import AuditLog
from models.database import User
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="audituser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "audituser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_audit_records_post(client, db_session):
    """POST requests should create an audit log entry."""
    _get_auth_header(client, db_session)  # This triggers POST /login

    entries = db_session.query(AuditLog).all()
    assert len(entries) >= 1  # at least login

    actions = [e.action for e in entries]
    assert "auth.login" in actions


def test_audit_skips_get(client, db_session):
    """GET requests should not create audit log entries."""
    headers = _get_auth_header(client, db_session)
    initial_count = db_session.query(AuditLog).count()

    client.get("/api/cameras", headers=headers)

    final_count = db_session.query(AuditLog).count()
    assert final_count == initial_count


def test_audit_records_ip(client, db_session):
    """Audit entries should contain the client IP."""
    _get_auth_header(client, db_session)

    entry = db_session.query(AuditLog).first()
    assert entry is not None
    assert entry.ip_address is not None


def test_audit_records_status_code(client, db_session):
    """Audit entries should contain the HTTP status code."""
    _get_auth_header(client, db_session)

    entry = db_session.query(AuditLog).first()
    assert entry is not None
    assert entry.status_code is not None
