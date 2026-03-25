import streamlit as st
import httpx
import json
from datetime import datetime, timezone

st.set_page_config(page_title="Event Analytics Dashboard", layout="wide")

st.title("Event Analytics Dashboard")

st.sidebar.header("Configuration")
api_base_url = st.sidebar.text_input("API Base URL", "http://127.0.0.1:8000")

tab_overview, tab_assets, tab_operators, tab_events, tab_analytics, tab_health, tab_alerts = st.tabs([
    "Overview", "Assets", "Operators", "Events", "Analytics", "Health", "Alerts"
])

# Helper functions
def api_get(endpoint, params=None):
    try:
        response = httpx.get(f"{api_base_url}{endpoint}", params=params, timeout=10)
        return response.status_code, response.json() if response.text else None
    except Exception as e:
        return 500, str(e)

def api_post(endpoint, json_data):
    try:
        response = httpx.post(f"{api_base_url}{endpoint}", json=json_data, timeout=10)
        return response.status_code, response.json() if response.text else None
    except Exception as e:
        return 500, str(e)

# --- OVERVIEW ---
with tab_overview:
    st.header("Overview")
    if st.button("Check /health"):
        status, data = api_get("/health")
        if status == 200:
            st.success("API is healthy!")
            st.json(data)
        else:
            st.error(f"Error {status}")
            st.write(data)
    st.markdown(f"**Interactive API Docs:** [{api_base_url}/docs]({api_base_url}/docs)")

# --- ASSETS ---
with tab_assets:
    st.header("Assets")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Asset")
        with st.form("add_asset_form"):
            a_id = st.text_input("Asset ID (Optional, leave blank for auto)")
            a_name = st.text_input("Name")
            a_type = st.text_input("Type")
            submitted = st.form_submit_button("Add Asset")
            if submitted:
                payload = {"name": a_name, "type": a_type}
                if a_id: payload["id"] = a_id
                status, data = api_post("/assets", payload)
                if status == 201: st.success("Created!"); st.json(data)
                else: st.error(f"Error {status}"); st.write(data)
                
    with col2:
        st.subheader("List Assets")
        if st.button("Refresh Assets"):
            status, data = api_get("/assets")
            if status == 200: st.json(data)
            else: st.error(f"Error {status}"); st.write(data)

# --- OPERATORS ---
with tab_operators:
    st.header("Operators")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Operator")
        with st.form("add_operator_form"):
            o_id = st.text_input("Operator ID (Optional)")
            o_name = st.text_input("Name")
            submitted = st.form_submit_button("Add Operator")
            if submitted:
                payload = {"name": o_name}
                if o_id: payload["id"] = o_id
                status, data = api_post("/operators", payload)
                if status == 201: st.success("Created!"); st.json(data)
                else: st.error(f"Error {status}"); st.write(data)
                
    with col2:
        st.subheader("List Operators")
        if st.button("Refresh Operators"):
            status, data = api_get("/operators")
            if status == 200: st.json(data)
            else: st.error(f"Error {status}"); st.write(data)

# --- EVENTS ---
with tab_events:
    st.header("Events")
    st.subheader("Submit Single Event")
    with st.form("submit_event_form"):
        e_ts = st.text_input("Timestamp (ISO 8601)", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        e_asset = st.text_input("Asset ID (Required)")
        e_op = st.text_input("Operator ID (Optional)")
        e_type = st.text_input("Event Type (Required)")
        e_severity = st.number_input("Severity (1-5)", min_value=1, max_value=5, value=1)
        e_meta = st.text_area("Metadata (JSON)", "{}")
        if st.form_submit_button("Submit Event"):
            try:
                meta_json = json.loads(e_meta) if e_meta.strip() else {}
                payload = {
                    "timestamp": e_ts,
                    "asset_id": e_asset,
                    "event_type": e_type,
                    "severity": e_severity,
                    "metadata": meta_json
                }
                if e_op: payload["operator_id"] = e_op
                status, data = api_post("/events", payload)
                if status == 201: st.success("Created!"); st.json(data)
                else: st.error(f"Error {status}"); st.write(data)
            except json.JSONDecodeError:
                st.error("Invalid Metadata JSON")

    st.subheader("Submit Bulk Events")
    with st.form("submit_bulk_events_form"):
        bulk_json = st.text_area("Events (JSON List)", "[\n  {\n    \"timestamp\": \"2026-03-25T10:00:00Z\",\n    \"asset_id\": \"asset_1\",\n    \"event_type\": \"test\",\n    \"severity\": 1\n  }\n]")
        if st.form_submit_button("Submit Bulk"):
            try:
                payload = json.loads(bulk_json)
                status, data = api_post("/events", payload)
                if status == 201: st.success("Created!"); st.json(data)
                else: st.error(f"Error {status}"); st.write(data)
            except json.JSONDecodeError:
                st.error("Invalid Bulk JSON")

# --- ANALYTICS ---
with tab_analytics:
    st.header("Analytics Summary")
    with st.form("analytics_form"):
        an_asset = st.text_input("Asset ID")
        an_op = st.text_input("Operator ID")
        an_type = st.text_input("Event Type")
        an_min_sev = st.number_input("Min Severity", min_value=1, max_value=5, value=1)
        an_from = st.text_input("From Timestamp")
        an_to = st.text_input("To Timestamp")
        if st.form_submit_button("Get Summary"):
            params = {}
            if an_asset: params["asset_id"] = an_asset
            if an_op: params["operator_id"] = an_op
            if an_type: params["event_type"] = an_type
            if an_min_sev > 1: params["min_severity"] = an_min_sev
            if an_from: params["from_ts"] = an_from
            if an_to: params["to_ts"] = an_to
            status, data = api_get("/analytics/summary", params)
            if status == 200: st.json(data)
            else: st.error(f"Error {status}"); st.write(data)

# --- HEALTH ---
with tab_health:
    st.header("Health Score")
    with st.form("health_form"):
        h_window = st.number_input("Window Hours", min_value=1, max_value=168, value=24)
        h_asset = st.text_input("Asset ID")
        if st.form_submit_button("Get Health Score"):
            params = {"window_hours": h_window}
            if h_asset: params["asset_id"] = h_asset
            status, data = api_get("/score/health", params)
            if status == 200: st.json(data)
            else: st.error(f"Error {status}"); st.write(data)

# --- ALERTS ---
with tab_alerts:
    st.header("Active Alerts")
    with st.form("alerts_form"):
        al_window = st.number_input("Window Hours", min_value=1, max_value=168, value=24)
        al_asset = st.text_input("Asset ID")
        al_op = st.text_input("Operator ID")
        if st.form_submit_button("Get Alerts"):
            params = {"window_hours": al_window}
            if al_asset: params["asset_id"] = al_asset
            if al_op: params["operator_id"] = al_op
            status, data = api_get("/alerts", params)
            if status == 200: st.json(data)
            else: st.error(f"Error {status}"); st.write(data)
