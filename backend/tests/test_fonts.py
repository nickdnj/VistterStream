"""
Tests for font endpoints (/api/fonts/*).
"""

import io

from models.database import User
from models.font import Font
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="fontuser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "fontuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_font(db_session, family="TestFont", source="uploaded", weight="400"):
    """Insert a font record directly into the database."""
    font = Font(
        family=family,
        weight=weight,
        style="normal",
        source=source,
        file_path=f"/fonts/{source}/{family.lower()}.ttf",
        is_active=True,
    )
    db_session.add(font)
    db_session.commit()
    db_session.refresh(font)
    return font


# ------------------------------------------------------------------
# Listing tests
# ------------------------------------------------------------------

def test_list_fonts(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_font(db_session, family="FontA", source="system")
    _seed_font(db_session, family="FontB", source="uploaded")

    resp = client.get("/api/fonts", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_list_fonts_filter_by_source(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_font(db_session, family="SystemFont", source="system")
    _seed_font(db_session, family="UploadedFont", source="uploaded")

    resp = client.get("/api/fonts?source=system", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source"] == "system"


def test_list_fonts_invalid_source(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.get("/api/fonts?source=invalid", headers=headers)
    assert resp.status_code == 400


# ------------------------------------------------------------------
# Upload tests
# ------------------------------------------------------------------

def test_upload_valid_ttf(client, db_session):
    headers = _get_auth_header(client, db_session)

    # Valid TTF magic bytes + padding to look like a real font
    ttf_data = b"\x00\x01\x00\x00" + b"\x00" * 500
    file = io.BytesIO(ttf_data)

    resp = client.post(
        "/api/fonts/upload",
        files={"file": ("myfont.ttf", file, "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "uploaded"
    assert data["is_active"] is True


def test_upload_invalid_file(client, db_session):
    headers = _get_auth_header(client, db_session)

    # Invalid magic bytes (not TTF or OTF)
    bad_data = b"NOT_A_FONT_FILE" + b"\x00" * 100
    file = io.BytesIO(bad_data)

    resp = client.post(
        "/api/fonts/upload",
        files={"file": ("bad.ttf", file, "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_upload_empty_file(client, db_session):
    headers = _get_auth_header(client, db_session)

    file = io.BytesIO(b"")

    resp = client.post(
        "/api/fonts/upload",
        files={"file": ("empty.ttf", file, "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 400


# ------------------------------------------------------------------
# Google Fonts search
# ------------------------------------------------------------------

def test_search_google_fonts(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.get("/api/fonts/google", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "fonts" in data
    assert "count" in data
    assert data["count"] > 0


def test_search_google_fonts_with_query(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.get("/api/fonts/google?q=Roboto", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any("Roboto" in f["family"] for f in data["fonts"])


def test_search_google_fonts_no_results(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.get("/api/fonts/google?q=zzz_nonexistent_font_zzz", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ------------------------------------------------------------------
# Delete tests
# ------------------------------------------------------------------

def test_delete_uploaded_font(client, db_session):
    headers = _get_auth_header(client, db_session)
    font = _seed_font(db_session, family="DeleteMe", source="uploaded")

    resp = client.delete(f"/api/fonts/{font.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == font.id


def test_delete_system_font_returns_400(client, db_session):
    headers = _get_auth_header(client, db_session)
    font = _seed_font(db_session, family="SystemFont", source="system")

    resp = client.delete(f"/api/fonts/{font.id}", headers=headers)
    assert resp.status_code == 400


def test_delete_font_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.delete("/api/fonts/9999", headers=headers)
    assert resp.status_code == 404


def test_fonts_unauthenticated(client):
    resp = client.get("/api/fonts")
    assert resp.status_code == 401
