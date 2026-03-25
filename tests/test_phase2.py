"""
test_phase2.py — Tests for Phase 2 (Events ingestion & querying).

Run with:  pytest tests/test_phase2.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


# ---------------------------------------------------------------------------
# Helper — create a test asset + operator via the API
# ---------------------------------------------------------------------------

def _setup_asset_and_operator(client):
    """Create a test asset and operator, returning their ids."""
    asset_resp = client.post("/assets", json={
        "id": "test-asset-1", "name": "sensor-A", "type": "sensor"
    })
    operator_resp = client.post("/operators", json={
        "id": "test-op-1", "name": "alice"
    })
    return asset_resp.json()["id"], operator_resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_event_single_success(client):
    """POST /events with a single valid event returns 201."""
    asset_id, operator_id = _setup_asset_and_operator(client)

    response = client.post("/events", json={
        "timestamp": "2026-03-20T10:00:00Z",
        "asset_id": asset_id,
        "operator_id": operator_id,
        "type": "cpu_spike",
        "severity": 3,
        "metadata": {"cpu_percent": 95.2},
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["asset_id"] == asset_id
    assert data["type"] == "cpu_spike"
    assert data["severity"] == 3
    assert data["metadata"]["cpu_percent"] == 95.2


def test_create_event_bulk_success(client):
    """POST /events with a list of 2 events returns 201 and a list."""
    asset_id, op_id = _setup_asset_and_operator(client)
    response = client.post("/events", json=[
        {
            "timestamp": "2026-03-20T11:00:00Z",
            "asset_id": asset_id,
            "type": "disk_full",
            "severity": 4,
        },
        {
            "timestamp": "2026-03-20T12:00:00Z",
            "asset_id": asset_id,
            "operator_id": op_id,
            "type": "login",
            "severity": 1,
        },
    ])
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["type"] == "disk_full"
    assert data[1]["type"] == "login"


def test_create_event_missing_asset_returns_404(client):
    """POST /events with a non-existent asset_id returns 404."""
    response = client.post("/events", json={
        "timestamp": "2026-03-20T13:00:00Z",
        "asset_id": "no-such-asset",
        "type": "error",
        "severity": 2,
    })
    assert response.status_code == 404
    assert "no-such-asset" in response.json()["detail"]


def test_create_event_missing_operator_returns_404(client):
    """POST /events with a non-existent operator_id returns 404."""
    asset_id, op_id = _setup_asset_and_operator(client)
    response = client.post("/events", json={
        "timestamp": "2026-03-20T13:30:00Z",
        "asset_id": asset_id,
        "operator_id": "no-such-operator",
        "type": "error",
        "severity": 2,
    })
    assert response.status_code == 404
    assert "no-such-operator" in response.json()["detail"]


def test_list_events_returns_inserted(client):
    """GET /events returns previously inserted events."""
    asset_id, op_id = _setup_asset_and_operator(client)
    for _ in range(3):
        client.post("/events", json={"timestamp": "2026-03-20T10:00:00Z", "asset_id": asset_id, "type": "warning", "severity": 2})
    response = client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # we created 3 events in earlier tests


def test_filter_events_by_asset_id(client):
    """GET /events?asset_id=test-asset-1 returns only matching events."""
    asset_id, op_id = _setup_asset_and_operator(client)
    client.post("/events", json={"timestamp": "2026-03-20T10:00:00Z", "asset_id": asset_id, "type": "warning", "severity": 2})
    response = client.get("/events", params={"asset_id": asset_id})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for event in data:
        assert event["asset_id"] == asset_id


def test_filter_events_by_min_severity(client):
    """GET /events?min_severity=3 returns only events with severity >= 3."""
    asset_id, op_id = _setup_asset_and_operator(client)
    client.post("/events", json={"timestamp": "2026-03-20T10:00:00Z", "asset_id": asset_id, "type": "warning", "severity": 4})
    response = client.get("/events", params={"min_severity": 3})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for event in data:
        assert event["severity"] >= 3

def test_filter_events_by_legacy_type(client):
    """GET /events?type=warning gracefully evaluates natively identical to event_type=warning."""
    asset_id, op_id = _setup_asset_and_operator(client)
    client.post("/events", json={"timestamp": "2026-03-20T10:00:00Z", "asset_id": asset_id, "type": "legacy_query", "severity": 2})
    
    res1 = client.get("/events", params={"event_type": "legacy_query"})
    res2 = client.get("/events", params={"type": "legacy_query"})
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert len(res1.json()) >= 1
    assert len(res2.json()) == len(res1.json())


def test_get_event_by_id_success(client):
    """GET /events/{id} returns 200 for an existing event."""
    asset_id, op_id = _setup_asset_and_operator(client)
    client.post("/events", json={"timestamp": "2026-03-20T10:00:00Z", "asset_id": asset_id, "type": "warning", "severity": 2})
    # First, list events and pick the first one
    events = client.get("/events").json()
    assert len(events) > 0
    event_id = events[0]["id"]

    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_id


def test_get_event_not_found(client):
    """GET /events/{id} returns 404 for a missing event."""
    response = client.get("/events/999999")
    assert response.status_code == 404


def test_create_event_severity_out_of_range(client):
    """POST /events with severity > 5 returns 422 (Pydantic validation)."""
    asset_id, op_id = _setup_asset_and_operator(client)
    response = client.post("/events", json={
        "timestamp": "2026-03-20T14:00:00Z",
        "asset_id": asset_id,
        "type": "error",
        "severity": 10,
    })
    assert response.status_code == 422
