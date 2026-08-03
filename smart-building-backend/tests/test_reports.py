from datetime import UTC, datetime, timedelta

from conftest import login_with_otp, sample_pilot_payload, save_valid_f01
from app.database import get_session
from app.database import get_engine
from app.main import app
from app.models import FinalOutcome, Incident, Permission, Pilot, Role, User
from sqlalchemy import event


def create_pilot(client, headers, *, suffix=""):
    payload = sample_pilot_payload()
    payload["owner"]["name"] += suffix
    payload["project"]["name"] += suffix
    response = client.post("/pilots", json=payload, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


def test_reports_openapi_empty_state_and_filters(client, super_admin_headers):
    schema = app.openapi()
    paths = schema["paths"]
    for path in (
        "/api/v1/reports/overview", "/api/v1/reports/pipeline",
        "/api/v1/reports/pilots", "/api/v1/reports/gates",
        "/api/v1/reports/actions", "/api/v1/reports/sla",
        "/api/v1/reports/kpis", "/api/v1/reports/incidents",
        "/api/v1/reports/pilots/{pilot_id}/one-page",
        "/api/v1/reports/pilots/{pilot_id}/external-evidence",
    ):
        assert path in paths
    empty = client.get("/api/v1/reports/overview", headers=super_admin_headers)
    assert empty.status_code == 200
    assert empty.json()["state"] == "NO_DATA"
    invalid = client.get(
        "/api/v1/reports/pilots?date_from=2027-01-02T00:00:00Z&date_to=2027-01-01T00:00:00Z",
        headers=super_admin_headers,
    )
    assert invalid.status_code == 422
    oversized = client.get("/api/v1/reports/pilots?page_size=101", headers=super_admin_headers)
    assert oversized.status_code == 422


def test_report_progress_counts_only_approved_stages(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)
    pilot_id = pilot["id"]
    save_valid_f01(client, pilot_id, super_admin_headers)
    submitted = client.post(f"/pilots/{pilot_id}/stages/1/submit", json={}, headers=super_admin_headers)
    assert submitted.status_code == 200
    listing = client.get("/api/v1/reports/pilots", headers=super_admin_headers).json()
    assert listing["items"][0]["approved_stages_count"] == 0
    assert listing["items"][0]["progress_percent"] == 0
    approved = client.post(f"/pilots/{pilot_id}/stages/1/approve", json={}, headers=super_admin_headers)
    assert approved.status_code == 200
    listing = client.get("/api/v1/reports/pilots", headers=super_admin_headers).json()
    assert listing["items"][0]["approved_stages_count"] == 1
    assert listing["items"][0]["progress_percent"] == round(100 / 19, 2)

    f01 = client.get(f"/pilots/{pilot_id}/forms/f01", headers=super_admin_headers).json()
    payload = {key: f01[key] for key in (
        "project_active", "imaging_value", "remote_viewing_need", "access_possible",
        "dwg_available", "continued_capacity", "not_demo_only", "introduction_completed",
        "imaging_accepted", "dwg_accepted", "feedback_accepted", "coordinator_name",
        "coordinator_mobile", "limitation", "result", "referral_deadline",
        "sales_user_id", "pilot_manager_user_id", "referred_at",
    )}
    payload["imaging_value"] = False
    assert client.put(f"/pilots/{pilot_id}/forms/f01", json=payload, headers=super_admin_headers).status_code == 200
    listing = client.get("/api/v1/reports/pilots", headers=super_admin_headers).json()
    assert listing["items"][0]["approved_stages_count"] == 0
    assert listing["items"][0]["current_stage_status"] == "needs_revision"


def test_overview_pipeline_outcomes_and_pagination(client, super_admin_headers):
    first = create_pilot(client, super_admin_headers, suffix=" قرارداد")
    second = create_pilot(client, super_admin_headers, suffix=" بسته")
    with get_session() as db:
        user_id = db.query(User.id).join(User.roles).filter(Role.name == "super_admin").scalar()
        first_pilot = db.get(Pilot, first["id"]); second_pilot = db.get(Pilot, second["id"])
        first_pilot.status = "converted"; second_pilot.status = "closed"
        approved_at = datetime.now(UTC).replace(tzinfo=None)
        db.add(FinalOutcome(pilot=first_pilot, responsible_user_id=user_id, outcome="contract", pilot_manager_approved=True, approved_by_user_id=user_id, approved_at=approved_at))
        db.add(FinalOutcome(pilot=second_pilot, responsible_user_id=user_id, outcome="closed", reason="عدم ادامه", pilot_manager_approved=True, approved_by_user_id=user_id, approved_at=approved_at))
        db.commit()
    overview = client.get("/api/v1/reports/overview", headers=super_admin_headers).json()
    assert overview["summary"]["total_pilots"] == 2
    assert overview["summary"]["contracted"] == 1
    assert overview["summary"]["closed_without_contract"] == 1
    pipeline = client.get("/api/v1/reports/pipeline", headers=super_admin_headers).json()
    counts = {item["key"]: item["count"] for item in pipeline["items"]}
    assert counts["converted"] == 1 and counts["closed"] == 1
    closed_group = next(item for item in pipeline["items"] if item["key"] == "closed")
    assert set(closed_group["source_statuses"]) == {"closed", "completed", "rejected", "stopped"}
    closed_drill_down = client.get(
        "/api/v1/reports/pilots?pilot_status=closed",
        headers=super_admin_headers,
    ).json()
    assert closed_drill_down["summary"]["total"] == closed_group["count"]
    page = client.get("/api/v1/reports/pilots?page=2&page_size=1", headers=super_admin_headers).json()
    assert page["pagination"] == {"page": 2, "page_size": 1, "total": 2, "total_pages": 2}
    assert len(page["items"]) == 1


def test_reports_scope_and_idor(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)
    role = next(r for r in client.get("/roles", headers=super_admin_headers).json() if r["name"] == "capture_expert")
    user = client.post("/users", json={"mobile":"09154443322","display_name":"Limited reporter","role_ids":[role["id"]]}, headers=super_admin_headers)
    assert user.status_code == 201
    with get_session() as db:
        db_role = db.query(Role).filter(Role.id == role["id"]).one()
        permission = db.query(Permission).filter(Permission.code == "reports.read").one()
        if permission not in db_role.permissions:
            db_role.permissions.append(permission)
        db.commit()
    limited = login_with_otp(client, "09154443322")
    listing = client.get("/api/v1/reports/pilots", headers=limited)
    assert listing.status_code == 200
    assert listing.json()["state"] == "NO_ACCESS"
    assert listing.json()["items"] == []
    hidden = client.get(f"/api/v1/reports/pilots/{pilot['id']}/one-page", headers=limited)
    assert hidden.status_code == 404


def test_incident_kpi_and_one_page_are_safe(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)
    now = datetime.now(UTC).replace(tzinfo=None)
    with get_session() as db:
        user_id = db.query(User.id).join(User.roles).filter(Role.name == "super_admin").scalar()
        db_pilot = db.get(Pilot, pilot["id"])
        for sequence in range(1, 6):
            db.add(Incident(pilot=db_pilot, sequence=sequence, code=f"INC-{pilot['code']}-{sequence:02d}", occurred_at=now, reported_at=now, reported_by_user_id=user_id, stage_number=1, severity="critical" if sequence == 1 else "important", incident_type="process", description="شرح حساس و طولانی " * 30, owner_user_id=user_id, response_due_at=now - timedelta(hours=2), status="open" if sequence < 5 else "closed", closed_at=now if sequence == 5 else None))
        db.commit()
    incidents = client.get("/api/v1/reports/incidents", headers=super_admin_headers).json()
    assert incidents["summary"]["critical_open"] == 1
    assert incidents["summary"]["total_open"] == 4
    assert all(len(item["description_short"]) <= 160 for item in incidents["items"])
    actions = client.get(
        "/api/v1/reports/actions?priority=critical&due=overdue",
        headers=super_admin_headers,
    ).json()
    assert actions["summary"]["total"] == 1
    assert actions["items"][0]["entity_type"] == "incident"
    sla = client.get("/api/v1/reports/sla", headers=super_admin_headers).json()
    assert sla["state"] == "PARTIAL_DATA"
    assert sla["summary"]["total_monitored"] == 5
    assert sla["summary"]["overdue"] == 5
    kpis = client.get("/api/v1/reports/kpis", headers=super_admin_headers).json()
    upload = next(item for item in kpis["items"] if item["key"] == "successful_upload_percent")
    assert upload["value"] is None and upload["status"] == "insufficient_data"
    one_page = client.get(f"/api/v1/reports/pilots/{pilot['id']}/one-page", headers=super_admin_headers)
    assert one_page.status_code == 200, one_page.json()
    report = one_page.json()["summary"]
    assert set(report) >= {"header","overall_result","process","operations","customer_experience","commercial","open_issues","recommended_decision","next_action"}
    assert len(report["open_issues"]) == 3
    assert report["recommended_decision"] is None
    assert report["decision_status"] == "requires_manager_decision"


def test_gate_report_has_all_management_groups_and_date_filter(client, super_admin_headers):
    create_pilot(client, super_admin_headers)
    gates = client.get("/api/v1/reports/gates", headers=super_admin_headers).json()
    assert set(gates["summary"]) == {"G1", "G2", "G3", "G4", "G5"}
    assert len(gates["items"]) == 5
    assert all(group["pending"] == 1 for group in gates["summary"].values())

    future = client.get(
        "/api/v1/reports/pilots?date_from=2099-01-01T00:00:00Z",
        headers=super_admin_headers,
    )
    assert future.status_code == 200
    assert future.json()["state"] == "NO_ACCESS"
    assert future.json()["pagination"]["total"] == 0


def test_report_pilot_query_count_does_not_grow_per_row(client, super_admin_headers):
    create_pilot(client, super_admin_headers, suffix=" ۱")
    engine = get_engine()
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        response = client.get("/api/v1/reports/pilots", headers=super_admin_headers)
        assert response.status_code == 200
        one_row_queries = select_count
        for suffix in (" ۲", " ۳", " ۴", " ۵"):
            create_pilot(client, super_admin_headers, suffix=suffix)
        select_count = 0
        response = client.get("/api/v1/reports/pilots", headers=super_admin_headers)
        assert response.status_code == 200
        five_row_queries = select_count
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)
    assert five_row_queries <= one_row_queries + 1
