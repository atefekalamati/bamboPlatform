import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BOOTSTRAP_MOBILE = "09150000000"


@pytest.fixture
def client(monkeypatch, tmp_path):
    database_path = tmp_path / "test_bambo.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_SECRET", "test-secret-not-for-production")
    monkeypatch.setenv("BOOTSTRAP_SUPER_ADMIN_MOBILE", BOOTSTRAP_MOBILE)

    import app.database as database
    import app.main as main_module

    database.init_db()
    with TestClient(main_module.app) as test_client:
        yield test_client


def login_with_otp(client, mobile: str) -> dict[str, str]:
    request_response = client.post("/auth/otp/request", json={"mobile": mobile})
    assert request_response.status_code == 200
    request_body = request_response.json()
    assert request_body["debug_code"]

    verify_response = client.post(
        "/auth/otp/verify",
        json={
            "request_id": request_body["request_id"],
            "code": request_body["debug_code"],
        },
    )
    assert verify_response.status_code == 200
    return {"Authorization": f"Bearer {verify_response.json()['access_token']}"}


@pytest.fixture
def super_admin_headers(client):
    return login_with_otp(client, BOOTSTRAP_MOBILE)
