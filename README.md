# Event Analytics API

[![Tests](https://github.com/sameelhaider32/event-analytics-api/actions/workflows/tests.yml/badge.svg)](https://github.com/sameelhaider32/event-analytics-api/actions/workflows/tests.yml)

A robust, lightweight REST API for ingesting, querying, and analyzing operational events over disparate assets. It dynamically tracks metrics, evaluates real-time functional health, and surfaces rule-based alerts tailored to infrastructure monitoring.

---

## Quickstart (Windows PowerShell)

### 1. Setup Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### 2. Start the API
```powershell
uvicorn app.main:app --reload
```
Interactive Swagger documentation will be immediately accessible locally at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Run Tests
The test suite utilizes functional execution environments resolving dynamically independent states across cases.
```powershell
python -m pytest tests/ -v
```

---

## Database Configuration

The application natively uses a local SQLite database (`app.db`). To map persistent states cleanly locally or across production, bind the following environment variables:
- `EVENT_ANALYTICS_DB_PATH` (Preferred) 
- `REST_PROJECT_DB_PATH` (Legacy Backwards Compatibility)

If neither are supplied, it securely generates and leverages `./app.db` natively.

---

## Example Usage (cURL)

**1. Create an Asset**
```powershell
curl -X POST http://127.0.0.1:8000/assets -H "Content-Type: application/json" -d '{"name": "Database Node A", "type": "server"}'
```

**2. Create an Operator**
```powershell
curl -X POST http://127.0.0.1:8000/operators -H "Content-Type: application/json" -d '{"name": "System Administrator"}'
```

**3. Bulk Post Events**
```powershell
curl -X POST http://127.0.0.1:8000/events -H "Content-Type: application/json" -d '[{"timestamp":"2026-03-25T10:00:00Z", "asset_id":"1", "event_type":"disk_full", "severity":4}, {"timestamp":"2026-03-25T10:05:00Z", "asset_id":"1", "event_type":"login", "severity":1}]'
```

**4. Evaluate Analytics Summary**
```powershell
curl -X GET "http://127.0.0.1:8000/analytics/summary?min_severity=3"
```

**5. Query Active Alerts**
```powershell
curl -X GET "http://127.0.0.1:8000/alerts"
```

---

## API Endpoints List

| Method | Path                         | Usage                                 |
|--------|------------------------------|---------------------------------------|
| GET    | `/health`                    | Database reachability check           |
| POST   | `/assets`                    | Asset provisioning                    |
| GET    | `/assets/{asset_id}`         | Asset querying                        |
| POST   | `/operators`                 | Operator provisioning                 |
| GET    | `/operators/{operator_id}`   | Operator querying                     |
| POST   | `/events`                    | Single / Bulk event ingestion         |
| GET    | `/events`                    | Event ledger w/ boundary filters      |
| GET    | `/analytics/summary`         | Real-time aggregated metrics          |
| GET    | `/score/health`              | Time-bounded health calculations      |
| GET    | `/alerts`                    | Active rule-flagged alert evaluations |

---

## Docker Execution

The application natively bundles containerized images via `Dockerfile` bridging directly over `docker-compose.yml`.
```powershell
docker compose up --build -d
```
State mappings natively decouple the local db into `./data/app.db` ensuring persistent bindings survive container teardowns.
