import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = tmp_path / "test_smart_building.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import app.database as database
    import app.main as main_module

    database.init_db()

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_building_equipment_sensor_crud(client):
    building_response = client.post(
        "/buildings",
        json={"name": "Bamboo Tower", "address": "Mashhad", "total_floors": 12},
    )
    assert building_response.status_code == 200
    building = building_response.json()

    equipment_response = client.post(
        "/equipment",
        json={
            "name": "HVAC-01",
            "equipment_type": "HVAC",
            "building_id": building["id"],
        },
    )
    assert equipment_response.status_code == 200
    equipment = equipment_response.json()

    sensor_response = client.post(
        "/sensors",
        json={
            "name": "Temp-01",
            "sensor_type": "temperature",
            "unit": "°C",
            "equipment_id": equipment["id"],
        },
    )
    assert sensor_response.status_code == 200
    sensor = sensor_response.json()

    update_response = client.put(
        f"/sensors/{sensor['id']}",
        json={"status": "inactive"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "inactive"

    assert client.get(f"/buildings/{building['id']}").status_code == 200
    assert len(client.get("/equipment").json()) == 1
    assert len(client.get("/sensors").json()) == 1

    assert client.delete(f"/equipment/{equipment['id']}").status_code == 200
    assert client.get(f"/sensors/{sensor['id']}").status_code == 404


def test_parent_references_must_exist(client):
    equipment_response = client.post(
        "/equipment",
        json={"name": "HVAC-01", "equipment_type": "HVAC", "building_id": 999},
    )
    assert equipment_response.status_code == 404
    assert equipment_response.json()["detail"] == "Building not found"

    sensor_response = client.post(
        "/sensors",
        json={"name": "Temp-01", "sensor_type": "temperature", "equipment_id": 999},
    )
    assert sensor_response.status_code == 404
    assert sensor_response.json()["detail"] == "Equipment not found"


STAGE_1_CHECKLIST = {
    "project_active": True,
    "imaging_value": True,
    "decision_maker_available": True,
    "safe_access": True,
    "dwg_available": True,
    "not_demo_only": True,
    "cooperation_capacity": True,
}

STAGE_2_CHECKLIST = {
    "introduction_completed": True,
    "site_coordinator_registered": True,
    "imaging_consent": True,
    "feedback_consent": True,
}


def create_pilot(client):
    response = client.post(
        "/pilots",
        json={"display_name": "مالک نمونه - مشهد", "pilot_year": 1405},
    )
    assert response.status_code == 201
    return response.json()


def test_pilot_creation_builds_prd_stage_and_gate_structure(client):
    pilot = create_pilot(client)

    assert pilot["code"] == "PIL-1405-001"
    assert pilot["project_system_name"] == "project-1"
    assert pilot["current_stage"] == 1
    assert len(pilot["stages"]) == 19
    assert pilot["stages"][0]["status"] == "open"
    assert all(stage["status"] == "locked" for stage in pilot["stages"][1:])
    assert [gate["code"] for gate in pilot["gates"]] == ["G1", "G2", "G3", "G4", "G5"]


def test_locked_stage_cannot_be_submitted(client):
    pilot = create_pilot(client)

    response = client.post(
        f"/pilots/{pilot['id']}/stages/2/submit",
        json={"form_data": {}, "checklist": {}, "submitted_by": "کاربر فروش"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "STAGE_LOCKED"
    assert response.json()["stage"] == 2
    assert response.json()["trace_id"]


def test_stage_validation_returns_field_level_error_contract(client):
    pilot = create_pilot(client)

    response = client.post(
        f"/pilots/{pilot['id']}/stages/1/submit",
        json={
            "form_data": {"owner_name": "مالک نمونه"},
            "checklist": {"project_active": True},
            "submitted_by": "کاربر فروش",
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "STAGE_VALIDATION_FAILED"
    assert body["message"] == "مرحله قابل تأیید نیست."
    assert body["stage"] == 1
    assert {error["field"] for error in body["errors"]} >= {
        "form_data.project_address",
        "checklist.imaging_value",
    }


def test_rejection_revision_gate_and_immutable_snapshots(client):
    pilot = create_pilot(client)
    pilot_id = pilot["id"]

    stage_1_submit = client.post(
        f"/pilots/{pilot_id}/stages/1/submit",
        json={
            "form_data": {"owner_name": "مالک نمونه", "project_address": "مشهد"},
            "checklist": STAGE_1_CHECKLIST,
            "submitted_by": "کاربر فروش",
        },
    )
    assert stage_1_submit.status_code == 200
    assert stage_1_submit.json()["submission"]["version"] == 1

    stage_1_approve = client.post(
        f"/pilots/{pilot_id}/stages/1/approve",
        json={"reviewer": "مدیر پایلوت"},
    )
    assert stage_1_approve.status_code == 200
    assert stage_1_approve.json()["snapshot"]["content_hash"]

    pilot_after_stage_1 = client.get(f"/pilots/{pilot_id}").json()
    assert pilot_after_stage_1["current_stage"] == 2
    assert pilot_after_stage_1["stages"][1]["status"] == "open"
    assert pilot_after_stage_1["gates"][0]["status"] == "locked"

    stage_2_submit = client.post(
        f"/pilots/{pilot_id}/stages/2/submit",
        json={
            "form_data": {"site_coordinator_phone": "09150000000"},
            "checklist": STAGE_2_CHECKLIST,
            "submitted_by": "ارتباط مشتری",
        },
    )
    assert stage_2_submit.status_code == 200

    missing_reason = client.post(
        f"/pilots/{pilot_id}/stages/2/reject",
        json={"reviewer": "مدیر پایلوت"},
    )
    assert missing_reason.status_code == 422

    rejected = client.post(
        f"/pilots/{pilot_id}/stages/2/reject",
        json={
            "reviewer": "مدیر پایلوت",
            "correction_items": ["شماره هماهنگ‌کننده محل بازبینی شود"],
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["stage"]["status"] == "needs_revision"

    revised = client.post(
        f"/pilots/{pilot_id}/stages/2/submit",
        json={
            "form_data": {"site_coordinator_phone": "09151111111"},
            "checklist": STAGE_2_CHECKLIST,
            "submitted_by": "ارتباط مشتری",
        },
    )
    assert revised.status_code == 200
    assert revised.json()["submission"]["version"] == 2

    approved = client.post(
        f"/pilots/{pilot_id}/stages/2/approve",
        json={"reviewer": "مدیر پایلوت"},
    )
    assert approved.status_code == 200
    assert approved.json()["snapshot"]["version"] == 2

    pilot_after_g1 = client.get(f"/pilots/{pilot_id}").json()
    assert pilot_after_g1["current_stage"] == 3
    assert pilot_after_g1["gates"][0]["status"] == "passed"
    assert pilot_after_g1["status"] == "waiting_documents"

    stage_1_snapshots = client.get(f"/pilots/{pilot_id}/stages/1/snapshots").json()
    stage_2_snapshots = client.get(f"/pilots/{pilot_id}/stages/2/snapshots").json()
    assert len(stage_1_snapshots) == 1
    assert len(stage_2_snapshots) == 1
    assert stage_2_snapshots[0]["content"]["submission"]["version"] == 2
    assert len(stage_2_snapshots[0]["content_hash"]) == 64

    from app.database import get_session
    from app.models import ImmutableSnapshot

    with get_session() as session:
        snapshot = session.get(ImmutableSnapshot, stage_2_snapshots[0]["id"])
        snapshot.content = {"tampered": True}
        with pytest.raises(ValueError, match="immutable"):
            session.commit()
