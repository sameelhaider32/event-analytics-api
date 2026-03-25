# Event Analytics API

[![Tests](https://github.com/sameelhaider32/event-analytics-api/actions/workflows/tests.yml/badge.svg)](https://github.com/sameelhaider32/event-analytics-api/actions/workflows/tests.yml)

> A small, practical REST API that lets you **log operational events**, **query them later**, and get quick insights like a **summary**, an explainable **health score (0–100)**, and **rule-based alerts**.

---

## ✨ What this project does

This API is useful for anything that produces events: **services, servers, devices, apps**, or any general “asset”.

It supports:

- ✅ Assets & Operators management  
- ✅ Event ingestion (single + bulk)  
- ✅ Event querying with filters (time, severity, type, asset, operator)  
- ✅ Analytics summary (counts, averages, top assets/operators)  
- ✅ Health score (0–100) with breakdown  
- ✅ Alerts (burst, critical severity, unauthorized activity)  
- ✅ Optional Streamlit UI dashboard

---

## 🚀 Quickstart (Windows PowerShell)

### 1) Set up a virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### 2) Start the API
```powershell
uvicorn app.main:app --reload
```

Open:
- Swagger docs: http://127.0.0.1:8000/docs  
- Health check: http://127.0.0.1:8000/health  

---

## ✅ Run tests

```powershell
python -m pytest -v
```

> Tests use an isolated temporary SQLite database (they do **not** depend on your local `app.db`).

---

## 🗄️ Database (SQLite)

By default the API uses:
- `./app.db`

You can override the DB file location using:

- `EVENT_ANALYTICS_DB_PATH` *(preferred)*
- `REST_PROJECT_DB_PATH` *(legacy / backwards compatible)*

Example:
```powershell
$env:EVENT_ANALYTICS_DB_PATH = "C:\temp\event_analytics.db"
uvicorn app.main:app --reload
```

---

## 🖥️ Optional UI (Streamlit Dashboard)

A lightweight Streamlit dashboard is included to explore the API without curl.

### Terminal 1 — Run the API
```powershell
.\venv\Scripts\Activate
uvicorn app.main:app --reload
```

### Terminal 2 — Run the UI
```powershell
.\venv\Scripts\Activate
pip install -r requirements-ui.txt
streamlit run ui/streamlit_app.py
```

Streamlit opens at:
- http://localhost:8501

In the UI, set the API base URL to:
- `http://127.0.0.1:8000`

---

## 🧪 Example usage (cURL)

> Tip: You can also run everything from Swagger UI at `/docs`.

### 1) Create an Asset
```powershell
curl -X POST http://127.0.0.1:8000/assets `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Database Node A\",\"type\":\"server\"}"
```

### 2) Create an Operator
```powershell
curl -X POST http://127.0.0.1:8000/operators `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"System Administrator\"}"
```

### 3) Post a Single Event
```powershell
curl -X POST http://127.0.0.1:8000/events `
  -H "Content-Type: application/json" `
  -d "{\"timestamp\":\"2026-03-25T10:00:00Z\",\"asset_id\":\"<ASSET_ID>\",\"operator_id\":null,\"event_type\":\"disk_full\",\"severity\":4,\"metadata\":{}}"
```

### 4) Bulk Post Events
```powershell
curl -X POST http://127.0.0.1:8000/events `
  -H "Content-Type: application/json" `
  -d "[{`"timestamp`":`"2026-03-25T10:00:00Z`",`"asset_id`":`"<ASSET_ID>`",`"event_type`":`"disk_full`",`"severity`":4,`"metadata`":{}},
       {`"timestamp`":`"2026-03-25T10:05:00Z`",`"asset_id`":`"<ASSET_ID>`",`"event_type`":`"login`",`"severity`":1,`"metadata`":{}}]"
```

### 5) Query Events (filters)
```powershell
curl "http://127.0.0.1:8000/events?asset_id=<ASSET_ID>&min_severity=3&event_type=disk_full"
```

### 6) Analytics Summary
```powershell
curl "http://127.0.0.1:8000/analytics/summary?min_severity=3"
```

### 7) Health Score (time-bounded)
```powershell
curl "http://127.0.0.1:8000/score/health?from_ts=2026-03-25T00:00:00Z&to_ts=2026-03-26T00:00:00Z"
```

### 8) Alerts
```powershell
curl "http://127.0.0.1:8000/alerts?from_ts=2026-03-25T00:00:00Z&to_ts=2026-03-26T00:00:00Z"
```

---

## 🧭 Endpoints overview

<details>
<summary><strong>Core</strong></summary>

- `GET /health`
- `GET /docs`
</details>

<details>
<summary><strong>Assets</strong></summary>

- `POST /assets`
- `GET /assets`
- `GET /assets/{asset_id}`
</details>

<details>
<summary><strong>Operators</strong></summary>

- `POST /operators`
- `GET /operators`
- `GET /operators/{operator_id}`
</details>

<details>
<summary><strong>Events</strong></summary>

- `POST /events` *(single or bulk)*
- `GET /events` *(filters supported)*
- `GET /events/{event_id}`
</details>

<details>
<summary><strong>Analytics</strong></summary>

- `GET /analytics/summary`
</details>

<details>
<summary><strong>Health Score</strong></summary>

- `GET /score/health`
</details>

<details>
<summary><strong>Alerts</strong></summary>

- `GET /alerts`
</details>

---

## 🐳 Docker (optional)

```powershell
docker compose up --build
```

This setup stores the SQLite DB under `./data/app.db` so your data survives container restarts.

---

## 🧱 Project structure

```text
app/            # FastAPI application code
tests/          # pytest test suite
ui/             # optional Streamlit UI
requirements.txt
requirements-ui.txt
Dockerfile
docker-compose.yml
```

---

## 🔮 Future improvements (nice-to-have)

- Add indexes on `timestamp` / `asset_id` for faster queries at scale  
- Add configurable alert thresholds (instead of hardcoded rules)  
- Add auth (API key / JWT) for real deployments  
- Add pagination defaults everywhere and clearer bulk ingest error reporting  
