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
    monkeypatch.setenv("DWG_STORAGE_ROOT", str(tmp_path / "dwg-storage"))
    monkeypatch.setenv("DWG_MAX_BYTES", str(1024 * 1024))

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


def sample_pilot_payload(total_floors: int = 2) -> dict:
    return {
        "pilot_year": 1405,
        "owner": {
            "name": "شرکت نمونه",
            "decision_maker_name": "مدیر نمونه",
            "decision_maker_position": "مدیرعامل",
            "primary_mobile": "09151111111",
        },
        "project": {
            "name": "پروژه نمونه",
            "total_floors": total_floors,
            "address": "مشهد، بلوار نمونه",
            "progress_stage": "اجرای سازه",
            "customer_need": "مشاهده غیرحضوری پیشرفت",
            "expected_value": "کاهش مراجعه حضوری",
        },
    }


def save_valid_f01(client, pilot_id: int, headers: dict[str, str]) -> dict:
    response = client.put(
        f"/pilots/{pilot_id}/forms/f01",
        json={
            "project_active": True,
            "imaging_value": True,
            "remote_viewing_need": True,
            "access_possible": True,
            "dwg_available": True,
            "continued_capacity": True,
            "not_demo_only": True,
            "introduction_completed": True,
            "imaging_accepted": True,
            "dwg_accepted": True,
            "feedback_accepted": True,
            "coordinator_name": "هماهنگ‌کننده نمونه",
            "coordinator_mobile": "09152222222",
            "result": "approved",
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def super_admin_headers(client):
    return login_with_otp(client, BOOTSTRAP_MOBILE)
