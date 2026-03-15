"""
Tests for template endpoints (/api/templates/*).
"""

import json

from models.database import User, Asset
from models.template import OverlayTemplate, TemplateInstance
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="templateuser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "templateuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_template(db_session, name="Test Weather", category="weather"):
    """Insert a minimal OverlayTemplate into the database."""
    config_schema = json.dumps({
        "fields": [
            {"key": "location", "label": "Location", "type": "text", "required": True},
            {"key": "units", "label": "Units", "type": "select", "required": False},
        ]
    })
    default_config = json.dumps({"location": "default", "units": "imperial"})
    template = OverlayTemplate(
        name=name,
        category=category,
        description="A test template",
        config_schema=config_schema,
        default_config=default_config,
        preview_path="/previews/test.png",
        version=1,
        is_bundled=True,
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


# ------------------------------------------------------------------
# Template catalog tests
# ------------------------------------------------------------------

def test_list_templates(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_template(db_session, name="Template A", category="weather")
    _seed_template(db_session, name="Template B", category="lower_third")

    resp = client.get("/api/templates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_list_templates_filter_category(client, db_session):
    headers = _get_auth_header(client, db_session)
    _seed_template(db_session, name="Weather One", category="weather")
    _seed_template(db_session, name="Lower Third One", category="lower_third")

    resp = client.get("/api/templates?category=weather", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["category"] == "weather"


def test_get_template_by_id(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    resp = client.get(f"/api/templates/{template.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == template.id
    assert data["name"] == template.name


def test_get_template_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.get("/api/templates/9999", headers=headers)
    assert resp.status_code == 404


# ------------------------------------------------------------------
# Template instance tests
# ------------------------------------------------------------------

def test_create_instance(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    config_values = json.dumps({"location": "Miami", "units": "metric"})
    resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": template.id,
            "config_values": config_values,
            "position_x": 0.1,
            "position_y": 0.9,
            "opacity": 0.8,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_id"] == template.id
    assert data["asset_id"] is not None
    # Verify the config was merged with defaults
    stored_config = json.loads(data["config_values"])
    assert stored_config["location"] == "Miami"
    assert stored_config["units"] == "metric"


def test_create_instance_template_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": 9999,
            "config_values": json.dumps({"location": "Anywhere"}),
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_create_instance_invalid_config_json(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": template.id,
            "config_values": "not valid json {{{",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "valid JSON" in resp.json()["detail"]


def test_create_instance_missing_required_field(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    # 'location' is required but not provided
    resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": template.id,
            "config_values": json.dumps({"units": "metric"}),
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_update_instance(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    # Create an instance first
    create_resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": template.id,
            "config_values": json.dumps({"location": "Miami"}),
        },
        headers=headers,
    )
    instance_id = create_resp.json()["id"]

    # Update display properties
    resp = client.put(
        f"/api/templates/instances/{instance_id}",
        json={"position_x": 0.5, "opacity": 0.7},
        headers=headers,
    )
    assert resp.status_code == 200


def test_update_instance_with_config(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    create_resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": template.id,
            "config_values": json.dumps({"location": "Miami"}),
        },
        headers=headers,
    )
    instance_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/templates/instances/{instance_id}",
        json={"config_values": json.dumps({"location": "Tampa"})},
        headers=headers,
    )
    assert resp.status_code == 200
    stored_config = json.loads(resp.json()["config_values"])
    assert stored_config["location"] == "Tampa"


def test_update_instance_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.put(
        "/api/templates/instances/9999",
        json={"opacity": 0.5},
        headers=headers,
    )
    assert resp.status_code == 404


def test_delete_instance(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    create_resp = client.post(
        "/api/templates/instances",
        json={
            "template_id": template.id,
            "config_values": json.dumps({"location": "Miami"}),
        },
        headers=headers,
    )
    instance_id = create_resp.json()["id"]

    resp = client.delete(f"/api/templates/instances/{instance_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == instance_id


def test_delete_instance_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.delete("/api/templates/instances/9999", headers=headers)
    assert resp.status_code == 404


def test_list_instances(client, db_session):
    headers = _get_auth_header(client, db_session)
    template = _seed_template(db_session)

    # Create two instances
    for loc in ("Miami", "Tampa"):
        client.post(
            "/api/templates/instances",
            json={
                "template_id": template.id,
                "config_values": json.dumps({"location": loc}),
            },
            headers=headers,
        )

    resp = client.get("/api/templates/instances", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_templates_unauthenticated(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 401
