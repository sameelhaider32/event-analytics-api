# Event Analytics API

A robust, lightweight REST API for ingesting, querying, and analyzing operational events over disparate assets. It dynamically tracks metrics, evaluates real-time functional health, and surfaces rule-based alerts tailored to infrastructure monitoring.

---

## Features

- **Assets & Operators CRUD**: Native identifiers and metadata tracking.
- **Event Ingestion**: Supports single-event and high-throughput bulk event streaming.
- **Event Querying**: Deep filtering capabilities (by asset, severity thresholds, time-boundaries).
- **Analytics Summary**: Real-time severity aggregations, metrics counts, and top entity tracking.
- **Health Score**: A dynamically calculated `0–100` system evaluating penalty deductions based on recent anomalies.
- **Alerts**: Rule-based evaluations triggering on critical failures, unauthorized access, and sustained anomaly bursts.

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **Database**: SQLite3 (native standard library)
- **Testing**: `pytest` & `httpx` with `tmp_path` session isolation hooks
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions workflows

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
The test suite spans across multiple constraint boundaries evaluating 36 unique cases idempotently.
```powershell
python -m pytest tests/ -v
```

---

## Database Configuration

The application natively uses a local SQLite database (`app.db`) situated at the root of the project. 
To securely route persistent data locally or during isolated test evaluations, the system reads from the `REST_PROJECT_DB_PATH` environment variable. If omitted, it securely defaults to `./app.db`.

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
curl -X POST http://127.0.0.1:8000/events -H "Content-Type: application/json" -d '[{"timestamp":"2026-03-25T10:00:00Z", "asset_id":"ast_123", "type":"disk_full", "severity":4}, {"timestamp":"2026-03-25T10:05:00Z", "asset_id":"ast_123", "type":"login", "severity":1}]'
```

**4. Evaluate Analytics Summary**
```powershell
curl -X GET "http://127.0.0.1:8000/analytics/summary?min_severity=3"
```

**5. Query Dynamic Health Score**
```powershell
curl -X GET "http://127.0.0.1:8000/score/health?window_hours=24"
```

---

## API Endpoints Overview

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

## CI/CD and Containerization

### GitHub Actions
A configured Push and Pull Request workflow securely triggers on `ubuntu-latest` nodes native to GitHub. This executes the entire suite (`pytest`) in containerized isolation on the active `main` branch.

### Docker
The application is pre-packaged alongside a portable `Dockerfile` bridging directly into `docker-compose.yml`.
```powershell
docker compose up --build -d
```
State mappings natively isolate the local db into `./data/app.db` ensuring persistency across container builds.

---

## Project Structure

```text
REST Project/
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI application, Core Endpoints
│   ├── db.py         # SQLite connection mappings and aggregations
│   └── schemas.py    # Pydantic models handling boundary validations
├── tests/
│   ├── conftest.py   # Global mock isolation fixtures
│   ├── test_phase*.py  # Functional Phase boundaries
├── .github/workflows/
│   └── tests.yml     # Automated integrations CI pipeline
├── Dockerfile        # Container builds
├── docker-compose.yml# Volume management orchestrations
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Future Improvements

- **Authentication / Authorization**: Implementing OAuth2/JWT bindings preventing unauthorized entity manipulations.
- **Dynamic Rules System**: Upgrading the `/alerts` boundaries with customized rule configuration schemas directly persisting evaluating parameters dynamically.
- **Relational ORM Overhaul**: Migrating from raw `sqlite3` driver queries to `SQLAlchemy` permitting expanded asynchronous query scalability mappings and dynamic indexing strategies.
- **Time-Series Metric Archiving**: Offloading massive timestamp aggregation sets iteratively into partitioned cold-storage blocks for analytics bounding limits.
