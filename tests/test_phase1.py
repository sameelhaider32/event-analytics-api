"""
test_phase1.py — Minimal tests for Phase 1 (Assets & Operators CRUD).

Run with:  pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app



# ---------------------------------------------------------------------------
# Asset tests
# ---------------------------------------------------------------------------

def test_create_asset_success(client):
    """POST /assets with valid data returns 201 and the created asset."""
    response = client.post("/assets", json={"name": "web-server-01", "type": "server"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "web-server-01"
    assert data["type"] == "server"
    assert "id" in data
    assert "created_at" in data


def test_create_asset_duplicate_returns_409(client):
    """POST /assets with an id that already exists returns 409."""
    payload = {"id": "dup-asset-1", "name": "asset-a", "type": "device"}
    first = client.post("/assets", json=payload)
    assert first.status_code == 201

    second = client.post("/assets", json=payload)
    assert second.status_code == 409


def test_get_asset_by_id_success(client):
    """GET /assets/{id} returns 200 for an existing asset."""
    create = client.post("/assets", json={"id": "lookup-1", "name": "my-asset", "type": "service"})
    assert create.status_code == 201

    response = client.get("/assets/lookup-1")
    assert response.status_code == 200
    assert response.json()["name"] == "my-asset"


def test_get_asset_not_found(client):
    """GET /assets/{id} returns 404 for an id that does not exist."""
    response = client.get("/assets/does-not-exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Operator tests
# ---------------------------------------------------------------------------

def test_create_operator_success(client):
    """POST /operators with valid data returns 201 and the created operator."""
    response = client.post("/operators", json={"name": "alice"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "alice"
    assert "id" in data
    assert "created_at" in data


def test_list_operators_includes_created(client):
    """GET /operators returns a list that contains a previously created operator."""
    client.post("/operators", json={"id": "op-list-1", "name": "bob"})
    response = client.get("/operators")
    assert response.status_code == 200
    ids = [op["id"] for op in response.json()]
    assert "op-list-1" in ids
