from conftest import (
    login_with_otp,
    prepare_pilot_through_g2,
    submit_and_approve_stage,
)
from app.main import app


def create_capture_expert(client, headers, mobile="09157777777"):
    roles = client.get("/roles", headers=headers).json()
    role_id = next(role["id"] for role in roles if role["name"] == "capture_expert")
    response = client.post(
        "/users",
        json={
            "mobile": mobile,
            "display_name": "کارشناس برداشت",
            "role_ids": [role_id],
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def mission_payload(expert_id, floor_ids, start="2027-01-10T08:00:00+00:00"):
    end_hour = "10" if "08:00:00" in start else "13"
    return {
        "expert_user_id": expert_id,
        "scheduled_start": start,
        "scheduled_end": f"2027-01-10T{end_hour}:00:00+00:00",
        "floor_ids": floor_ids,
        "location": "مشهد، محل پروژه",
        "site_contact_name": "هماهنگ‌کننده نمونه",
        "site_contact_mobile": "09152222222",
        "limitation": "ورود فقط با هماهنگی",
    }


def f03_payload(
    *,
    assignment=True,
    readiness=False,
    stop_condition_reason=None,
    started_at=None,
    finished_at=None,
    mission_completed=False,
    operations_confirmed=False,
):
    return {
        "assignment_accepted": assignment,
        "site_entry_confirmed": readiness,
        "permission_confirmed": readiness,
        "ppe_ready": readiness,
        "camera_ready": readiness,
        "main_app_connected": readiness,
        "battery_ready": readiness,
        "storage_ready": readiness,
        "project_floor_plan_confirmed": readiness,
        "test_image_completed": readiness,
        "stop_condition_reason": stop_condition_reason,
        "mission_completed": mission_completed,
        "operations_confirmed": operations_confirmed,
        "started_at": started_at,
        "finished_at": finished_at,
    }


def mission_floor_payload(*, upload_complete=False):
    return {
        "capture_state": "completed",
        "correct_floor": True,
        "start_point_confirmed": True,
        "main_capture_started": True,
        "continuous_route": True,
        "coverage_completed": True,
        "capture_finished": True,
        "saved_in_main_app": True,
        "capture_started_at": "2027-01-10T08:15:00+00:00",
        "capture_finished_at": "2027-01-10T09:30:00+00:00",
        "main_upload_started": upload_complete,
        "main_upload_completed": upload_complete,
        "correct_floor_link": upload_complete,
        "operations_notified": upload_complete,
    }


def test_operations_openapi_contract():
    schema = app.openapi()
    for path in (
        "/pilots/{pilot_id}/missions",
        "/missions/{mission_id}",
        "/missions/{mission_id}/forms/f03",
        "/missions/{mission_id}/floors/{floor_id}",
    ):
        assert path in schema["paths"]
    assert "MissionCreate" in schema["components"]["schemas"]
    assert "FormF03Update" in schema["components"]["schemas"]


def test_floor_linked_to_mission_cannot_be_deleted(client, super_admin_headers):
    expert = create_capture_expert(client, super_admin_headers)
    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    mission = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floors[0]["id"]]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201

    blocked = client.delete(
        f"/floors/{floors[0]['id']}",
        headers=super_admin_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "FLOOR_HAS_MISSIONS"


def test_mission_f03_stages_5_to_9_and_g3(client, super_admin_headers):
    expert = create_capture_expert(client, super_admin_headers)
    expert_headers = login_with_otp(client, "09157777777")
    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    mission_response = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission_response.status_code == 201, mission_response.json()
    mission = mission_response.json()
    mission_id = mission["id"]
    assert mission["code"] == f"MIS-{pilot['code']}-01"
    assert mission["notifications"][0]["template"] == "mission_created"
    assert mission["notifications"][0]["status"] == "delivered"

    create_capture_expert(client, super_admin_headers, "09159999999")
    other_expert_headers = login_with_otp(client, "09159999999")
    assert (
        client.get(
            f"/missions/{mission_id}",
            headers=other_expert_headers,
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/pilots/{pilot['id']}/missions",
            headers=other_expert_headers,
        ).json()
        == []
    )
    expert_reschedule = client.patch(
        f"/missions/{mission_id}",
        json={
            "scheduled_start": "2027-01-10T08:30:00+00:00",
            "scheduled_end": "2027-01-10T10:30:00+00:00",
            "reason": "تغییر غیرمجاز",
        },
        headers=expert_headers,
    )
    assert expert_reschedule.status_code == 403
    assert expert_reschedule.json()["code"] == "MISSION_ACCESS_DENIED"

    rescheduled = client.patch(
        f"/missions/{mission_id}",
        json={
            "scheduled_start": "2027-01-10T08:30:00+00:00",
            "scheduled_end": "2027-01-10T10:30:00+00:00",
            "reason": "هماهنگی با کارفرما",
        },
        headers=super_admin_headers,
    )
    assert rescheduled.status_code == 200, rescheduled.json()
    assert len(rescheduled.json()["notifications"]) == 2
    assert rescheduled.json()["notifications"][-1]["template"] == "mission_rescheduled"

    blocked_stage_5 = client.post(
        f"/pilots/{pilot['id']}/stages/5/submit",
        json={
            "form_data": {"expert": "جعلی"},
            "checklist": {"expert_assignment_confirmed": True},
        },
        headers=super_admin_headers,
    )
    assert blocked_stage_5.status_code == 422
    assert any(
        error["field"] == "checklist.expert_assignment_confirmed"
        for error in blocked_stage_5.json()["errors"]
    )

    accepted = client.put(
        f"/missions/{mission_id}/forms/f03",
        json=f03_payload(),
        headers=expert_headers,
    )
    assert accepted.status_code == 200
    stage_5 = submit_and_approve_stage(
        client,
        pilot["id"],
        5,
        super_admin_headers,
    )
    assert stage_5["snapshot"]["content"]["submission"]["form_data"][
        "mission_code"
    ] == mission["code"]

    media_rejected = client.put(
        f"/missions/{mission_id}/forms/f03",
        json=f03_payload(readiness=True) | {"photo_url": "https://example.invalid/a.jpg"},
        headers=expert_headers,
    )
    assert media_rejected.status_code == 422

    stopped = client.put(
        f"/missions/{mission_id}/forms/f03",
        json=f03_payload(
            readiness=True,
            stop_condition_reason="اتصال اپ اصلی قطع است",
        ),
        headers=expert_headers,
    )
    assert stopped.status_code == 200
    stop_submit = client.post(
        f"/pilots/{pilot['id']}/stages/6/submit",
        json={},
        headers=expert_headers,
    )
    assert stop_submit.status_code == 422
    assert any(
        error["field"] == "checklist.no_stop_condition"
        for error in stop_submit.json()["errors"]
    )

    ready = client.put(
        f"/missions/{mission_id}/forms/f03",
        json=f03_payload(readiness=True),
        headers=expert_headers,
    )
    assert ready.status_code == 200
    assert ready.json()["stop_condition_reason"] is None
    submit_and_approve_stage(client, pilot["id"], 6, super_admin_headers)

    started = client.put(
        f"/missions/{mission_id}/forms/f03",
        json=f03_payload(
            readiness=True,
            started_at="2027-01-10T08:10:00+00:00",
            finished_at="2027-01-10T09:45:00+00:00",
        ),
        headers=super_admin_headers,
    )
    assert started.status_code == 200
    for floor in floors:
        updated = client.put(
            f"/missions/{mission_id}/floors/{floor['id']}",
            json=mission_floor_payload(),
            headers=expert_headers,
        )
        assert updated.status_code == 200, updated.json()
    submit_and_approve_stage(client, pilot["id"], 7, super_admin_headers)
    submit_and_approve_stage(client, pilot["id"], 8, super_admin_headers)

    for floor in floors:
        uploaded = client.put(
            f"/missions/{mission_id}/floors/{floor['id']}",
            json=mission_floor_payload(upload_complete=True),
            headers=expert_headers,
        )
        assert uploaded.status_code == 200, uploaded.json()
    completed = client.put(
        f"/missions/{mission_id}/forms/f03",
        json=f03_payload(
            readiness=True,
            started_at="2027-01-10T08:10:00+00:00",
            finished_at="2027-01-10T09:45:00+00:00",
            mission_completed=True,
            operations_confirmed=True,
        ),
        headers=expert_headers,
    )
    assert completed.status_code == 200
    submit_and_approve_stage(client, pilot["id"], 9, super_admin_headers)

    after_g3 = client.get(
        f"/pilots/{pilot['id']}",
        headers=expert_headers,
    ).json()
    assert after_g3["current_stage"] == 10
    assert next(gate for gate in after_g3["gates"] if gate["code"] == "G3")[
        "status"
    ] == "passed"

    changed_upload = mission_floor_payload(upload_complete=True) | {
        "main_upload_completed": False,
        "correct_floor_link": False,
        "operations_notified": False,
    }
    reopened = client.put(
        f"/missions/{mission_id}/floors/{floors[0]['id']}",
        json=changed_upload,
        headers=super_admin_headers,
    )
    assert reopened.status_code == 200
    pilot_after_change = client.get(
        f"/pilots/{pilot['id']}",
        headers=super_admin_headers,
    ).json()
    assert pilot_after_change["current_stage"] == 9
    assert pilot_after_change["stages"][8]["status"] == "needs_revision"
    assert next(
        gate for gate in pilot_after_change["gates"] if gate["code"] == "G3"
    )["status"] == "locked"
    snapshots = client.get(
        f"/pilots/{pilot['id']}/stages/9/snapshots",
        headers=super_admin_headers,
    ).json()
    assert len(snapshots) == 1


def test_expert_conflict_and_failed_provider_are_recorded(
    client,
    super_admin_headers,
    monkeypatch,
):
    expert = create_capture_expert(client, super_admin_headers, "09158888888")
    first_pilot, first_floors = prepare_pilot_through_g2(
        client,
        super_admin_headers,
        total_floors=1,
    )
    second_pilot, second_floors = prepare_pilot_through_g2(
        client,
        super_admin_headers,
        total_floors=1,
    )

    super_admin = client.get("/auth/me", headers=super_admin_headers).json()
    invalid_expert = client.post(
        f"/pilots/{first_pilot['id']}/missions",
        json=mission_payload(
            super_admin["id"],
            [first_floors[0]["id"]],
        ),
        headers=super_admin_headers,
    )
    assert invalid_expert.status_code == 422
    assert invalid_expert.json()["code"] == "CAPTURE_EXPERT_INVALID"

    first = client.post(
        f"/pilots/{first_pilot['id']}/missions",
        json=mission_payload(expert["id"], [first_floors[0]["id"]]),
        headers=super_admin_headers,
    )
    assert first.status_code == 201

    conflict_payload = mission_payload(
        expert["id"],
        [second_floors[0]["id"]],
        start="2027-01-10T09:00:00+00:00",
    )
    conflict_payload["scheduled_end"] = "2027-01-10T11:00:00+00:00"
    conflict = client.post(
        f"/pilots/{second_pilot['id']}/missions",
        json=conflict_payload,
        headers=super_admin_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "MISSION_EXPERT_CONFLICT"

    monkeypatch.setenv("APP_ENV", "production")
    boundary_payload = mission_payload(
        expert["id"],
        [second_floors[0]["id"]],
        start="2027-01-10T10:00:00+00:00",
    )
    boundary = client.post(
        f"/pilots/{second_pilot['id']}/missions",
        json=boundary_payload,
        headers=super_admin_headers,
    )
    assert boundary.status_code == 201, boundary.json()
    assert boundary.json()["notifications"][0]["status"] == "failed"
    assert boundary.json()["notifications"][0]["provider_status"] == "unconfigured"
