"""Stage 10-13, G4, external evidence, notification, and F05 tests."""

from datetime import datetime

from conftest import (
    login_with_otp,
    prepare_pilot_through_g2,
    submit_and_approve_stage,
)
from app.main import app


def _create_expert(client, headers, mobile: str = "09156666666") -> dict:
    roles = client.get("/roles", headers=headers).json()
    role_id = next(role["id"] for role in roles if role["name"] == "capture_expert")
    response = client.post(
        "/users",
        json={
            "mobile": mobile,
            "display_name": "Capture expert",
            "role_ids": [role_id],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return response.json()


def _prepare_pilot_through_g3(
    client,
    headers,
    *,
    expert_mobile: str = "09156666666",
) -> tuple[dict, dict]:
    pilot, floors = prepare_pilot_through_g2(
        client,
        headers,
        total_floors=1,
    )
    expert = _create_expert(client, headers, expert_mobile)
    mission_response = client.post(
        f"/pilots/{pilot['id']}/missions",
        json={
            "expert_user_id": expert["id"],
            "scheduled_start": "2027-01-10T08:00:00+00:00",
            "scheduled_end": "2027-01-10T10:00:00+00:00",
            "floor_ids": [floors[0]["id"]],
            "location": "Pilot site",
            "site_contact_name": "Site contact",
            "site_contact_mobile": "09152222222",
        },
        headers=headers,
    )
    assert mission_response.status_code == 201, mission_response.json()
    mission = mission_response.json()

    f03_response = client.put(
        f"/missions/{mission['id']}/forms/f03",
        json={
            "assignment_accepted": True,
            "site_entry_confirmed": True,
            "permission_confirmed": True,
            "ppe_ready": True,
            "camera_ready": True,
            "main_app_connected": True,
            "battery_ready": True,
            "storage_ready": True,
            "project_floor_plan_confirmed": True,
            "test_image_completed": True,
            "mission_completed": True,
            "operations_confirmed": True,
            "started_at": "2027-01-10T08:10:00+00:00",
            "finished_at": "2027-01-10T09:40:00+00:00",
        },
        headers=headers,
    )
    assert f03_response.status_code == 200, f03_response.json()
    floor_response = client.put(
        f"/missions/{mission['id']}/floors/{floors[0]['id']}",
        json={
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
            "main_upload_started": True,
            "main_upload_completed": True,
            "correct_floor_link": True,
            "operations_notified": True,
        },
        headers=headers,
    )
    assert floor_response.status_code == 200, floor_response.json()
    for stage_number in range(5, 10):
        submit_and_approve_stage(client, pilot["id"], stage_number, headers)
    return pilot, mission


def _external_platform_payload() -> dict:
    return {
        "project_reference": "main-platform-project-42",
        "platform_status": "available",
        "processing_started": True,
        "route_detected": True,
        "plan_connected": True,
        "tour_ready": True,
        "captures_menu_checked": True,
        "latest_capture_checked": True,
        "last_visit_checked": True,
        "checked_at": "2027-01-10T11:00:00+00:00",
    }


def _training_payload() -> dict:
    return {
        "training_completed": True,
        "login_trained": True,
        "project_trained": True,
        "floor_trained": True,
        "plan_trained": True,
        "tour_trained": True,
        "navigation_trained": True,
        "support_trained": True,
        "independent_use_confirmed": True,
    }


def test_experience_openapi_contract():
    schema = app.openapi()
    for path in (
        "/pilots/{pilot_id}/external-platform",
        "/pilots/{pilot_id}/forms/f04",
        "/pilots/{pilot_id}/external-evidence/{capability}",
        "/pilots/{pilot_id}/notifications/main-output",
        "/pilots/{pilot_id}/incidents",
        "/incidents/{incident_id}/close",
        "/missions/{mission_id}/continuation-review",
        "/pilots/{pilot_id}/evaluation",
    ):
        assert path in schema["paths"]
    for name in (
        "ExternalPlatformUpdate",
        "FormF04Patch",
        "ExternalEvidenceUpdate",
        "IncidentCreate",
        "IncidentClose",
        "ContinuationReviewUpdate",
        "PilotEvaluationUpdate",
    ):
        assert name in schema["components"]["schemas"]


def test_stage_10_platform_status_and_incident_sla(
    client,
    super_admin_headers,
):
    pilot, mission = _prepare_pilot_through_g3(client, super_admin_headers)
    pilot_id = pilot["id"]

    evidence_too_early = client.put(
        f"/pilots/{pilot_id}/external-evidence/project_summary",
        json={
            "status": "checked",
            "checked_at": "2027-01-10T11:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert evidence_too_early.status_code == 409
    assert evidence_too_early.json()["code"] == "EXTERNAL_EVIDENCE_STAGE_LOCKED"

    url_rejected = client.put(
        f"/pilots/{pilot_id}/external-platform",
        json=_external_platform_payload()
        | {"project_reference": "https://example.invalid/tour"},
        headers=super_admin_headers,
    )
    assert url_rejected.status_code == 422

    platform_down = client.put(
        f"/pilots/{pilot_id}/external-platform",
        json={
            "project_reference": "main-platform-project-42",
            "platform_status": "down",
            "processing_started": False,
            "route_detected": False,
            "plan_connected": False,
            "tour_ready": False,
            "captures_menu_checked": False,
            "latest_capture_checked": False,
            "last_visit_checked": False,
            "reason": "External platform is temporarily unavailable.",
            "checked_at": "2027-01-10T10:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert platform_down.status_code == 200, platform_down.json()
    down_incident = client.post(
        f"/pilots/{pilot_id}/incidents",
        json={
            "mission_id": mission["id"],
            "occurred_at": "2027-01-10T10:00:00+00:00",
            "stage_number": 10,
            "severity": "important",
            "incident_type": "main_platform",
            "description": "External platform is down.",
        },
        headers=super_admin_headers,
    )
    assert down_incident.status_code == 201, down_incident.json()
    down_occurred_at = datetime.fromisoformat(down_incident.json()["occurred_at"])
    down_due_at = datetime.fromisoformat(down_incident.json()["response_due_at"])
    assert (down_due_at - down_occurred_at).total_seconds() == 4 * 60 * 60
    normal_incident = client.post(
        f"/pilots/{pilot_id}/incidents",
        json={
            "occurred_at": "2027-01-10T14:00:00+00:00",
            "stage_number": 10,
            "severity": "normal",
            "incident_type": "process",
            "description": "A normal operational follow-up is required.",
        },
        headers=super_admin_headers,
    )
    assert normal_incident.status_code == 201, normal_incident.json()
    normal_due_at = datetime.fromisoformat(normal_incident.json()["response_due_at"])
    assert normal_due_at.date() == datetime(2027, 1, 10).date()
    assert (normal_due_at.hour, normal_due_at.minute) == (23, 59)
    incomplete_close = client.post(
        f"/incidents/{normal_incident.json()['id']}/close",
        json={
            "root_cause": "Routine process gap.",
            "corrective_action": "Document the routine.",
            "result": "Routine documented.",
            "lessons_learned": "Assign every action before closure.",
            "confirmed": True,
        },
        headers=super_admin_headers,
    )
    assert incomplete_close.status_code == 422
    assert incomplete_close.json()["code"] == "INCIDENT_CLOSE_INCOMPLETE"
    down_blocked = client.post(
        f"/pilots/{pilot_id}/stages/10/submit",
        json={"checklist": {"tour_ready": True}},
        headers=super_admin_headers,
    )
    assert down_blocked.status_code == 422

    platform_response = client.put(
        f"/pilots/{pilot_id}/external-platform",
        json=_external_platform_payload(),
        headers=super_admin_headers,
    )
    assert platform_response.status_code == 200, platform_response.json()
    assert platform_response.json()["platform_status"] == "available"
    stage_10 = submit_and_approve_stage(
        client,
        pilot_id,
        10,
        super_admin_headers,
    )
    assert (
        stage_10["snapshot"]["content"]["submission"]["form_data"][
            "project_reference"
        ]
        == "main-platform-project-42"
    )

    notification = client.post(
        f"/pilots/{pilot_id}/notifications/main-output",
        json={},
        headers=super_admin_headers,
    )
    assert notification.status_code == 201, notification.json()
    assert notification.json()["status"] == "delivered"
    submit_and_approve_stage(client, pilot_id, 11, super_admin_headers)


def _prepare_pilot_through_g4(
    client,
    headers,
    *,
    expert_mobile: str = "09158886666",
) -> tuple[dict, dict]:
    pilot, mission = _prepare_pilot_through_g3(
        client,
        headers,
        expert_mobile=expert_mobile,
    )
    pilot_id = pilot["id"]
    platform_response = client.put(
        f"/pilots/{pilot_id}/external-platform",
        json=_external_platform_payload(),
        headers=headers,
    )
    assert platform_response.status_code == 200, platform_response.json()
    submit_and_approve_stage(client, pilot_id, 10, headers)
    notification = client.post(
        f"/pilots/{pilot_id}/notifications/main-output",
        json={},
        headers=headers,
    )
    assert notification.status_code == 201, notification.json()
    submit_and_approve_stage(client, pilot_id, 11, headers)
    training = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json=_training_payload(),
        headers=headers,
    )
    assert training.status_code == 200, training.json()
    submit_and_approve_stage(client, pilot_id, 12, headers)
    follow_up = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json={
            "owner_logged_in": True,
            "project_opened": True,
            "main_tour_viewed": True,
            "viewing_result": "Owner reviewed the main output.",
            "first_follow_up_at": "2027-01-11T09:00:00+00:00",
            "second_follow_up_at": "2027-01-14T09:00:00+00:00",
        },
        headers=headers,
    )
    assert follow_up.status_code == 200, follow_up.json()
    submit_and_approve_stage(client, pilot_id, 13, headers)
    return pilot, mission


def test_stages_14_to_16_and_g5(
    client,
    super_admin_headers,
):
    pilot, initial_mission = _prepare_pilot_through_g4(
        client,
        super_admin_headers,
    )
    pilot_id = pilot["id"]
    floor_id = initial_mission["floor_states"][0]["floor_id"]

    continuation_response = client.post(
        f"/pilots/{pilot_id}/missions",
        json={
            "expert_user_id": initial_mission["expert_user_id"],
            "scheduled_start": "2027-02-10T08:00:00+00:00",
            "scheduled_end": "2027-02-10T10:00:00+00:00",
            "floor_ids": [floor_id],
            "location": "Pilot site - continuation",
            "site_contact_name": "Site contact",
            "site_contact_mobile": "09152222222",
        },
        headers=super_admin_headers,
    )
    assert continuation_response.status_code == 201, continuation_response.json()
    continuation = continuation_response.json()
    assert continuation["sequence"] == 2
    assert continuation["code"] == f"MIS-{pilot['code']}-02"

    f03_response = client.put(
        f"/missions/{continuation['id']}/forms/f03",
        json={
            "assignment_accepted": True,
            "site_entry_confirmed": True,
            "permission_confirmed": True,
            "ppe_ready": True,
            "camera_ready": True,
            "main_app_connected": True,
            "battery_ready": True,
            "storage_ready": True,
            "project_floor_plan_confirmed": True,
            "test_image_completed": True,
            "mission_completed": True,
            "operations_confirmed": True,
            "started_at": "2027-02-10T08:10:00+00:00",
            "finished_at": "2027-02-10T09:40:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert f03_response.status_code == 200, f03_response.json()
    floor_response = client.put(
        f"/missions/{continuation['id']}/floors/{floor_id}",
        json={
            "capture_state": "completed",
            "correct_floor": True,
            "start_point_confirmed": True,
            "main_capture_started": True,
            "continuous_route": True,
            "coverage_completed": True,
            "capture_finished": True,
            "saved_in_main_app": True,
            "capture_started_at": "2027-02-10T08:15:00+00:00",
            "capture_finished_at": "2027-02-10T09:30:00+00:00",
            "main_upload_started": True,
            "main_upload_completed": True,
            "correct_floor_link": True,
            "operations_notified": True,
        },
        headers=super_admin_headers,
    )
    assert floor_response.status_code == 200, floor_response.json()

    missing_review = client.post(
        f"/pilots/{pilot_id}/stages/14/submit",
        json={"checklist": {"new_mission": True}},
        headers=super_admin_headers,
    )
    assert missing_review.status_code == 422
    review_payload = {
        **{
            f"stage_{number}_confirmed": True
            for number in range(5, 14)
        },
        "independent_result": (
            "The continuation capture completed independently and all "
            "stage checks were repeated."
        ),
    }
    review_media_rejected = client.put(
        f"/missions/{continuation['id']}/continuation-review",
        json=review_payload | {"report_url": "https://example.invalid/report"},
        headers=super_admin_headers,
    )
    assert review_media_rejected.status_code == 422
    review = client.put(
        f"/missions/{continuation['id']}/continuation-review",
        json=review_payload,
        headers=super_admin_headers,
    )
    assert review.status_code == 200, review.json()
    _create_expert(client, super_admin_headers, "09159998888")
    other_expert_headers = login_with_otp(client, "09159998888")
    restricted_review = client.get(
        f"/missions/{continuation['id']}/continuation-review",
        headers=other_expert_headers,
    )
    assert restricted_review.status_code == 403
    stage_14 = submit_and_approve_stage(
        client,
        pilot_id,
        14,
        super_admin_headers,
    )
    assert stage_14["snapshot"]["content"]["submission"]["form_data"][
        "mission_code"
    ] == continuation["code"]

    evidence = client.put(
        f"/pilots/{pilot_id}/external-evidence/actual_progress",
        json={
            "status": "checked",
            "checked_at": "2027-02-11T08:00:00+00:00",
            "result": "The existing main-platform report was reviewed.",
        },
        headers=super_admin_headers,
    )
    assert evidence.status_code == 200, evidence.json()
    audio_media_rejected = client.put(
        f"/pilots/{pilot_id}/external-evidence/manager_audio_report",
        json={
            "status": "checked",
            "checked_at": "2027-02-11T08:10:00+00:00",
            "audio_url": "https://example.invalid/audio.mp3",
        },
        headers=super_admin_headers,
    )
    assert audio_media_rejected.status_code == 422
    audio_status = client.put(
        f"/pilots/{pilot_id}/external-evidence/manager_audio_report",
        json={
            "status": "checked",
            "checked_at": "2027-02-11T08:10:00+00:00",
            "result": "Availability was checked; no audio was copied.",
        },
        headers=super_admin_headers,
    )
    assert audio_status.status_code == 200, audio_status.json()

    evaluation_payload = {
        "operations_status": "approved",
        "operations_result": "Operations completed as planned.",
        "quality_status": "approved",
        "quality_result": "Capture quality met the pilot requirement.",
        "technical_status": "needs_action",
        "technical_result": "One non-critical optimization was assigned.",
        "customer_status": "approved",
        "customer_result": "The owner confirmed useful remote access.",
        "commercial_status": "approved",
        "commercial_result": "The opportunity is ready for a proposal.",
        "one_page_summary": (
            "The pilot demonstrated operational, customer, and commercial "
            "value. One non-critical technical action remains tracked."
        ),
    }
    evaluation_file_rejected = client.put(
        f"/pilots/{pilot_id}/evaluation",
        json=evaluation_payload
        | {"report_file": "data:application/pdf;base64,invalid"},
        headers=super_admin_headers,
    )
    assert evaluation_file_rejected.status_code == 422
    evaluation = client.put(
        f"/pilots/{pilot_id}/evaluation",
        json=evaluation_payload,
        headers=super_admin_headers,
    )
    assert evaluation.status_code == 200, evaluation.json()
    stage_15 = submit_and_approve_stage(
        client,
        pilot_id,
        15,
        super_admin_headers,
    )
    evidence_names = {
        item["capability"]
        for item in stage_15["snapshot"]["content"]["submission"]["form_data"][
            "external_evidence"
        ]
    }
    assert {"actual_progress", "manager_audio_report"} <= evidence_names

    closing = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json={
            "main_platform_login_count": 4,
            "viewed_sections": ["project", "floor", "plan", "tour"],
            "visit_reduction_result": "confirmed",
            "customer_need_summary": "Remote progress visibility remains clear.",
            "closing_decision": "proposal",
            "realized_value": "Fewer site visits and faster owner visibility.",
            "purchase_blocker": "No active blocker.",
            "project_count": 3,
            "usage_frequency": "weekly",
            "user_count": 5,
            "decision_maker": "Owner CEO",
        },
        headers=super_admin_headers,
    )
    assert closing.status_code == 200, closing.json()
    stage_16 = submit_and_approve_stage(
        client,
        pilot_id,
        16,
        super_admin_headers,
    )
    assert stage_16["snapshot"]["content"]["submission"]["form_data"][
        "decision"
    ] == "proposal"
    after_g5 = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert after_g5["current_stage"] == 17
    assert next(gate for gate in after_g5["gates"] if gate["code"] == "G5")[
        "status"
    ] == "passed"

    changed_evaluation = client.put(
        f"/pilots/{pilot_id}/evaluation",
        json=evaluation_payload
        | {
            "technical_status": "approved",
            "technical_result": "The optimization was completed.",
        },
        headers=super_admin_headers,
    )
    assert changed_evaluation.status_code == 200, changed_evaluation.json()
    after_change = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert after_change["current_stage"] == 15
    assert after_change["stages"][14]["status"] == "needs_revision"
    assert next(gate for gate in after_change["gates"] if gate["code"] == "G5")[
        "status"
    ] == "locked"
    stage_16_snapshots = client.get(
        f"/pilots/{pilot_id}/stages/16/snapshots",
        headers=super_admin_headers,
    ).json()
    assert len(stage_16_snapshots) == 1


def test_customer_success_incident_blocker_and_g4(
    client,
    super_admin_headers,
):
    pilot, mission = _prepare_pilot_through_g3(
        client,
        super_admin_headers,
    )
    pilot_id = pilot["id"]
    platform_response = client.put(
        f"/pilots/{pilot_id}/external-platform",
        json=_external_platform_payload(),
        headers=super_admin_headers,
    )
    assert platform_response.status_code == 200, platform_response.json()
    submit_and_approve_stage(client, pilot_id, 10, super_admin_headers)
    notification = client.post(
        f"/pilots/{pilot_id}/notifications/main-output",
        json={},
        headers=super_admin_headers,
    )
    assert notification.status_code == 201, notification.json()
    submit_and_approve_stage(client, pilot_id, 11, super_admin_headers)

    training = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json=_training_payload(),
        headers=super_admin_headers,
    )
    assert training.status_code == 200, training.json()
    submit_and_approve_stage(client, pilot_id, 12, super_admin_headers)

    invalid_capability = client.put(
        f"/pilots/{pilot_id}/external-evidence/raw_report",
        json={
            "status": "checked",
            "checked_at": "2027-01-11T08:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert invalid_capability.status_code == 422
    evidence_media_rejected = client.put(
        f"/pilots/{pilot_id}/external-evidence/project_summary",
        json={
            "status": "checked",
            "checked_at": "2027-01-11T08:00:00+00:00",
            "report_url": "https://example.invalid/report",
        },
        headers=super_admin_headers,
    )
    assert evidence_media_rejected.status_code == 422
    evidence = client.put(
        f"/pilots/{pilot_id}/external-evidence/project_summary",
        json={
            "status": "checked",
            "checked_at": "2027-01-11T08:00:00+00:00",
            "result": "Summary capability was present and current.",
        },
        headers=super_admin_headers,
    )
    assert evidence.status_code == 200, evidence.json()

    user_id = client.get(
        "/auth/me",
        headers=super_admin_headers,
    ).json()["id"]
    wrong_route = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json={
            "issue_description": "Owner cannot access the main platform.",
            "issue_category": "access",
            "issue_route": "technical",
            "issue_owner_user_id": user_id,
            "issue_due_at": "2027-01-11T12:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert wrong_route.status_code == 422
    routed_issue = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json={
            "issue_description": "Owner cannot access the main platform.",
            "issue_category": "access",
            "issue_route": "support",
            "issue_owner_user_id": user_id,
            "issue_due_at": "2027-01-11T12:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert routed_issue.status_code == 200, routed_issue.json()

    incident_response = client.post(
        f"/pilots/{pilot_id}/incidents",
        json={
            "mission_id": mission["id"],
            "occurred_at": "2027-01-11T08:00:00+00:00",
            "stage_number": 13,
            "severity": "critical",
            "incident_type": "main_platform",
            "description": "Main platform unavailable during owner follow-up.",
            "containment_action": "Owner was informed and follow-up was paused.",
            "notified_people": ["pilot manager", "technical team"],
            "owner_user_id": user_id,
            "correction_due_at": "2027-01-11T10:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert incident_response.status_code == 201, incident_response.json()
    incident = incident_response.json()
    occurred_at = datetime.fromisoformat(incident["occurred_at"])
    response_due_at = datetime.fromisoformat(incident["response_due_at"])
    assert (response_due_at - occurred_at).total_seconds() == 30 * 60

    follow_up = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json={
            "owner_logged_in": True,
            "project_opened": True,
            "main_tour_viewed": True,
            "viewing_result": "Owner reviewed the main output successfully.",
            "first_follow_up_at": "2027-01-11T09:00:00+00:00",
            "second_follow_up_at": "2027-01-14T09:00:00+00:00",
            "useful": True,
            "coverage_score": 9,
            "quality_score": 8,
            "satisfaction_score": 9,
        },
        headers=super_admin_headers,
    )
    assert follow_up.status_code == 200, follow_up.json()

    blocked = client.post(
        f"/pilots/{pilot_id}/stages/13/submit",
        json={
            "form_data": {"follow_up_result": "client supplied"},
            "checklist": {"no_open_critical_incident": True},
        },
        headers=super_admin_headers,
    )
    assert blocked.status_code == 422
    assert any(
        error["field"] == f"incidents.{incident['code']}"
        and error["reason"] == "open_critical_incident"
        for error in blocked.json()["errors"]
    )

    unconfirmed_close = client.post(
        f"/incidents/{incident['id']}/close",
        json={
            "root_cause": "External processing service outage.",
            "corrective_action": "Service recovered and output rechecked.",
            "result": "Output available again.",
            "lessons_learned": "Verify availability before owner follow-up.",
            "confirmed": False,
        },
        headers=super_admin_headers,
    )
    assert unconfirmed_close.status_code == 422
    closed = client.post(
        f"/incidents/{incident['id']}/close",
        json={
            "root_cause": "External processing service outage.",
            "corrective_action": "Service recovered and output rechecked.",
            "result": "Output available again.",
            "evidence": "Status rechecked by technical operator.",
            "lessons_learned": "Verify availability before owner follow-up.",
            "confirmed": True,
        },
        headers=super_admin_headers,
    )
    assert closed.status_code == 200, closed.json()
    assert closed.json()["status"] == "closed"

    stage_13 = submit_and_approve_stage(
        client,
        pilot_id,
        13,
        super_admin_headers,
    )
    assert stage_13["snapshot"]["content"]["submission"]["form_data"][
        "external_evidence"
    ][0]["capability"] == "project_summary"
    after_g4 = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert after_g4["current_stage"] == 14
    assert next(gate for gate in after_g4["gates"] if gate["code"] == "G4")[
        "status"
    ] == "passed"

    reopened = client.post(
        f"/pilots/{pilot_id}/incidents",
        json={
            "occurred_at": "2027-01-15T08:00:00+00:00",
            "stage_number": 14,
            "severity": "critical",
            "incident_type": "access",
            "description": "Critical owner access failure.",
        },
        headers=super_admin_headers,
    )
    assert reopened.status_code == 201, reopened.json()
    after_reopen = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert after_reopen["current_stage"] == 13
    assert after_reopen["stages"][12]["status"] == "needs_revision"
    assert next(gate for gate in after_reopen["gates"] if gate["code"] == "G4")[
        "status"
    ] == "locked"
    snapshots = client.get(
        f"/pilots/{pilot_id}/stages/13/snapshots",
        headers=super_admin_headers,
    ).json()
    assert len(snapshots) == 1


def test_failed_sms_needs_alternate_delivery_record(
    client,
    super_admin_headers,
    monkeypatch,
):
    pilot, _ = _prepare_pilot_through_g3(
        client,
        super_admin_headers,
        expert_mobile="09157776666",
    )
    pilot_id = pilot["id"]
    platform_response = client.put(
        f"/pilots/{pilot_id}/external-platform",
        json=_external_platform_payload(),
        headers=super_admin_headers,
    )
    assert platform_response.status_code == 200
    submit_and_approve_stage(client, pilot_id, 10, super_admin_headers)

    monkeypatch.setenv("APP_ENV", "production")
    failed = client.post(
        f"/pilots/{pilot_id}/notifications/main-output",
        json={},
        headers=super_admin_headers,
    )
    assert failed.status_code == 201
    assert failed.json()["status"] == "failed"
    blocked = client.post(
        f"/pilots/{pilot_id}/stages/11/submit",
        json={},
        headers=super_admin_headers,
    )
    assert blocked.status_code == 422
    assert any(
        error["field"] == "checklist.delivery_registered"
        for error in blocked.json()["errors"]
    )

    alternate = client.post(
        f"/pilots/{pilot_id}/notifications/main-output",
        json={"alternate_contact_method": "Telephone call recorded by support."},
        headers=super_admin_headers,
    )
    assert alternate.status_code == 201
    assert alternate.json()["alternate_contact_method"]
    submit_and_approve_stage(client, pilot_id, 11, super_admin_headers)
