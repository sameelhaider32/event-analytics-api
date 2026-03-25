"""
main.py — The FastAPI application entry-point.

This file:
  - Creates the FastAPI app
  - Initialises the database on startup
  - Exposes the GET /health endpoint  (Phase 0)
  - Exposes CRUD endpoints for assets and operators  (Phase 1)
  - Automatic interactive docs are available at /docs
"""

import sqlite3
from contextlib import asynccontextmanager
from typing import List, Optional, Union
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException, Depends, Query

from app.db import (
    init_db,
    run_db_check,
    get_db_connection,
    insert_asset,
    get_all_assets,
    get_asset_by_id,
    insert_operator,
    get_all_operators,
    get_operator_by_id,
    insert_event,
    insert_events_bulk,
    get_event_by_id,
    get_events_filtered,
    get_analytics_summary,
    get_health_score_stats,
    get_burst_assets,
    get_event_ids_by_rule,
)
from app.schemas import (
    AssetCreate, Asset,
    OperatorCreate, Operator,
    EventCreate, Event,
    AnalyticsSummary,
    HealthScoreResponse,
    AlertResponse,
)


# ---------------------------------------------------------------------------
# Lifespan (runs code on startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs once when the server starts up.
    We use it to make sure the database and its tables exist.
    """
    # --- Startup ---
    init_db()
    yield
    # --- Shutdown (nothing to clean up for now) ---


# ---------------------------------------------------------------------------
# Create the app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Event Analytics API",
    description="A simple Event Analytics API — Phase 0 foundation + Phase 1 CRUD + Phase 2 Events + Phase 3 Analytics.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Phase 0 — Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """
    Quick health endpoint.
    Returns whether the service and its database are working.
    """
    db_ok = run_db_check()

    return {
        "ok": db_ok,
        "db_ok": db_ok,
        "service": "event-analytics-api",
    }


# ---------------------------------------------------------------------------
# Phase 1 — Assets
# ---------------------------------------------------------------------------

@app.post("/assets", response_model=Asset, status_code=201)
def create_asset(body: AssetCreate):
    """Create a new asset. Returns 409 if the id already exists."""
    try:
        asset = insert_asset(body.id, body.name, body.type)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Asset with id '{body.id}' already exists.")
    return asset


@app.get("/assets", response_model=List[Asset])
def list_assets():
    """Return all assets."""
    assets = get_all_assets()
    return assets


@app.get("/assets/{asset_id}", response_model=Asset)
def get_asset(asset_id: str):
    """Return a single asset or 404."""
    asset = get_asset_by_id(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")
    return asset


# ---------------------------------------------------------------------------
# Phase 1 — Operators
# ---------------------------------------------------------------------------

@app.post("/operators", response_model=Operator, status_code=201)
def create_operator(body: OperatorCreate):
    """Create a new operator. Returns 409 if the id already exists."""
    try:
        operator = insert_operator(body.id, body.name)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Operator with id '{body.id}' already exists.")
    return operator


@app.get("/operators", response_model=List[Operator])
def list_operators():
    """Return all operators."""
    operators = get_all_operators()
    return operators


@app.get("/operators/{operator_id}", response_model=Operator)
def get_operator(operator_id: str):
    """Return a single operator or 404."""
    operator = get_operator_by_id(operator_id)
    if operator is None:
        raise HTTPException(status_code=404, detail=f"Operator '{operator_id}' not found.")
    return operator


# ---------------------------------------------------------------------------
# Phase 2 — Events
# ---------------------------------------------------------------------------

@app.post("/events", response_model=Union[Event, List[Event]], status_code=201)
def create_events(body: Union[EventCreate, List[EventCreate]]):
    """
    Create one or more events.
    Accepts a single EventCreate object OR a JSON array of EventCreate objects.
    Validates that asset_id exists (and operator_id if provided).
    """
    # Normalise input: wrap a single item in a list for uniform processing
    if isinstance(body, list):
        items = body
        is_bulk = True
    else:
        items = [body]
        is_bulk = False

    # ---------- validation pass ----------
    for i, item in enumerate(items):
        prefix = f"Item [{i}]: " if is_bulk else ""

        # asset_id must exist
        if get_asset_by_id(item.asset_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"{prefix}Asset '{item.asset_id}' not found.",
            )

        # operator_id must exist if provided
        if item.operator_id is not None and get_operator_by_id(item.operator_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"{prefix}Operator '{item.operator_id}' not found.",
            )

    # ---------- insert ----------
    if is_bulk:
        events_data = [
            {
                "timestamp": item.timestamp,
                "asset_id": item.asset_id,
                "operator_id": item.operator_id,
                "event_type": item.type,
                "severity": item.severity,
                "metadata": item.metadata,
            }
            for item in items
        ]
        created = insert_events_bulk(events_data)
        return created
    else:
        item = items[0]
        created = insert_event(
            timestamp=item.timestamp,
            asset_id=item.asset_id,
            operator_id=item.operator_id,
            event_type=item.type,
            severity=item.severity,
            metadata=item.metadata,
        )
        return created


@app.get("/events", response_model=List[Event])
def list_events(
    asset_id: Optional[str] = Query(None),
    operator_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_severity: Optional[int] = Query(None, ge=1, le=5),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Return events matching optional filters, ordered newest-first."""
    actual_type = event_type if event_type is not None else type
    events = get_events_filtered(
        asset_id=asset_id,
        operator_id=operator_id,
        event_type=actual_type,
        min_severity=min_severity,
        from_ts=from_ts,
        to_ts=to_ts,
        limit=limit,
        offset=offset,
    )
    return events


@app.get("/events/{event_id}", response_model=Event)
def get_event(event_id: int):
    """Return a single event or 404."""
    event = get_event_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
    return event


# ---------------------------------------------------------------------------
# Phase 3 — Analytics
# ---------------------------------------------------------------------------

@app.get("/analytics/summary", response_model=AnalyticsSummary)
def get_summary(
    asset_id: Optional[str] = Query(None),
    operator_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_severity: Optional[int] = Query(None, ge=1, le=5),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
):
    """Return summary metrics for events matching optional filters."""
    actual_type = event_type if event_type is not None else type
    summary = get_analytics_summary(
        asset_id=asset_id,
        operator_id=operator_id,
        event_type=actual_type,
        min_severity=min_severity,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    return summary


# ---------------------------------------------------------------------------
# Phase 4 — Health Score
# ---------------------------------------------------------------------------

@app.get("/score/health", response_model=HealthScoreResponse)
def get_health_score(
    window_hours: int = Query(24, ge=1, le=168),
    asset_id: Optional[str] = Query(None),
    operator_id: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
):
    """
    Return health score based on recent events (Phase 4).
    Calculates a score 0-100 and outlines deductions.
    """
    now_utc = datetime.now(timezone.utc)
    
    # 1. Determine start time (from_ts takes precedence over window_hours)
    if from_ts is not None:
        start_ts = from_ts
    else:
        start_dt = now_utc - timedelta(hours=window_hours)
        start_ts = start_dt.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        
    # 2. Determine end time (to_ts vs now_utc)
    if to_ts is not None:
        end_ts = to_ts
    else:
        end_ts = now_utc.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')

    # 3. Fetch aggregates
    stats = get_health_score_stats(
        from_ts=start_ts,
        to_ts=end_ts,
        asset_id=asset_id,
        operator_id=operator_id
    )

    total_events = stats["total_events"]
    
    # 4. Compute formula
    if total_events == 0:
        score = 100
        severity_sum = 0
        high_sev_count = 0
        error_count = 0
        deduction_severity = 0
        deduction_high = 0
        deduction_error = 0
    else:
        severity_sum = stats["severity_sum"]
        high_sev_count = stats["high_sev_count"]
        error_count = stats["error_count"]
        
        deduction_severity = 2 * severity_sum
        deduction_high = 5 * high_sev_count
        deduction_error = 2 * error_count
        
        raw_score = 100 - deduction_severity - deduction_high - deduction_error
        score = max(0, min(100, raw_score))

    # 5. Determine status
    if score >= 80:
        status = "good"
    elif score >= 50:
        status = "moderate"
    else:
        status = "poor"

    return {
        "filters": {
            "asset_id": asset_id,
            "operator_id": operator_id,
            "from_ts": from_ts,
            "to_ts": to_ts,
        },
        "window_hours": window_hours,
        "total_events": total_events,
        "score": score,
        "status": status,
        "breakdown": {
            "severity_sum": severity_sum,
            "high_sev_count": high_sev_count,
            "error_count": error_count,
            "deduction_severity": deduction_severity,
            "deduction_high": deduction_high,
            "deduction_error": deduction_error,
        }
    }


# ---------------------------------------------------------------------------
# Phase 5 — Alerts
# ---------------------------------------------------------------------------

@app.get("/alerts", response_model=List[AlertResponse])
def get_alerts(
    asset_id: Optional[str] = Query(None),
    operator_id: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
):
    """
    Return active alerts based on hardcoded rules (Phase 5).
    Rules: Critical (priority 1), Unauthorized (priority 2), Burst (priority 3).
    """
    now_utc = datetime.now(timezone.utc)
    
    # End logic
    if to_ts is not None:
        end_ts = to_ts
    else:
        end_ts = now_utc.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')
        
    end_dt = datetime.strptime(end_ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        
    # Start logic (default 24 hours back)
    if from_ts is not None:
        start_ts = from_ts
    else:
        start_ts = (end_dt - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
    # Burst logic (last 15m)
    burst_start_ts = (end_dt - timedelta(minutes=15)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    alerts = []
    
    # Rule B: Critical (severity = 5)
    critical_groups = get_event_ids_by_rule("severity = 5", start_ts, end_ts, asset_id, operator_id)
    for a_id, ev_ids in critical_groups.items():
        alerts.append({
            "alert_type": "critical",
            "asset_id": a_id,
            "operator_id": operator_id,
            "triggered_at": end_ts,
            "severity": 5,
            "evidence": {
                "count": len(ev_ids),
                "event_ids": ev_ids,
            }
        })
        
    # Rule C: Unauthorized (type = 'unauthorized')
    unauth_groups = get_event_ids_by_rule("type = 'unauthorized'", start_ts, end_ts, asset_id, operator_id)
    for a_id, ev_ids in unauth_groups.items():
        alerts.append({
            "alert_type": "unauthorized",
            "asset_id": a_id,
            "operator_id": operator_id,
            "triggered_at": end_ts,
            "severity": None,
            "evidence": {
                "count": len(ev_ids),
                "event_ids": ev_ids,
            }
        })
        
    # Rule A: Burst (>= 5 events within 15min)
    burst_assets = get_burst_assets(burst_start_ts, end_ts, asset_id, operator_id)
    for b in burst_assets:
        alerts.append({
            "alert_type": "burst",
            "asset_id": b["asset_id"],
            "operator_id": operator_id,
            "triggered_at": end_ts,
            "severity": None,
            "evidence": {
                "count": b["count"],
                "window_minutes": 15,
            }
        })
        
    return alerts

