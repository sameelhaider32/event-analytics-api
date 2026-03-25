# tests/test_phase4.py
"""
test_phase4.py — Tests for Phase 4: /score/health

Assumes Phase 2 exists (POST /events) and Phase 0/1 for setup.

Run with:
  python -m pytest tests/test_phase4.py -v
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app





def _create_asset(client, asset_id="ast_1"):
    r = client.post("/assets", json={"id": asset_id, "name": f"Asset {asset_id}", "type": "server"})
    assert r.status_code in (201, 409)

def _create_operator(client, op_id="op_1"):
    r = client.post("/operators", json={"id": op_id, "name": f"Op {op_id}"})
    assert r.status_code in (201, 409)

def _post_event(client, timestamp, severity, event_type="warning", asset_id="ast_1", op_id="op_1"):
    r = client.post("/events", json={
        "timestamp": timestamp,
        "asset_id": asset_id,
        "operator_id": op_id,
        "type": event_type,
        "severity": severity,
        "metadata": {}
    })
    assert r.status_code == 201

def _get_score(client, **params):
    r = client.get("/score/health", params=params)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Test 1: Empty range returns score=100 and total_events=0 and deductions all 0.
# ---------------------------------------------------------------------------
def test_empty_range_perfect_score(client):
    data = _get_score(client, from_ts="2026-03-25T00:00:00Z", to_ts="2026-03-25T01:00:00Z")
    assert data["total_events"] == 0
    assert data["score"] == 100
    assert data["status"] == "good"
    b = data["breakdown"]
    assert b["severity_sum"] == 0
    assert b["high_sev_count"] == 0
    assert b["error_count"] == 0
    assert b["deduction_severity"] == 0
    assert b["deduction_high"] == 0
    assert b["deduction_error"] == 0


# ---------------------------------------------------------------------------
# Test 2: Inserting an event in-range reduces score correctly.
# ---------------------------------------------------------------------------
def test_event_in_range_reduces_score(client):
    _create_asset(client)
    _create_operator(client)
    _post_event(client, "2026-03-25T10:00:00Z", severity=2, event_type="login")
    
    # Formula for 1 event: 
    # severity_sum = 2 -> deduction 4
    # high_sev = 0 -> deduction 0
    # error = 0 -> deduction 0
    # score = 100 - 4 = 96
    data = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z")
    assert data["total_events"] == 1
    assert data["score"] == 96


# ---------------------------------------------------------------------------
# Test 3: Events outside the time range are safely ignored.
# ---------------------------------------------------------------------------
def test_events_outside_range_ignored(client):
    _create_asset(client)
    _create_operator(client)
    _post_event(client, "2026-03-25T08:00:00Z", severity=3) # before range
    _post_event(client, "2026-03-25T12:00:00Z", severity=3) # after range
    
    data = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z")
    assert data["total_events"] == 0
    assert data["score"] == 100


# ---------------------------------------------------------------------------
# Test 4: Severity >= 4 contributes to high_sev_count and deduction_high.
# ---------------------------------------------------------------------------
def test_high_severity_deduction(client):
    _create_asset(client)
    _create_operator(client)
    _post_event(client, "2026-03-25T10:00:00Z", severity=4, event_type="login")
    
    # Formula:
    # sev_sum = 4 -> deduction 8
    # high_sev = 1 -> deduction 5 
    # error = 0 -> 0
    # score = 100 - 8 - 5 = 87
    data = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z")
    assert data["total_events"] == 1
    assert data["breakdown"]["high_sev_count"] == 1
    assert data["breakdown"]["deduction_high"] == 5
    assert data["score"] == 87


# ---------------------------------------------------------------------------
# Test 5: Type="error" contributes to error_count and deduction_error.
# ---------------------------------------------------------------------------
def test_error_type_deduction(client):
    _create_asset(client)
    _create_operator(client)
    _post_event(client, "2026-03-25T10:00:00Z", severity=2, event_type="error") # notice event_type
    
    # Formula:
    # sev_sum = 2 -> deduction 4
    # high_sev = 0 -> 0 
    # error = 1 -> deduction 2
    # score = 100 - 4 - 2 = 94
    data = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z")
    assert data["total_events"] == 1
    assert data["breakdown"]["error_count"] == 1
    assert data["breakdown"]["deduction_error"] == 2
    assert data["score"] == 94


# ---------------------------------------------------------------------------
# Test 6: Asset ID filtering works (two assets, score differs).
# ---------------------------------------------------------------------------
def test_asset_id_filter(client):
    _create_asset(client, "ast_1")
    _create_asset(client, "ast_2")
    _create_operator(client)
    
    # ast_1 gets a bad event
    _post_event(client, "2026-03-25T10:00:00Z", severity=5, event_type="error", asset_id="ast_1")
    # ast_2 gets a mild event
    _post_event(client, "2026-03-25T10:00:00Z", severity=1, event_type="login", asset_id="ast_2")
    
    data1 = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z", asset_id="ast_1")
    assert data1["total_events"] == 1
    assert data1["score"] < 100  # Will be 100 - 10(sev) - 5(high) - 2(err) = 83
    
    data2 = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z", asset_id="ast_2")
    assert data2["total_events"] == 1
    assert data2["score"] == 98  # 100 - 2(sev)
    
    assert data1["score"] != data2["score"]


# ---------------------------------------------------------------------------
# Test 7: Operator ID filtering works (two operators, score differs).
# ---------------------------------------------------------------------------
def test_operator_id_filter(client):
    _create_asset(client)
    _create_operator(client, "op_1")
    _create_operator(client, "op_2")
    
    # op_1 gets worst possible
    _post_event(client, "2026-03-25T10:00:00Z", severity=5, event_type="error", op_id="op_1")
    _post_event(client, "2026-03-25T10:00:00Z", severity=5, event_type="error", op_id="op_1")
    # op_2 gets empty
    
    data1 = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z", operator_id="op_1")
    assert data1["total_events"] == 2
    assert data1["score"] == 66  # 100 - 20(sev) - 10(high) - 4(err) = 66
    
    data2 = _get_score(client, from_ts="2026-03-25T09:00:00Z", to_ts="2026-03-25T11:00:00Z", operator_id="op_2")
    assert data2["total_events"] == 0
    assert data2["score"] == 100
    
    assert data1["score"] != data2["score"]
