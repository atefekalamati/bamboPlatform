from conftest import login_with_otp, prepare_pilot_through_g2, sample_pilot_payload


def _create_capture_expert(client, headers, mobile="09157777777"):
    roles = client.get("/roles", headers=headers).json()
    role_id = next(role["id"] for role in roles if role["name"] == "capture_expert")
    response = client.post(
        "/users",
        json={"mobile": mobile, "display_name": "کارشناس برداشت محدود", "role_ids": [role_id]},
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _mission_payload(expert_id, floor_ids):
    return {
        "expert_user_id": expert_id,
        "scheduled_start": "2027-01-10T08:00:00+00:00",
        "scheduled_end": "2027-01-10T10:00:00+00:00",
        "floor_ids": floor_ids,
        "location": "محل پروژه",
        "site_contact_name": "هماهنگ‌کننده",
        "site_contact_mobile": "09152222222",
        "limitation": "ندارد",
    }


def test_dashboard_summary_and_pilot_list(client, super_admin_headers):
    created = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert created.status_code == 201

    summary = client.get("/api/v1/dashboard/summary", headers=super_admin_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["state"] == "SUCCESS"
    assert body["summary"]["total_pilots"] == 1
    assert body["summary"]["active"] == 1

    listing = client.get("/api/v1/dashboard/pilots?page=1&page_size=10", headers=super_admin_headers)
    assert listing.status_code == 200
    assert listing.json()["pagination"]["total"] == 1
    assert listing.json()["items"][0]["progress_percent"] == 0


def test_server_paginated_users_and_pilots(client, super_admin_headers):
    first = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert first.status_code == 201

    created_pilot = first.json()
    pilot_page = client.get(
        f"/api/v1/pilots?page=1&page_size=20&q={created_pilot['code']}&status={created_pilot['status']}",
        headers=super_admin_headers,
    )
    assert pilot_page.status_code == 200, pilot_page.text
    assert pilot_page.json()["total"] == 1
    assert pilot_page.json()["items"][0]["id"] == created_pilot["id"]

    expert = _create_capture_expert(client, super_admin_headers, "09156667777")
    user_page = client.get(
        "/api/v1/users?page=1&page_size=20&q=09156667777&status=active",
        headers=super_admin_headers,
    )
    assert user_page.status_code == 200, user_page.text
    assert user_page.json()["total"] == 1
    assert user_page.json()["items"][0]["id"] == expert["id"]


def test_dashboard_sections_and_actions(client, super_admin_headers):
    created = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert created.status_code == 201
    for section in ("stages", "gates", "missions", "incidents", "sla", "forms", "commercial", "activities"):
        response = client.get(f"/api/v1/dashboard/{section}", headers=super_admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["state"] == "SUCCESS"
    actions = client.get("/api/v1/dashboard/my-actions", headers=super_admin_headers)
    assert actions.status_code == 200
    assert actions.json()["items"][0]["entity_type"] == "stage"


def test_dashboard_requires_permission_and_powerbi_route_is_removed(client, super_admin_headers):
    no_auth = client.get("/api/v1/dashboard/summary")
    assert no_auth.status_code == 401
    embed = client.get("/api/v1/dashboard/powerbi/embed-token", headers=super_admin_headers)
    assert embed.status_code == 404


def test_dashboard_no_data_state(client, super_admin_headers):
    response = client.get("/api/v1/dashboard/summary", headers=super_admin_headers)
    assert response.status_code == 200
    assert response.json()["state"] == "NO_DATA"


def test_dashboard_scope_does_not_leak_unassigned_pilots(client, super_admin_headers):
    created = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert created.status_code == 201
    role = next(item for item in client.get("/roles", headers=super_admin_headers).json() if item["name"] == "capture_expert")
    user = client.post("/users", json={"mobile": "09157777777", "display_name": "Scoped viewer", "role_ids": [role["id"]]}, headers=super_admin_headers)
    assert user.status_code == 201
    scoped_headers = login_with_otp(client, "09157777777")
    response = client.get("/api/v1/dashboard/pilots", headers=scoped_headers)
    assert response.status_code == 200
    assert response.json()["state"] == "NO_ACCESS"
    assert response.json()["items"] == []
    assert client.get("/pilots", headers=scoped_headers).json() == []
    assert client.get(f"/pilots/{created.json()['id']}", headers=scoped_headers).status_code == 404


def test_capture_expert_only_sees_pilot_assigned_through_mission(client, super_admin_headers):
    assigned, floors = prepare_pilot_through_g2(client, super_admin_headers, total_floors=1)
    unassigned = client.post("/pilots", json=sample_pilot_payload(), headers=super_admin_headers)
    assert unassigned.status_code == 201
    expert = _create_capture_expert(client, super_admin_headers, "09158887777")
    mission = client.post(
        f"/pilots/{assigned['id']}/missions",
        json=_mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201, mission.json()
    expert_headers = login_with_otp(client, "09158887777")

    pilot_list = client.get("/pilots", headers=expert_headers)
    assert pilot_list.status_code == 200
    assert [pilot["id"] for pilot in pilot_list.json()] == [assigned["id"]]
    assert client.get(f"/pilots/{assigned['id']}", headers=expert_headers).status_code == 200
    assert client.get(f"/pilots/{unassigned.json()['id']}", headers=expert_headers).status_code == 404

    dashboard = client.get("/api/v1/dashboard/pilots", headers=expert_headers).json()
    assert [pilot["id"] for pilot in dashboard["items"]] == [assigned["id"]]
    summary = client.get("/api/v1/dashboard/summary", headers=expert_headers).json()
    assert summary["summary"]["total_pilots"] == 1
