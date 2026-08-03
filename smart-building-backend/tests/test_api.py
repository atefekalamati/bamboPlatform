import pytest

from conftest import login_with_otp, sample_pilot_payload, save_valid_f01
from app.database import get_session
from app.models import PilotStage
from app.schemas.product import FormF01Update

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


def create_pilot(client, headers):
    response = client.post(
        "/pilots",
        json=sample_pilot_payload(),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_stage_2_f01_update_preserves_stage_1_approval_and_snapshot(
    client,
    super_admin_headers,
):
    pilot = create_pilot(client, super_admin_headers)
    pilot_id = pilot["id"]
    saved_f01 = save_valid_f01(client, pilot_id, super_admin_headers)
    stage_1_submit = client.post(
        f"/pilots/{pilot_id}/stages/1/submit",
        json={},
        headers=super_admin_headers,
    )
    assert stage_1_submit.status_code == 200, stage_1_submit.json()
    stage_1_reject = client.post(
        f"/pilots/{pilot_id}/stages/1/reject",
        json={"correction_items": ["بازبینی کنترل مرحله یک"]},
        headers=super_admin_headers,
    )
    assert stage_1_reject.status_code == 200, stage_1_reject.json()
    stage_1_resubmit = client.post(
        f"/pilots/{pilot_id}/stages/1/submit",
        json={},
        headers=super_admin_headers,
    )
    assert stage_1_resubmit.status_code == 200, stage_1_resubmit.json()
    assert stage_1_resubmit.json()["submission"]["version"] == 2
    stage_1_approve = client.post(
        f"/pilots/{pilot_id}/stages/1/approve",
        json={},
        headers=super_admin_headers,
    )
    assert stage_1_approve.status_code == 200, stage_1_approve.json()

    with get_session() as db:
        stage_1 = (
            db.query(PilotStage)
            .filter(PilotStage.pilot_id == pilot_id, PilotStage.number == 1)
            .one()
        )
        approval = stage_1.submissions[-1].review
        snapshot = approval.snapshot
        approval_fingerprint = (
            approval.id,
            approval.submission_id,
            approval.reviewer,
            approval.reviewed_at,
            snapshot.id,
            snapshot.content_hash,
        )

    stage_2_payload = {
        field: saved_f01[field] for field in FormF01Update.model_fields
    }
    stage_2_payload["coordinator_name"] = "هماهنگ‌کننده اصلاح‌شده مرحله دو"
    saved_stage_2 = client.put(
        f"/pilots/{pilot_id}/forms/f01",
        json=stage_2_payload,
        headers=super_admin_headers,
    )
    assert saved_stage_2.status_code == 200, saved_stage_2.json()

    after_save = client.get(
        f"/pilots/{pilot_id}", headers=super_admin_headers
    ).json()
    assert after_save["current_stage"] == 2
    assert after_save["stages"][0]["status"] == "approved"
    assert after_save["stages"][1]["status"] == "open"

    stage_2_submit = client.post(
        f"/pilots/{pilot_id}/stages/2/submit",
        json={"form_data": {}, "checklist": {}},
        headers=super_admin_headers,
    )
    assert stage_2_submit.status_code == 200, stage_2_submit.json()
    assert stage_2_submit.json()["stage"]["number"] == 2
    assert stage_2_submit.json()["stage"]["status"] == "submitted"

    refreshed = client.get(
        f"/pilots/{pilot_id}", headers=super_admin_headers
    ).json()
    assert refreshed["current_stage"] == 2
    assert refreshed["stages"][0]["status"] == "approved"
    assert refreshed["stages"][1]["status"] == "submitted"
    assert refreshed["stages"][2]["status"] == "locked"

    with get_session() as db:
        stage_1 = (
            db.query(PilotStage)
            .filter(PilotStage.pilot_id == pilot_id, PilotStage.number == 1)
            .one()
        )
        approval = stage_1.submissions[-1].review
        snapshot = approval.snapshot
        assert (
            approval.id,
            approval.submission_id,
            approval.reviewer,
            approval.reviewed_at,
            snapshot.id,
            snapshot.content_hash,
        ) == approval_fingerprint

    stage_1_payload = dict(stage_2_payload)
    stage_1_payload["imaging_value"] = False
    changed_stage_1 = client.put(
        f"/pilots/{pilot_id}/forms/f01",
        json=stage_1_payload,
        headers=super_admin_headers,
    )
    assert changed_stage_1.status_code == 200, changed_stage_1.json()
    reopened = client.get(
        f"/pilots/{pilot_id}", headers=super_admin_headers
    ).json()
    assert reopened["current_stage"] == 1
    assert reopened["stages"][0]["status"] == "needs_revision"
    assert reopened["stages"][1]["status"] == "locked"
    assert reopened["stages"][2]["status"] == "locked"


def test_stage_2_submit_is_rejected_until_stage_1_is_approved(
    client,
    super_admin_headers,
):
    pilot = create_pilot(client, super_admin_headers)
    response = client.post(
        f"/pilots/{pilot['id']}/stages/2/submit",
        json={"form_data": {}, "checklist": {}},
        headers=super_admin_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "STAGE_LOCKED"
    assert response.json()["stage"] == 2


def test_stage_decision_is_single_use_and_requires_permission(
    client,
    super_admin_headers,
):
    pilot = create_pilot(client, super_admin_headers)
    save_valid_f01(client, pilot["id"], super_admin_headers)

    sales_role = next(
        role
        for role in client.get("/roles", headers=super_admin_headers).json()
        if role["name"] == "sales"
    )
    sales_user = client.post(
        "/users",
        json={
            "mobile": "09151000004",
            "display_name": "کاربر ارسال مرحله",
            "role_ids": [sales_role["id"]],
        },
        headers=super_admin_headers,
    )
    assert sales_user.status_code == 201
    sales_headers = login_with_otp(client, "09151000004")

    submitted = client.post(
        f"/pilots/{pilot['id']}/stages/1/submit",
        json={},
        headers=sales_headers,
    )
    assert submitted.status_code == 200
    denied = client.post(
        f"/pilots/{pilot['id']}/stages/1/approve",
        json={},
        headers=sales_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "PERMISSION_DENIED"

    approved = client.post(
        f"/pilots/{pilot['id']}/stages/1/approve",
        json={},
        headers=super_admin_headers,
    )
    assert approved.status_code == 200
    repeated = client.post(
        f"/pilots/{pilot['id']}/stages/1/approve",
        json={},
        headers=super_admin_headers,
    )
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "STAGE_TRANSITION_NOT_ALLOWED"

    stage_approvals = [
        item
        for item in client.get(
            "/audit",
            params={"action": "stages.approved"},
            headers=super_admin_headers,
        ).json()
        if item["new_data"]["stage"] == 1
    ]
    assert len(stage_approvals) == 1


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_frontend_cors_preflight(client):
    response = client.options(
        "/roles",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"


def test_pilot_api_requires_authentication(client):
    response = client.get("/pilots")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_pilot_creation_builds_prd_stage_and_gate_structure(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)

    assert pilot["code"] == "PIL-1405-001"
    assert pilot["project_system_name"] == "project-1"
    assert pilot["current_stage"] == 1
    assert len(pilot["stages"]) == 19
    assert pilot["stages"][0]["status"] == "open"
    assert all(stage["status"] == "locked" for stage in pilot["stages"][1:])
    assert [stage["title"] for stage in pilot["stages"]] == [
        "انتخاب پروژه مناسب برای پایلوت",
        "معرفی و موافقت",
        "دریافت DWG و اطلاعات طبقات",
        "راه‌اندازی در پلتفرم اصلی",
        "برنامه‌ریزی و تخصیص مأموریت",
        "آمادگی قبل از برداشت",
        "اجرای برداشت طبقات",
        "کنترل نتیجه چندطبقه",
        "وضعیت Upload در پلتفرم اصلی",
        "کنترل پردازش در پلتفرم اصلی",
        "اطلاع‌رسانی آماده‌شدن بازدید",
        "آموزش اولیه مالک",
        "پیگیری موفقیت مشتری",
        "ادامه برداشت‌های پایلوت",
        "ارزیابی موفقیت پایلوت",
        "جلسه جمع‌بندی با مالک",
        "تهیه و ارائه پیشنهاد تجاری",
        "پیگیری تا تصمیم و عقد قرارداد",
        "تبدیل پایلوت به قرارداد یا بستن پرونده",
    ]
    assert [gate["code"] for gate in pilot["gates"]] == ["G1", "G2", "G3", "G4", "G5"]
    assert [gate["after_stage"] for gate in pilot["gates"]] == [2, 4, 9, 13, 15]


def test_locked_stage_cannot_be_submitted(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)

    response = client.post(
        f"/pilots/{pilot['id']}/stages/2/submit",
        json={"form_data": {}, "checklist": {}},
        headers=super_admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "STAGE_LOCKED"
    assert response.json()["stage"] == 2
    assert response.json()["trace_id"]


def test_stage_validation_returns_field_level_error_contract(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)

    response = client.post(
        f"/pilots/{pilot['id']}/stages/1/submit",
        json={
            "form_data": {"owner_name": "مالک نمونه"},
            "checklist": {"project_active": True},
        },
        headers=super_admin_headers,
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


def test_rejection_revision_gate_and_immutable_snapshots(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)
    pilot_id = pilot["id"]
    save_valid_f01(client, pilot_id, super_admin_headers)

    stage_1_submit = client.post(
        f"/pilots/{pilot_id}/stages/1/submit",
        json={},
        headers=super_admin_headers,
    )
    assert stage_1_submit.status_code == 200
    assert stage_1_submit.json()["submission"]["version"] == 1
    assert stage_1_submit.json()["submission"]["submitted_by"].startswith("کاربر")

    stage_1_approve = client.post(
        f"/pilots/{pilot_id}/stages/1/approve",
        json={},
        headers=super_admin_headers,
    )
    assert stage_1_approve.status_code == 200
    assert stage_1_approve.json()["snapshot"]["content_hash"]

    pilot_after_stage_1 = client.get(
        f"/pilots/{pilot_id}", headers=super_admin_headers
    ).json()
    assert pilot_after_stage_1["current_stage"] == 2
    assert pilot_after_stage_1["stages"][1]["status"] == "open"
    assert pilot_after_stage_1["gates"][0]["status"] == "locked"

    stage_2_submit = client.post(
        f"/pilots/{pilot_id}/stages/2/submit",
        json={},
        headers=super_admin_headers,
    )
    assert stage_2_submit.status_code == 200

    missing_reason = client.post(
        f"/pilots/{pilot_id}/stages/2/reject",
        json={},
        headers=super_admin_headers,
    )
    assert missing_reason.status_code == 422

    rejected = client.post(
        f"/pilots/{pilot_id}/stages/2/reject",
        json={"correction_items": ["شماره هماهنگ‌کننده محل بازبینی شود"]},
        headers=super_admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["stage"]["status"] == "needs_revision"

    revised = client.post(
        f"/pilots/{pilot_id}/stages/2/submit",
        json={},
        headers=super_admin_headers,
    )
    assert revised.status_code == 200
    assert revised.json()["submission"]["version"] == 2

    approved = client.post(
        f"/pilots/{pilot_id}/stages/2/approve",
        json={"comment": "تمام موارد بررسی شد"},
        headers=super_admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["snapshot"]["version"] == 2

    pilot_after_g1 = client.get(
        f"/pilots/{pilot_id}", headers=super_admin_headers
    ).json()
    assert pilot_after_g1["current_stage"] == 3
    assert pilot_after_g1["gates"][0]["status"] == "passed"
    assert pilot_after_g1["status"] == "waiting_documents"

    stage_1_snapshots = client.get(
        f"/pilots/{pilot_id}/stages/1/snapshots", headers=super_admin_headers
    ).json()
    stage_2_snapshots = client.get(
        f"/pilots/{pilot_id}/stages/2/snapshots", headers=super_admin_headers
    ).json()
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
