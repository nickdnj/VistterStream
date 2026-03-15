"""
Tests for asset endpoint extensions: ?type= and ?search= query params,
plus canvas_composite asset type support.
"""

import json

from models.database import User, Asset
from models.template import OverlayTemplate, TemplateInstance
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="assetext_user",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "assetext_user", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_assets(client, headers):
    """Create a variety of assets for filtering tests. Returns list of created assets."""
    assets = [
        {
            "name": "Station Logo",
            "type": "static_image",
            "file_path": "/uploads/logo.png",
        },
        {
            "name": "Weather Overlay",
            "type": "api_image",
            "api_url": "http://tempest.local:8036/api/overlay/conditions",
        },
        {
            "name": "Marine Forecast",
            "type": "api_image",
            "api_url": "http://tempest.local:8036/api/overlay/marine",
        },
        {
            "name": "Sponsor Banner",
            "type": "static_image",
            "file_path": "/uploads/sponsor.png",
        },
    ]
    created = []
    for asset_data in assets:
        resp = client.post("/api/assets", json=asset_data, headers=headers)
        assert resp.status_code == 200
        created.append(resp.json())
    return created


def _seed_template_asset(db_session):
    """Create an asset linked to a template instance (for type=template filter)."""
    # Create a minimal template
    template = OverlayTemplate(
        name="Filter Test Template",
        category="weather",
        description="For testing",
        config_schema=json.dumps({"fields": []}),
        default_config=json.dumps({}),
        is_active=True,
    )
    db_session.add(template)
    db_session.flush()

    # Create the asset first
    asset = Asset(
        name="Template Weather Asset",
        type="api_image",
        api_url="http://example.com/weather",
        is_active=True,
    )
    db_session.add(asset)
    db_session.flush()

    # Create the template instance
    instance = TemplateInstance(
        template_id=template.id,
        config_values=json.dumps({}),
        asset_id=asset.id,
    )
    db_session.add(instance)
    db_session.flush()

    # Link asset back to instance
    asset.template_instance_id = instance.id
    db_session.commit()
    db_session.refresh(asset)
    return asset


# ------------------------------------------------------------------
# Type filter tests
# ------------------------------------------------------------------

def test_filter_assets_by_type_static_image(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    resp = client.get("/api/assets?type=static_image", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(a["type"] == "static_image" for a in data)


def test_filter_assets_by_type_api_image(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    resp = client.get("/api/assets?type=api_image", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(a["type"] == "api_image" for a in data)


def test_filter_assets_by_type_template(client, db_session):
    """The 'template' type is a virtual filter matching assets with template_instance_id."""
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)  # Regular assets (no template link)
    _seed_template_asset(db_session)  # Asset linked to template instance

    resp = client.get("/api/assets?type=template", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["template_instance_id"] is not None
    assert data[0]["name"] == "Template Weather Asset"


# ------------------------------------------------------------------
# Search filter tests
# ------------------------------------------------------------------

def test_search_assets_by_name(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    resp = client.get("/api/assets?search=weather", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "Weather" in data[0]["name"]


def test_search_assets_case_insensitive(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    resp = client.get("/api/assets?search=LOGO", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "Logo" in data[0]["name"]


def test_search_assets_no_results(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    resp = client.get("/api/assets?search=nonexistent_xyz", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ------------------------------------------------------------------
# Combined filter tests
# ------------------------------------------------------------------

def test_filter_type_and_search_combined(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    # Only api_image assets with "weather" in the name
    resp = client.get("/api/assets?type=api_image&search=weather", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "api_image"
    assert "Weather" in data[0]["name"]


def test_filter_type_and_search_no_overlap(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    # static_image + "weather" should return nothing (Weather Overlay is api_image)
    resp = client.get("/api/assets?type=static_image&search=weather", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ------------------------------------------------------------------
# Canvas composite asset creation
# ------------------------------------------------------------------

def test_create_canvas_composite_asset(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.post(
        "/api/assets",
        json={
            "name": "Custom Composite",
            "type": "canvas_composite",
            "width": 800,
            "height": 600,
            "position_x": 0.5,
            "position_y": 0.5,
            "opacity": 0.95,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "canvas_composite"
    assert data["name"] == "Custom Composite"


def test_no_filter_returns_all(client, db_session):
    """Verify that omitting type and search returns all assets."""
    headers = _get_auth_header(client, db_session)
    _seed_assets(client, headers)

    resp = client.get("/api/assets", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 4
