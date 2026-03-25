# REST Project

A lightweight REST API built with **FastAPI** and **SQLite**.
Currently at **Phase 5** — dynamic rule-based alerts on top of the Phase 0–4 foundation.

---

## Local Setup (Windows PowerShell)

```powershell
# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload
```

## Run Tests
The test suite spans Phase 1 to Phase 5 constraints using a generalized `conftest.py` fixture isolating databases dynamically into temporary routes.
```powershell
python -m pytest tests/ -v
```

## Docker (optional)
You can directly spin up the database and web-server isolated behind a pre-compiled Container pointing persistently towards `./data` volumes natively configuring DB locations.
```powershell
docker compose up --build -d
```
The localized container respects standard `http://localhost:8000/docs`.

## Continuous Integration (CI)
Configured cleanly on push/PR via GitHub Actions, running automated `ubuntu-latest` checks dynamically testing standard `conftest.py` states isolating Phase conditions over the root branch.

---

## Endpoints

| Method | Path                         | Description                              |
|--------|------------------------------|------------------------------------------|
| GET    | `/health`                    | Service & database health                |
| POST   | `/assets`                    | Create an asset                          |
| GET    | `/assets`                    | List all assets                          |
| GET    | `/assets/{asset_id}`         | Get asset by id                          |
| POST   | `/operators`                 | Create an operator                       |
| GET    | `/operators`                 | List all operators                       |
| GET    | `/operators/{operator_id}`   | Get operator by id                       |
| POST   | `/events`                    | Create event(s) — single or bulk         |
| GET    | `/events`                    | List/filter events (query params below)  |
| GET    | `/events/{event_id}`         | Get event by id                          |
| GET    | `/analytics/summary`         | Summarize events by filters              |
| GET    | `/score/health`              | Calculate 0-100 health score             |
| GET    | `/alerts`                    | Evaluate recent events for alert rules   |
| GET    | `/docs`                      | Interactive Swagger UI (auto)            |

### GET /events query parameters

| Param          | Type   | Default | Description                        |
|----------------|--------|---------|------------------------------------|
| `asset_id`     | string | —       | Filter by asset                    |
| `operator_id`  | string | —       | Filter by operator                 |
| `type`         | string | —       | Filter by event type               |
| `min_severity` | int    | —       | Only events with severity ≥ value  |
| `from_ts`      | string | —       | Events at or after this ISO time   |
| `to_ts`        | string | —       | Events at or before this ISO time  |
| `limit`        | int    | 100     | Max rows returned (1–500)          |
| `offset`       | int    | 0       | Pagination offset                  |

---

## Example Requests

### Health check

```powershell
curl http://127.0.0.1:8000/health
```

```json
{ "ok": true, "db_ok": true, "service": "rest-project" }
```

### Create an asset

```powershell
curl -X POST http://127.0.0.1:8000/assets -H "Content-Type: application/json" -d '{"name": "web-server-01", "type": "server"}'
```

```json
{ "id": "a1b2c3...", "name": "web-server-01", "type": "server", "created_at": "2026-03-20T..." }
```

### Create an operator

```powershell
curl -X POST http://127.0.0.1:8000/operators -H "Content-Type: application/json" -d '{"name": "alice"}'
```

```json
{ "id": "d4e5f6...", "name": "alice", "created_at": "2026-03-20T..." }
```

### Create a single event (Phase 2)

```powershell
curl -X POST http://127.0.0.1:8000/events -H "Content-Type: application/json" -d '{"timestamp":"2026-03-20T10:00:00Z","asset_id":"a1b2c3...","type":"cpu_spike","severity":3}'
```

```json
{ "id": 1, "timestamp": "2026-03-20T10:00:00Z", "asset_id": "a1b2c3...", "operator_id": null, "type": "cpu_spike", "severity": 3, "metadata": {} }
```

### Bulk-ingest events (Phase 2)

```powershell
curl -X POST http://127.0.0.1:8000/events -H "Content-Type: application/json" -d '[{"timestamp":"2026-03-20T11:00:00Z","asset_id":"a1b2c3...","type":"disk_full","severity":4},{"timestamp":"2026-03-20T12:00:00Z","asset_id":"a1b2c3...","type":"login","severity":1}]'
```

### Filter events (Phase 2)

```powershell
curl "http://127.0.0.1:8000/events?asset_id=a1b2c3...&min_severity=3"
```

### Basic Analytics Summary (Phase 3)

```powershell
curl http://127.0.0.1:8000/analytics/summary
```

### Filtered Analytics Summary (Phase 3)

```powershell
curl "http://127.0.0.1:8000/analytics/summary?asset_id=a1b2c3...&min_severity=3"
```

### Health Score (Phase 4)

Formula evaluates recent events to generate a 0-100 score:
`Score = 100 - (2 * sum of severities) - (5 * count of high severity events) - (2 * count of errors)`

```powershell
curl "http://127.0.0.1:8000/score/health?from_ts=2026-03-24T00:00:00Z&to_ts=2026-03-25T00:00:00Z"
```

### Alerts (Phase 5)

Evaluates event history against 3 distinct security/reliability rules:
- **Burst**: Triggered if 5 or more events occur within the previous 15 minutes.
- **Critical**: Triggered if *any* severity 5 event occurs.
- **Unauthorized**: Triggered if *any* event of type "unauthorized" occurs.

Alerts over the last 24 hours (default window):
```powershell
curl http://127.0.0.1:8000/alerts
```

Alerts scoped strictly to a specific asset and timeframe:
```powershell
curl "http://127.0.0.1:8000/alerts?asset_id=ast_123&from_ts=2026-03-24T00:00:00Z&to_ts=2026-03-25T00:00:00Z"
```

---

## Project Structure

```
REST Project/
├── app/
│   ├── __init__.py   # Python package marker
│   ├── main.py       # FastAPI app & all endpoints
│   ├── db.py         # SQLite helpers (connect, init, CRUD)
│   └── schemas.py    # Pydantic request/response models
├── tests/
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   └── test_phase5.py
├── requirements.txt
├── .gitignore
└── README.md
```
