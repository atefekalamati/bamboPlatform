import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "test_smart_building.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    for module_name in ["app.database", "app.models", "app.main", "app.models.building", "app.models.equipment", "app.models.sensor"]:
        sys.modules.pop(module_name, None)

    import app.database as database
    import app.main as main_module

    database = importlib.reload(database)
    main_module = importlib.reload(main_module)
    database.init_db()

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
