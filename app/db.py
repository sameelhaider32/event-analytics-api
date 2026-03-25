"""
db.py — Database helpers using Python's built-in sqlite3.

This module handles:
  - Connecting to the SQLite database file (app.db)
  - Creating tables on first run (init_db)
  - A quick health-check query (run_db_check)
  - CRUD helpers for assets and operators (Phase 1)
"""

import json
import sqlite3
import os
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# app/db.py
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app.db")

def get_db_path() -> str:
    return os.getenv("REST_PROJECT_DB_PATH", DEFAULT_DB_PATH)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db_connection():
    """
    Open and return a connection to the SQLite database.
    - timeout=30 gives plenty of time for locks to clear.
    - check_same_thread=False allows FastAPI's threadpool to use it.
    """
    connection = sqlite3.connect(get_db_path(), timeout=30.0, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA busy_timeout=30000;")
    connection.row_factory = sqlite3.Row  # return rows as dict-like objects
    return connection


# ---------------------------------------------------------------------------
# Table creation (runs once at startup)
# ---------------------------------------------------------------------------

def init_db():
    """
    Create all tables if they don't already exist.
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor()

        # -- events table (Phase 0 + updated in Phase 2) -----------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp      TEXT    NOT NULL,
                type           TEXT    NOT NULL,
                severity       INTEGER NOT NULL DEFAULT 0,
                asset_id       TEXT    NOT NULL,
                operator_id    TEXT,
                metadata_json  TEXT
            );
        """)

        # Safe migration: add operator_id column if it's missing (old schema)
        try:
            cursor.execute("ALTER TABLE events ADD COLUMN operator_id TEXT;")
        except sqlite3.OperationalError:
            pass  # column already exists — nothing to do

        # -- assets table (Phase 1) --------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
        """)

        # -- operators table (Phase 1) -----------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operators (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
        """)

        connection.commit()
    finally:
        connection.close()
    
    print("✔ Database initialised (tables created if needed).")


# ---------------------------------------------------------------------------
# Health-check helper
# ---------------------------------------------------------------------------

def run_db_check():
    """
    Run a trivial query (SELECT 1) to confirm the database is reachable.
    Returns True if the query succeeds, False otherwise.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        connection.close()
        return True
    except Exception as error:
        print(f"Database health-check failed: {error}")
        return False


# ---------------------------------------------------------------------------
# Asset CRUD helpers (Phase 1)
# ---------------------------------------------------------------------------

def insert_asset(asset_id, name, asset_type):
    """Insert a new asset row. Returns the full row as a dict."""
    if not asset_id:
        asset_id = str(uuid.uuid4())

    created_at = datetime.now(timezone.utc).isoformat()
    
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO assets (id, name, type, created_at) VALUES (?, ?, ?, ?)",
                (asset_id, name, asset_type, created_at),
            )
    finally:
        conn.close()
        
    return {"id": asset_id, "name": name, "type": asset_type, "created_at": created_at}


def get_all_assets():
    """Return every asset as a list of dicts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, created_at FROM assets")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_asset_by_id(asset_id):
    """Return a single asset dict, or None if not found."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, created_at FROM assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Operator CRUD helpers (Phase 1)
# ---------------------------------------------------------------------------

def insert_operator(operator_id, name):
    """Insert a new operator row. Returns the full row as a dict."""
    if not operator_id:
        operator_id = str(uuid.uuid4())

    created_at = datetime.now(timezone.utc).isoformat()
    
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO operators (id, name, created_at) VALUES (?, ?, ?)",
                (operator_id, name, created_at),
            )
    finally:
        conn.close()
        
    return {"id": operator_id, "name": name, "created_at": created_at}


def get_all_operators():
    """Return every operator as a list of dicts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM operators")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_operator_by_id(operator_id):
    """Return a single operator dict, or None if not found."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM operators WHERE id = ?", (operator_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Event helpers (Phase 2)
# ---------------------------------------------------------------------------

def row_to_event(row):
    """
    Convert a sqlite3.Row from the events table into a plain dict
    that matches the Event schema. Parses metadata_json back to a dict.
    """
    raw = dict(row)
    # Parse the JSON string stored in metadata_json into a Python dict
    meta_str = raw.pop("metadata_json", None)
    raw["metadata"] = json.loads(meta_str) if meta_str else {}
    return raw


def insert_event(timestamp, asset_id, operator_id, event_type, severity, metadata):
    """
    Insert a single event row. Returns the full row as a dict (with id).
    """
    metadata_json = json.dumps(metadata or {})
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (timestamp, asset_id, operator_id, type, severity, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (timestamp, asset_id, operator_id, event_type, severity, metadata_json),
            )
            event_id = cursor.lastrowid
    finally:
        conn.close()

    return {
        "id": event_id,
        "timestamp": timestamp,
        "asset_id": asset_id,
        "operator_id": operator_id,
        "type": event_type,
        "severity": severity,
        "metadata": metadata or {},
    }


def insert_events_bulk(events_list):
    """
    Insert multiple events in a single transaction.
    events_list is a list of dicts with keys:
      timestamp, asset_id, operator_id, event_type, severity, metadata
    Returns a list of created event dicts (with ids).
    """
    results = []
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            for ev in events_list:
                metadata_json = json.dumps(ev["metadata"] or {})
                cursor.execute(
                    """
                    INSERT INTO events (timestamp, asset_id, operator_id, type, severity, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (ev["timestamp"], ev["asset_id"], ev["operator_id"],
                     ev["event_type"], ev["severity"], metadata_json),
                )
                results.append({
                    "id": cursor.lastrowid,
                    "timestamp": ev["timestamp"],
                    "asset_id": ev["asset_id"],
                    "operator_id": ev["operator_id"],
                    "type": ev["event_type"],
                    "severity": ev["severity"],
                    "metadata": ev["metadata"] or {},
                })
    finally:
        conn.close()

    return results


def get_event_by_id(event_id):
    """Return a single event dict, or None if not found."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, asset_id, operator_id, type, severity, metadata_json FROM events WHERE id = ?",
            (event_id,),
        )
        row = cursor.fetchone()
        return row_to_event(row) if row else None
    finally:
        conn.close()


def _build_events_where_clause(
    asset_id=None,
    operator_id=None,
    event_type=None,
    min_severity=None,
    from_ts=None,
    to_ts=None,
):
    """
    Helper to construct the WHERE clause and parameters for event queries.
    Returns (where_sql, params_list).
    where_sql might be empty ("") if no filters exist.
    """
    conditions = []
    params = []

    if asset_id is not None:
        conditions.append("asset_id = ?")
        params.append(asset_id)
    if operator_id is not None:
        conditions.append("operator_id = ?")
        params.append(operator_id)
    if event_type is not None:
        conditions.append("type = ?")
        params.append(event_type)
    if min_severity is not None:
        conditions.append("severity >= ?")
        params.append(min_severity)
    if from_ts is not None:
        conditions.append("timestamp >= ?")
        params.append(from_ts)
    if to_ts is not None:
        conditions.append("timestamp <= ?")
        params.append(to_ts)

    where_sql = ""
    if conditions:
        where_sql = " WHERE " + " AND ".join(conditions)

    return where_sql, params


def get_events_filtered(
    asset_id=None,
    operator_id=None,
    event_type=None,
    min_severity=None,
    from_ts=None,
    to_ts=None,
    limit=100,
    offset=0,
):
    """
    Return events matching the given optional filters,
    ordered by id DESC (newest first).
    All filters are combined with AND.
    """
    where_sql, params = _build_events_where_clause(
        asset_id, operator_id, event_type, min_severity, from_ts, to_ts
    )
    
    query = "SELECT id, timestamp, asset_id, operator_id, type, severity, metadata_json FROM events"
    query += where_sql
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [row_to_event(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Analytics helpers (Phase 3)
# ---------------------------------------------------------------------------

def get_analytics_summary(
    asset_id=None,
    operator_id=None,
    event_type=None,
    min_severity=None,
    from_ts=None,
    to_ts=None,
):
    """
    Summarise events into metrics matching the requested filters.
    Executes multiple aggregations dynamically using standard sqlite3.
    """
    where_sql, params = _build_events_where_clause(
        asset_id, operator_id, event_type, min_severity, from_ts, to_ts
    )
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Total + Avg Severity
        cursor.execute(f"SELECT COUNT(*) as total, AVG(severity) as avg_sev FROM events{where_sql}", params)
        row = cursor.fetchone()
        total_events = row["total"] if row and row["total"] else 0
        avg_severity = row["avg_sev"] if total_events > 0 else None
        
        # 2. Counts by type
        cursor.execute(f"SELECT type, COUNT(*) as c FROM events{where_sql} GROUP BY type", params)
        counts_by_type = {r["type"]: r["c"] for r in cursor.fetchall()}
        
        # 3. Counts by severity (always ensure 1..5 exist)
        cursor.execute(f"SELECT severity, COUNT(*) as c FROM events{where_sql} GROUP BY severity", params)
        db_sev_counts = {str(r["severity"]): r["c"] for r in cursor.fetchall()}
        counts_by_severity = {str(i): db_sev_counts.get(str(i), 0) for i in range(1, 6)}
        
        # 4. Top 3 assets
        cursor.execute(f"SELECT asset_id, COUNT(*) as c FROM events{where_sql} GROUP BY asset_id ORDER BY c DESC LIMIT 3", params)
        top_assets = [{"asset_id": r["asset_id"], "count": r["c"]} for r in cursor.fetchall()]
        
        # 5. Top 3 operators (exclude NULL)
        op_where = where_sql
        if op_where:
            op_where += " AND operator_id IS NOT NULL"
        else:
            op_where = " WHERE operator_id IS NOT NULL"
            
        cursor.execute(f"SELECT operator_id, COUNT(*) as c FROM events{op_where} GROUP BY operator_id ORDER BY c DESC LIMIT 3", params)
        top_operators = [{"operator_id": r["operator_id"], "count": r["c"]} for r in cursor.fetchall()]
        
    finally:
        conn.close()

    # Match the AnalyticsSummary schema exactly
    return {
        "filters": {
            "asset_id": asset_id,
            "operator_id": operator_id,
            "type": event_type,
            "min_severity": min_severity,
            "from_ts": from_ts,
            "to_ts": to_ts,
        },
        "total_events": total_events,
        "avg_severity": avg_severity,
        "counts_by_type": counts_by_type,
        "counts_by_severity": counts_by_severity,
        "top_assets": top_assets,
        "top_operators": top_operators,
    }

# ---------------------------------------------------------------------------
# Health Score helpers (Phase 4)
# ---------------------------------------------------------------------------

def get_health_score_stats(from_ts, to_ts, asset_id=None, operator_id=None):
    """
    Get raw aggregates required for the health score formula within a specific time range.
    """
    where_sql, params = _build_events_where_clause(
        asset_id=asset_id,
        operator_id=operator_id,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = f"""
            SELECT 
                COUNT(*) as total_events,
                SUM(severity) as severity_sum,
                SUM(CASE WHEN severity >= 4 THEN 1 ELSE 0 END) as high_sev_count,
                SUM(CASE WHEN type = 'error' THEN 1 ELSE 0 END) as error_count
            FROM events
            {where_sql}
        """
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        return {
            "total_events": row["total_events"] if row and row["total_events"] is not None else 0,
            "severity_sum": row["severity_sum"] if row and row["severity_sum"] is not None else 0,
            "high_sev_count": row["high_sev_count"] if row and row["high_sev_count"] is not None else 0,
            "error_count": row["error_count"] if row and row["error_count"] is not None else 0,
        }
    finally:
        conn.close()


def get_burst_assets(burst_start, burst_end, asset_id=None, operator_id=None):
    """
    Rule A: Get assets that have >= 5 events in the burst window.
    """
    where_sql, params = _build_events_where_clause(
        asset_id=asset_id,
        operator_id=operator_id,
        from_ts=burst_start,
        to_ts=burst_end,
    )
    conn = get_db_connection()
    try:
        query = f"""
            SELECT asset_id, COUNT(*) as c
            FROM events
            {where_sql}
            GROUP BY asset_id
            HAVING c >= 5
            ORDER BY c DESC
        """
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [{"asset_id": r["asset_id"], "count": r["c"]} for r in cursor.fetchall()]
    finally:
        conn.close()


def get_event_ids_by_rule(rule_condition, start, end, asset_id=None, operator_id=None):
    """
    Rule B & C: Return dict mapping asset_id -> list of event ids matching the condition.
    """
    where_sql, params = _build_events_where_clause(
        asset_id=asset_id,
        operator_id=operator_id,
        from_ts=start,
        to_ts=end,
    )
    if where_sql:
        where_sql += f" AND {rule_condition}"
    else:
        where_sql = f" WHERE {rule_condition}"

    conn = get_db_connection()
    try:
        query = f"""
            SELECT id, asset_id
            FROM events
            {where_sql}
            ORDER BY id DESC
        """
        cursor = conn.cursor()
        cursor.execute(query, params)
        groups = {}
        for r in cursor.fetchall():
            a_id = r["asset_id"]
            if a_id not in groups:
                groups[a_id] = []
            groups[a_id].append(r["id"])
        return groups
    finally:
        conn.close()
