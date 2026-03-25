import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def setup_test_env(tmp_path_factory):
    # 1) Create a temporary database file in tmp_path
    db_path = tmp_path_factory.mktemp("data") / "test_app.db"
    
    # 2) Set DB path variables natively picking them up
    os.environ["EVENT_ANALYTICS_DB_PATH"] = str(db_path)
    os.environ["REST_PROJECT_DB_PATH"] = str(db_path)
    
    yield
    
    # Teardown: not strictly necessary as tmp_path_factory cleans up after sessions, but good practice
    pass

@pytest.fixture(scope="module")
def client():
    # 3) Imports app AFTER to ensure the mocked path operates natively
    from app.main import app
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def reset_db_per_test():
    """Ensure database is clean before EVERY test runs natively guaranteeing order-independence."""
    from app.db import get_db_connection
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM assets")
        conn.execute("DELETE FROM operators")
        conn.commit()
    except Exception:
        pass  # Just in case tables aren't perfectly compiled yet at earliest initialization boundaries
    finally:
        conn.close()
