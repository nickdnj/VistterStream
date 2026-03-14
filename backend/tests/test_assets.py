"""
Tests for asset endpoints (/api/assets/*).
"""


from models.database import User
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="assetuser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "assetuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------
# CRUD Tests
# ------------------------------------------------------------------

def test_get_assets_unauthenticated(client):
    resp = client.get("/api/assets")
    assert resp.status_code == 401


def test_create_api_image_asset(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.post(
        "/api/assets",
        json={
            "name": "Weather Overlay",
            "type": "api_image",
            "api_url": "http://tempest.local:8036/api/overlay/conditions",
            "api_refresh_interval": 120,
            "width": 400,
            "height": 200,
            "position_x": 0.05,
            "position_y": 0.85,
            "opacity": 0.9,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    asset = resp.json()
    assert asset["name"] == "Weather Overlay"
    assert asset["type"] == "api_image"
    assert asset["api_url"] == "http://tempest.local:8036/api/overlay/conditions"


def test_create_static_image_asset(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.post(
        "/api/assets",
        json={
            "name": "Logo",
            "type": "static_image",
            "file_path": "/uploads/logo.png",
            "width": 200,
            "height": 100,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "static_image"


def test_create_api_image_without_url_fails(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.post(
        "/api/assets",
        json={
            "name": "Bad Asset",
            "type": "api_image",
            # missing api_url
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_list_assets(client, db_session):
    headers = _get_auth_header(client, db_session)
    # Create two assets
    client.post(
        "/api/assets",
        json={"name": "Asset 1", "type": "api_image", "api_url": "http://example.com/img1"},
        headers=headers,
    )
    client.post(
        "/api/assets",
        json={"name": "Asset 2", "type": "api_image", "api_url": "http://example.com/img2"},
        headers=headers,
    )

    resp = client.get("/api/assets", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_asset(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/assets",
        json={"name": "Original", "type": "api_image", "api_url": "http://example.com/img"},
        headers=headers,
    )
    asset_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/assets/{asset_id}",
        json={"name": "Renamed", "opacity": 0.5},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"
    assert resp.json()["opacity"] == 0.5


def test_delete_asset(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/assets",
        json={"name": "To Delete", "type": "api_image", "api_url": "http://example.com/del"},
        headers=headers,
    )
    asset_id = create_resp.json()["id"]

    resp = client.delete(f"/api/assets/{asset_id}", headers=headers)
    assert resp.status_code == 200

    # Soft delete — should return 404 for active asset queries
    resp = client.get(f"/api/assets/{asset_id}", headers=headers)
    assert resp.status_code == 404
