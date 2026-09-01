"""Scope-aware global incident-list contract tests."""

from datetime import UTC, datetime, timedelta

from conftest import login_with_otp, sample_pilot_payload, save_valid_f01
from sqlalchemy import event

from app.database import get_engine, get_session
from app.models import FormF01, Incident, Permission, Role


def _role_id(client, headers, role_name: str) -> int:
    roles = client.get("/roles", headers=headers).json()
    return next(role["id"] for role in roles if role["name"] == role_name)


def _create_user(client, headers, *, mobile: str, role_name: str) -> dict:
    response = client.post(
        "/users",
        json={
            "mobile": mobile,
            "display_name": f"{role_name} incident viewer",
            "role_ids": [_role_id(client, headers, role_name)],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _seed_incident(
    *,
    pilot_id: int,
    sequence: int,
    code: str,
    reported_by_user_id: int,
    owner_user_id: int | None,
    occurred_at: datetime,
    severity: str,
    status: str,
    description: str,
    overdue: bool,
) -> None:
    with get_session() as db:
        db.add(
            Incident(
                pilot_id=pilot_id,
                sequence=sequence,
                code=code,
                occurred_at=occurred_at,
                reported_at=occurred_at,
                reported_by_user_id=reported_by_user_id,
                stage_number=10,
                severity=severity,
                incident_type="process",
                description=description,
                owner_user_id=owner_user_id,
                response_due_at=(
                    datetime.now(UTC) - timedelta(hours=1)
                    if overdue
                    else datetime.now(UTC) + timedelta(hours=1)
                ),
                status=status,
                closed_at=datetime.now(UTC) if status == "closed" else None,
            )
        )
        db.commit()


def test_global_incidents_pagination_filters_sort_summary_and_validation(
    client,
    super_admin_headers,
):
    pilot = client.post(
        "/pilots", json=sample_pilot_payload(), headers=super_admin_headers
    ).json()
    reporter_id = client.get("/users", headers=super_admin_headers).json()[0]["id"]
    first_at = datetime(2025, 1, 10, 8, tzinfo=UTC)
    _seed_incident(
        pilot_id=pilot["id"],
        sequence=1,
        code=f"INC-{pilot['code']}-01",
        reported_by_user_id=reporter_id,
        owner_user_id=reporter_id,
        occurred_at=first_at,
        severity="critical",
        status="open",
        description="Global searchable elevator incident",
        overdue=True,
    )
    _seed_incident(
        pilot_id=pilot["id"],
        sequence=2,
        code=f"INC-{pilot['code']}-02",
        reported_by_user_id=reporter_id,
        owner_user_id=None,
        occurred_at=first_at + timedelta(days=1),
        severity="important",
        status="closed",
        description="Closed process issue",
        overdue=False,
    )

    incident_statements = []

    def record_incident_queries(_conn, _cursor, statement, _params, _context, _many):
        if "FROM incidents" in statement:
            incident_statements.append(statement)

    engine = get_engine()
    event.listen(engine, "before_cursor_execute", record_incident_queries)
    try:
        first_page = client.get(
            "/incidents",
            params={"page": 1, "page_size": 1, "sort": "occurred_at"},
            headers=super_admin_headers,
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_incident_queries)
    assert first_page.status_code == 200, first_page.json()
    assert len(incident_statements) == 2
    body = first_page.json()
    assert (body["total"], body["total_pages"], len(body["items"])) == (2, 2, 1)
    assert body["items"][0]["pilot_code"] == pilot["code"]
    assert body["items"][0]["pilot_display_name"] == pilot["display_name"]
    assert body["items"][0]["sla_due_at"] == body["items"][0]["response_due_at"]
    assert body["summary"] == {
        "total": 2,
        "open": 1,
        "critical": 1,
        "important": 1,
        "overdue": 1,
        "closed": 1,
    }

    filtered = client.get(
        "/incidents",
        params={
            "q": "elevator",
            "status": "open",
            "severity": "critical",
            "type": "process",
            "pilot_id": pilot["id"],
            "stage_number": 10,
            "assignee_id": reporter_id,
            "overdue": True,
            "occurred_from": "2025-01-10T00:00:00Z",
            "occurred_to": "2025-01-10T23:59:59Z",
            "sort": "-sla_due_at",
        },
        headers=super_admin_headers,
    )
    assert filtered.status_code == 200, filtered.json()
    assert filtered.json()["total"] == 1
    assert filtered.json()["summary"]["total"] == 1
    assert filtered.json()["summary"]["critical"] == 1

    by_pilot_code = client.get(
        "/incidents", params={"q": pilot["code"]}, headers=super_admin_headers
    )
    assert by_pilot_code.status_code == 200
    assert by_pilot_code.json()["total"] == 2

    empty = client.get(
        "/incidents", params={"q": "not-found-anywhere"}, headers=super_admin_headers
    ).json()
    assert empty["items"] == []
    assert empty["summary"] == {
        "total": 0,
        "open": 0,
        "critical": 0,
        "important": 0,
        "overdue": 0,
        "closed": 0,
    }

    for params in (
        {"status": "invalid"},
        {"severity": "invalid"},
        {"type": "invalid"},
        {"sort": "description"},
        {"page_size": 101},
    ):
        assert client.get(
            "/incidents", params=params, headers=super_admin_headers
        ).status_code == 422

    openapi = client.get("/openapi.json").json()
    assert openapi["paths"]["/pilots/{pilot_id}/incidents"]["get"]["deprecated"] is True


def test_global_incidents_scope_prevents_items_and_summary_leaks(
    client,
    super_admin_headers,
):
    capture_mobile = "09157770001"
    manager_mobile = "09157770002"
    capture = _create_user(
        client,
        super_admin_headers,
        mobile=capture_mobile,
        role_name="capture_expert",
    )
    manager = _create_user(
        client,
        super_admin_headers,
        mobile=manager_mobile,
        role_name="pilot_manager",
    )
    first = client.post(
        "/pilots", json=sample_pilot_payload(), headers=super_admin_headers
    ).json()
    second = client.post(
        "/pilots", json=sample_pilot_payload(), headers=super_admin_headers
    ).json()
    save_valid_f01(client, first["id"], super_admin_headers)
    save_valid_f01(client, second["id"], super_admin_headers)
    with get_session() as db:
        manager_role = db.query(Role).filter(Role.name == "pilot_manager").one()
        read_all = (
            db.query(Permission)
            .filter(Permission.code == "incidents.read_all")
            .one()
        )
        manager_role.permissions.remove(read_all)
        first_form = db.query(FormF01).filter(FormF01.pilot_id == first["id"]).one()
        first_form.pilot_manager_user_id = manager["id"]
        db.commit()

    occurred_at = datetime(2025, 2, 1, 8, tzinfo=UTC)
    _seed_incident(
        pilot_id=first["id"],
        sequence=1,
        code=f"INC-{first['code']}-01",
        reported_by_user_id=capture["id"],
        owner_user_id=capture["id"],
        occurred_at=occurred_at,
        severity="critical",
        status="open",
        description="Visible assigned incident",
        overdue=True,
    )
    _seed_incident(
        pilot_id=second["id"],
        sequence=1,
        code=f"INC-{second['code']}-01",
        reported_by_user_id=capture["id"],
        owner_user_id=None,
        occurred_at=occurred_at,
        severity="critical",
        status="open",
        description="Forbidden incident",
        overdue=True,
    )

    for mobile in (capture_mobile, manager_mobile):
        scoped_headers = login_with_otp(client, mobile)
        scoped = client.get("/incidents", headers=scoped_headers)
        assert scoped.status_code == 200, scoped.json()
        assert scoped.json()["total"] == 1
        assert scoped.json()["summary"]["total"] == 1
        assert scoped.json()["summary"]["critical"] == 1
        assert scoped.json()["items"][0]["pilot_id"] == first["id"]

        forbidden_filter = client.get(
            "/incidents",
            params={"pilot_id": second["id"]},
            headers=scoped_headers,
        ).json()
        assert forbidden_filter["items"] == []
        assert forbidden_filter["total"] == 0
        assert forbidden_filter["summary"]["total"] == 0

    unrestricted = client.get("/incidents", headers=super_admin_headers).json()
    assert unrestricted["total"] == 2
