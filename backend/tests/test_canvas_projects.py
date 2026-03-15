"""
Tests for canvas project endpoints (/api/canvas-projects/*).
"""

import base64
import json

from models.database import User
from models.canvas import CanvasProject
from routers.auth import get_password_hash


def _get_auth_header(client, db_session):
    """Seed a test user and login to get an Authorization header dict."""
    user = User(
        username="canvasuser",
        password_hash=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "canvasuser", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _minimal_png_base64():
    """Return a minimal valid base64-encoded PNG for export tests."""
    return base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()


# ------------------------------------------------------------------
# CRUD Tests
# ------------------------------------------------------------------

def test_create_canvas_project(client, db_session):
    headers = _get_auth_header(client, db_session)
    resp = client.post(
        "/api/canvas-projects",
        json={
            "name": "My Test Canvas",
            "description": "A canvas for testing",
            "width": 1920,
            "height": 1080,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Test Canvas"
    assert data["width"] == 1920
    assert data["height"] == 1080
    assert "canvas_json" in data  # Detail response includes canvas_json


def test_list_canvas_projects(client, db_session):
    headers = _get_auth_header(client, db_session)
    # Create two projects
    client.post(
        "/api/canvas-projects",
        json={"name": "Project A"},
        headers=headers,
    )
    client.post(
        "/api/canvas-projects",
        json={"name": "Project B"},
        headers=headers,
    )

    resp = client.get("/api/canvas-projects", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_get_canvas_project_detail(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/canvas-projects",
        json={
            "name": "Detail Test",
            "canvas_json": '{"version":"6.0.0","objects":[{"type":"rect"}]}',
        },
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    resp = client.get(f"/api/canvas-projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == project_id
    assert "canvas_json" in data
    parsed = json.loads(data["canvas_json"])
    assert parsed["version"] == "6.0.0"


def test_get_canvas_project_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.get("/api/canvas-projects/9999", headers=headers)
    assert resp.status_code == 404


def test_save_canvas_project(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/canvas-projects",
        json={"name": "Save Test"},
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    updated_json = '{"version":"6.0.0","objects":[{"type":"circle","radius":50}]}'
    resp = client.put(
        f"/api/canvas-projects/{project_id}",
        json={"canvas_json": updated_json},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert json.loads(data["canvas_json"]) == json.loads(updated_json)


def test_save_canvas_project_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.put(
        "/api/canvas-projects/9999",
        json={"canvas_json": '{"version":"6.0.0","objects":[]}'},
        headers=headers,
    )
    assert resp.status_code == 404


def test_export_canvas_project(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/canvas-projects",
        json={"name": "Export Source"},
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    png_data = _minimal_png_base64()
    resp = client.post(
        f"/api/canvas-projects/{project_id}/export",
        json={
            "asset_name": "Exported Canvas",
            "png_data": png_data,
            "position_x": 0.1,
            "position_y": 0.2,
            "width": 400,
            "height": 300,
            "opacity": 0.9,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Exported Canvas"
    assert data["type"] == "canvas_composite"
    assert data["canvas_project_id"] == project_id


def test_export_canvas_project_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.post(
        "/api/canvas-projects/9999/export",
        json={
            "asset_name": "Should Fail",
            "png_data": _minimal_png_base64(),
        },
        headers=headers,
    )
    assert resp.status_code == 400  # ValueError -> 400


def test_duplicate_canvas_project(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/canvas-projects",
        json={
            "name": "Original",
            "description": "The original project",
            "canvas_json": '{"version":"6.0.0","objects":[{"type":"text"}]}',
        },
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/canvas-projects/{project_id}/duplicate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Original (Copy)"
    assert data["id"] != project_id
    # The copy should have the same canvas_json
    assert json.loads(data["canvas_json"]) == json.loads(
        '{"version":"6.0.0","objects":[{"type":"text"}]}'
    )


def test_duplicate_canvas_project_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.post(
        "/api/canvas-projects/9999/duplicate",
        headers=headers,
    )
    assert resp.status_code == 404


def test_delete_canvas_project(client, db_session):
    headers = _get_auth_header(client, db_session)
    create_resp = client.post(
        "/api/canvas-projects",
        json={"name": "To Delete"},
        headers=headers,
    )
    project_id = create_resp.json()["id"]

    resp = client.delete(f"/api/canvas-projects/{project_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id

    # Soft delete — GET should return 404
    resp = client.get(f"/api/canvas-projects/{project_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_canvas_project_not_found(client, db_session):
    headers = _get_auth_header(client, db_session)

    resp = client.delete("/api/canvas-projects/9999", headers=headers)
    assert resp.status_code == 404


def test_canvas_projects_unauthenticated(client):
    resp = client.get("/api/canvas-projects")
    assert resp.status_code == 401
