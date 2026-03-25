# tests/test_phase5.py
"""
test_phase5.py — Tests for Phase 5: /alerts

Run with:
  python -m pytest tests/test_phase5.py -v
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app



def _reset_db():
    from app.db import get_db_connection
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM assets")
        conn.execute("DELETE FROM operators")
        conn.commit()
    finally:
        conn.close()

def _create_asset(client, asset_id="ast_1"):
    r = client.post("/assets", json={"id": asset_id, "name": f"Asset {asset_id}", "type": "server"})
    assert r.status_code in (201, 409)

def _create_operator(client, op_id="op_1"):
    r = client.post("/operators", json={"id": op_id, "name": f"Op {op_id}"})
    assert r.status_code in (201, 409)

def _post_event(client, timestamp, severity, event_type="routine", asset_id="ast_1", op_id="op_1"):
    r = client.post("/events", json={
        "timestamp": timestamp,
        "asset_id": asset_id,
        "operator_id": op_id,
        "type": event_type,
        "severity": severity,
        "metadata": {}
    })
    assert r.status_code == 201

def _get_alerts(client, **params):
    r = client.get("/alerts", params=params)
    assert r.status_code == 200, r.text
    return r.json()

# 1) empty DB -> /alerts returns []
def test_empty_db_no_alerts(client):
    _reset_db()
    alerts = _get_alerts(client)
    assert alerts == []

# 2) burst rule triggers (>=5 events in 15 min window) for an asset
def test_burst_rule_triggers(client):
    _reset_db()
    _create_asset(client)
    _create_operator(client)
    # Burst requires >=5 in last 15 mins.
    # We will query with to_ts="2026-03-25T10:15:00Z", so burst window is 10:00:00Z to 10:15:00Z
    # 5 events inside window
    for i in range(5):
        _post_event(client, f"2026-03-25T10:1{i}:00Z", severity=1)
        
    alerts = _get_alerts(client, to_ts="2026-03-25T10:15:00Z")
    # Only burst should trigger (severity=1, type='routine')
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "burst"
    assert alerts[0]["asset_id"] == "ast_1"
    assert alerts[0]["evidence"]["count"] == 5

# 3) critical rule triggers when severity==5 event exists
def test_critical_rule_triggers(client):
    _reset_db()
    _create_asset(client)
    _create_operator(client)
    
    _post_event(client, "2026-03-25T10:05:00Z", severity=5)
    
    alerts = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z")
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "critical"
    assert alerts[0]["severity"] == 5
    assert alerts[0]["evidence"]["count"] == 1

# 4) unauthorized rule triggers when type=="unauthorized" event exists
def test_unauthorized_rule_triggers(client):
    _reset_db()
    _create_asset(client)
    _create_operator(client)
    
    _post_event(client, "2026-03-25T10:05:00Z", severity=2, event_type="unauthorized")
    
    alerts = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z")
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "unauthorized"
    assert alerts[0]["evidence"]["count"] == 1

# 5) asset_id filter limits alerts to that asset
def test_asset_id_filter(client):
    _reset_db()
    _create_asset(client, "ast_1")
    _create_asset(client, "ast_2")
    _create_operator(client)
    
    # ast_1 gets critical
    _post_event(client, "2026-03-25T10:05:00Z", severity=5, asset_id="ast_1")
    # ast_2 gets unauthorized
    _post_event(client, "2026-03-25T10:05:00Z", severity=2, event_type="unauthorized", asset_id="ast_2")
    
    alerts_1 = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z", asset_id="ast_1")
    assert len(alerts_1) == 1
    assert alerts_1[0]["alert_type"] == "critical"
    assert alerts_1[0]["asset_id"] == "ast_1"
    
    alerts_2 = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z", asset_id="ast_2")
    assert len(alerts_2) == 1
    assert alerts_2[0]["alert_type"] == "unauthorized"
    assert alerts_2[0]["asset_id"] == "ast_2"

# 6) operator_id filter limits alerts to that operator’s events only
def test_operator_id_filter(client):
    _reset_db()
    _create_asset(client)
    _create_operator(client, "op_1")
    _create_operator(client, "op_2")
    
    # op_1 triggers critical
    _post_event(client, "2026-03-25T10:05:00Z", severity=5, op_id="op_1")
    # op_2 triggers nothing
    _post_event(client, "2026-03-25T10:06:00Z", severity=1, op_id="op_2")
    
    alerts_1 = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z", operator_id="op_1")
    assert len(alerts_1) == 1
    assert alerts_1[0]["alert_type"] == "critical"
    
    alerts_2 = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z", operator_id="op_2")
    assert len(alerts_2) == 0

# 7) time window behavior: events outside range do not trigger alerts
def test_time_window_behavior(client):
    _reset_db()
    _create_asset(client)
    _create_operator(client)
    
    # Critical event outside window
    _post_event(client, "2026-03-25T09:00:00Z", severity=5) 
    
    # Query window is after the event
    alerts = _get_alerts(client, from_ts="2026-03-25T10:00:00Z", to_ts="2026-03-25T10:15:00Z")
    assert len(alerts) == 0

