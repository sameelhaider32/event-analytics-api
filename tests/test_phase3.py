# tests/test_phase3.py
"""
test_phase3.py — Tests for Phase 3: /analytics/summary

Assumes Phase 2 exists:
- POST /events
- GET /analytics/summary

Run with:
  python -m pytest -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app





def _reset_db():
    """
    Clears tables so tests don't depend on previous runs.
    Adjust table names if your schema differs.
    """
    from app.db import get_db_connection

    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM assets")
        conn.execute("DELETE FROM operators")
        conn.commit()
    finally:
        conn.close()


def _create_asset(client, asset_id="ast_1", name="Payment Service", asset_type="service"):
    r = client.post("/assets", json={"id": asset_id, "name": name, "type": asset_type})
    assert r.status_code in (201, 409)  # allow reruns (409 if already exists)
    return asset_id


def _create_operator(client, operator_id="op_1", name="Ali"):
    r = client.post("/operators", json={"id": operator_id, "name": name})
    assert r.status_code in (201, 409)
    return operator_id


def _post_event(client, payload):
    r = client.post("/events", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _summary(client, **params):
    r = client.get("/analytics/summary", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_summary_empty_returns_zeros(client):
    _reset_db()
    data = _summary(client)

    assert data["total_events"] == 0
    assert data["avg_severity"] is None

    # counts_by_severity should always have "1".."5"
    cbs = data["counts_by_severity"]
    for k in ["1", "2", "3", "4", "5"]:
        assert k in cbs
        assert cbs[k] == 0


def test_counts_by_type_and_total(client):
    _reset_db()
    _create_asset(client, "ast_1")
    _create_operator(client, "op_1")

    _post_event(client, {
        "timestamp": "2026-03-20T10:00:00Z",
        "asset_id": "ast_1",
        "operator_id": "op_1",
        "type": "error",
        "severity": 4,
        "metadata": {"code": "500"},
    })
    _post_event(client, {
        "timestamp": "2026-03-20T10:05:00Z",
        "asset_id": "ast_1",
        "operator_id": "op_1",
        "type": "warning",
        "severity": 2,
        "metadata": {},
    })
    _post_event(client, {
        "timestamp": "2026-03-20T10:10:00Z",
        "asset_id": "ast_1",
        "operator_id": None,
        "type": "error",
        "severity": 3,
        "metadata": {},
    })

    data = _summary(client)
    assert data["total_events"] == 3
    assert data["counts_by_type"]["error"] == 2
    assert data["counts_by_type"]["warning"] == 1


def test_counts_by_severity_has_correct_values(client):
    _reset_db()
    _create_asset(client, "ast_1")
    _create_operator(client, "op_1")

    severities = [1, 2, 2, 5]
    for i, sev in enumerate(severities):
        _post_event(client, {
            "timestamp": f"2026-03-20T11:0{i}:00Z",
            "asset_id": "ast_1",
            "operator_id": "op_1",
            "type": "error",
            "severity": sev,
            "metadata": {},
        })

    data = _summary(client)
    cbs = data["counts_by_severity"]
    assert cbs["1"] == 1
    assert cbs["2"] == 2
    assert cbs["5"] == 1


def test_filter_by_asset_id(client):
    _reset_db()
    _create_asset(client, "ast_1")
    _create_asset(client, "ast_2")

    _post_event(client, {
        "timestamp": "2026-03-20T12:00:00Z",
        "asset_id": "ast_1",
        "operator_id": None,
        "type": "error",
        "severity": 4,
        "metadata": {},
    })
    _post_event(client, {
        "timestamp": "2026-03-20T12:01:00Z",
        "asset_id": "ast_2",
        "operator_id": None,
        "type": "error",
        "severity": 4,
        "metadata": {},
    })

    data = _summary(client, asset_id="ast_1")
    assert data["total_events"] == 1


def test_filter_by_min_severity(client):
    _reset_db()
    _create_asset(client, "ast_1")

    _post_event(client, {
        "timestamp": "2026-03-20T13:00:00Z",
        "asset_id": "ast_1",
        "operator_id": None,
        "type": "warning",
        "severity": 2,
        "metadata": {},
    })
    _post_event(client, {
        "timestamp": "2026-03-20T13:01:00Z",
        "asset_id": "ast_1",
        "operator_id": None,
        "type": "error",
        "severity": 5,
        "metadata": {},
    })

    data = _summary(client, min_severity=4)
    assert data["total_events"] == 1
    assert data["counts_by_type"]["error"] == 1


def test_top_assets_and_top_operators(client):
    _reset_db()
    _create_asset(client, "ast_1")
    _create_asset(client, "ast_2")
    _create_operator(client, "op_1")
    _create_operator(client, "op_2")

    # ast_1: 3 events, ast_2: 1 event
    _post_event(client, {"timestamp": "2026-03-20T14:00:00Z", "asset_id": "ast_1", "operator_id": "op_1", "type": "error", "severity": 4, "metadata": {}})
    _post_event(client, {"timestamp": "2026-03-20T14:01:00Z", "asset_id": "ast_1", "operator_id": "op_1", "type": "error", "severity": 3, "metadata": {}})
    _post_event(client, {"timestamp": "2026-03-20T14:02:00Z", "asset_id": "ast_1", "operator_id": None,   "type": "warning", "severity": 2, "metadata": {}})
    _post_event(client, {"timestamp": "2026-03-20T14:03:00Z", "asset_id": "ast_2", "operator_id": "op_2", "type": "error", "severity": 5, "metadata": {}})

    data = _summary(client)

    top_assets = data["top_assets"]
    assert len(top_assets) >= 1
    assert top_assets[0]["asset_id"] == "ast_1"
    assert top_assets[0]["count"] == 3

    top_ops = data["top_operators"]
    # operator_id None should not appear in top_operators
    for item in top_ops:
        assert item["operator_id"] is not None