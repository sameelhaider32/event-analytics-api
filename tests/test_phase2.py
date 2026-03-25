"""
test_phase2.py — Tests for Phase 2 (Events ingestion & querying).

Run with:  pytest tests/test_phase2.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


# ---------------------------------------------------------------------------
# Fixture — shared TestClient with clean DB state
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def clean_db_for_phase2(client):
    from app.db import get_db_connection
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM assets")
        conn.execute("DELETE FROM operators")
        conn.commit()
    finally:
        conn.close()


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
    response = client.post("/events", json=[
        {
            "timestamp": "2026-03-20T11:00:00Z",
            "asset_id": "test-asset-1",
            "type": "disk_full",
            "severity": 4,
        },
        {
            "timestamp": "2026-03-20T12:00:00Z",
            "asset_id": "test-asset-1",
            "operator_id": "test-op-1",
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
    response = client.post("/events", json={
        "timestamp": "2026-03-20T13:30:00Z",
        "asset_id": "test-asset-1",
        "operator_id": "no-such-operator",
        "type": "error",
        "severity": 2,
    })
    assert response.status_code == 404
    assert "no-such-operator" in response.json()["detail"]


def test_list_events_returns_inserted(client):
    """GET /events returns previously inserted events."""
    response = client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # we created 3 events in earlier tests


def test_filter_events_by_asset_id(client):
    """GET /events?asset_id=test-asset-1 returns only matching events."""
    response = client.get("/events", params={"asset_id": "test-asset-1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for event in data:
        assert event["asset_id"] == "test-asset-1"


def test_filter_events_by_min_severity(client):
    """GET /events?min_severity=3 returns only events with severity >= 3."""
    response = client.get("/events", params={"min_severity": 3})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for event in data:
        assert event["severity"] >= 3


def test_get_event_by_id_success(client):
    """GET /events/{id} returns 200 for an existing event."""
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
    response = client.post("/events", json={
        "timestamp": "2026-03-20T14:00:00Z",
        "asset_id": "test-asset-1",
        "type": "error",
        "severity": 10,
    })
    assert response.status_code == 422
