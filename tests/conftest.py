import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def setup_test_env(tmp_path_factory):
    # 1) Create a temporary database file in tmp_path
    db_path = tmp_path_factory.mktemp("data") / "test_app.db"
    
    # 2) Set REST_PROJECT_DB_PATH using environ so app.db dynamically picks it up
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
