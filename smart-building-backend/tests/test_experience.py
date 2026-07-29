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
        "/pilots/{pilot_id}/commercial-proposal",
        "/pilots/{pilot_id}/commercial-follow-ups",
        "/pilots/{pilot_id}/commercial-follow-ups/{schedule_slot}",
        "/pilots/{pilot_id}/final-outcome",
        "/pilots/{pilot_id}/final-outcome/approve",
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
        "CommercialProposalUpdate",
        "CustomerFollowUpUpdate",
        "FinalOutcomeUpdate",
        "FinalOutcomeApprove",
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


def _prepare_pilot_through_g5(
    client,
    headers,
    *,
    expert_mobile: str = "09157775555",
) -> dict:
    pilot, initial_mission = _prepare_pilot_through_g4(
        client,
        headers,
        expert_mobile=expert_mobile,
    )
    pilot_id = pilot["id"]
    floor_id = initial_mission["floor_states"][0]["floor_id"]
    continuation = client.post(
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
        headers=headers,
    )
    assert continuation.status_code == 201, continuation.json()
    mission = continuation.json()
    form_f03 = client.put(
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
            "started_at": "2027-02-10T08:10:00+00:00",
            "finished_at": "2027-02-10T09:40:00+00:00",
        },
        headers=headers,
    )
    assert form_f03.status_code == 200, form_f03.json()
    floor = client.put(
        f"/missions/{mission['id']}/floors/{floor_id}",
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
        headers=headers,
    )
    assert floor.status_code == 200, floor.json()
    review = client.put(
        f"/missions/{mission['id']}/continuation-review",
        json={
            **{
                f"stage_{number}_confirmed": True
                for number in range(5, 14)
            },
            "independent_result": (
                "Continuation completed independently with all checks repeated."
            ),
        },
        headers=headers,
    )
    assert review.status_code == 200, review.json()
    submit_and_approve_stage(client, pilot_id, 14, headers)
    evaluation = client.put(
        f"/pilots/{pilot_id}/evaluation",
        json={
            "operations_status": "approved",
            "operations_result": "Operations completed.",
            "quality_status": "approved",
            "quality_result": "Quality met the pilot target.",
            "technical_status": "approved",
            "technical_result": "Technical checks completed.",
            "customer_status": "approved",
            "customer_result": "Customer value was confirmed.",
            "commercial_status": "approved",
            "commercial_result": "Commercial proposal is appropriate.",
            "one_page_summary": "The pilot is ready for commercial closing.",
        },
        headers=headers,
    )
    assert evaluation.status_code == 200, evaluation.json()
    submit_and_approve_stage(client, pilot_id, 15, headers)
    closing = client.patch(
        f"/pilots/{pilot_id}/forms/f04",
        json={
            "main_platform_login_count": 4,
            "viewed_sections": ["project", "floor", "plan", "tour"],
            "visit_reduction_result": "confirmed",
            "customer_need_summary": "Remote progress visibility is required.",
            "closing_decision": "proposal",
            "realized_value": "Fewer site visits.",
            "purchase_blocker": "No active blocker.",
            "project_count": 3,
            "usage_frequency": "weekly",
            "user_count": 5,
            "decision_maker": "Owner CEO",
        },
        headers=headers,
    )
    assert closing.status_code == 200, closing.json()
    submit_and_approve_stage(client, pilot_id, 16, headers)
    return pilot


def test_stages_17_to_19_full_commercial_workflow(
    client,
    super_admin_headers,
):
    pilot = _prepare_pilot_through_g5(client, super_admin_headers)
    pilot_id = pilot["id"]
    proposal_payload = {
        "project_count": 3,
        "floor_count": 12,
        "area_sqm": 14500.5,
        "frequency": "weekly",
        "period": "12 months",
        "user_count": 8,
        "support_scope": "Business-hours support and onboarding.",
        "features": ["capture", "tour", "progress reporting"],
        "proposal_file_name": "BAMBO-proposal-v1.pdf",
        "proposal_file_size": 245760,
        "proposal_file_sha256": "a" * 64,
        "decision_maker": "Owner CEO",
        "follow_up_at": "2027-03-01T09:00:00+00:00",
    }

    missing_proposal = client.get(
        f"/pilots/{pilot_id}/commercial-proposal",
        headers=super_admin_headers,
    )
    assert missing_proposal.status_code == 404
    unsafe_file = client.put(
        f"/pilots/{pilot_id}/commercial-proposal",
        json=proposal_payload
        | {"proposal_file_name": "https://example.invalid/proposal.pdf"},
        headers=super_admin_headers,
    )
    assert unsafe_file.status_code == 422
    external_file_field = client.put(
        f"/pilots/{pilot_id}/commercial-proposal",
        json=proposal_payload | {"proposal_url": "https://example.invalid/proposal"},
        headers=super_admin_headers,
    )
    assert external_file_field.status_code == 422
    proposal = client.put(
        f"/pilots/{pilot_id}/commercial-proposal",
        json=proposal_payload,
        headers=super_admin_headers,
    )
    assert proposal.status_code == 200, proposal.json()
    assert proposal.json()["proposal_file_sha256"] == "a" * 64
    stage_17 = submit_and_approve_stage(
        client,
        pilot_id,
        17,
        super_admin_headers,
    )
    proposal_snapshot = stage_17["snapshot"]["content"]["submission"]["form_data"]
    assert proposal_snapshot["proposal_file"] == {
        "name": "BAMBO-proposal-v1.pdf",
        "size": 245760,
        "sha256": "a" * 64,
    }
    assert "proposal_url" not in proposal_snapshot

    invalid_schedule = client.put(
        f"/pilots/{pilot_id}/commercial-follow-ups/day_2",
        json={
            "obstacle": "Budget review.",
            "action": "Review the business case.",
            "owner_user_id": proposal.json()["responsible_user_id"],
            "due_at": "2027-03-04T09:00:00+00:00",
            "result": "Review meeting completed.",
            "completed_at": "2027-03-04T10:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert invalid_schedule.status_code == 422
    assert invalid_schedule.json()["code"] == "FOLLOW_UP_SCHEDULE_INVALID"

    follow_up_dates = {
        "day_0": "2027-03-01T09:00:00+00:00",
        "day_2": "2027-03-03T09:00:00+00:00",
        "day_5": "2027-03-06T09:00:00+00:00",
        "day_7_10": "2027-03-09T09:00:00+00:00",
    }
    for slot in ("day_0", "day_2", "day_5"):
        response = client.put(
            f"/pilots/{pilot_id}/commercial-follow-ups/{slot}",
            json={
                "obstacle": f"Commercial obstacle for {slot}.",
                "action": f"Commercial action for {slot}.",
                "owner_user_id": proposal.json()["responsible_user_id"],
                "due_at": follow_up_dates[slot],
                "result": f"Commercial result for {slot}.",
                "completed_at": follow_up_dates[slot],
            },
            headers=super_admin_headers,
        )
        assert response.status_code == 200, response.json()

    incomplete_stage_18 = client.post(
        f"/pilots/{pilot_id}/stages/18/submit",
        json={},
        headers=super_admin_headers,
    )
    assert incomplete_stage_18.status_code == 422
    final_follow_up = client.put(
        f"/pilots/{pilot_id}/commercial-follow-ups/day_7_10",
        json={
            "obstacle": "Final legal review.",
            "action": "Resolve contract wording.",
            "owner_user_id": proposal.json()["responsible_user_id"],
            "due_at": follow_up_dates["day_7_10"],
            "result": "Contract wording accepted.",
            "completed_at": "2027-03-09T10:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert final_follow_up.status_code == 200, final_follow_up.json()
    listed_follow_ups = client.get(
        f"/pilots/{pilot_id}/commercial-follow-ups",
        headers=super_admin_headers,
    )
    assert listed_follow_ups.status_code == 200
    assert [item["schedule_slot"] for item in listed_follow_ups.json()] == [
        "day_0",
        "day_2",
        "day_5",
        "day_7_10",
    ]
    stage_18 = submit_and_approve_stage(
        client,
        pilot_id,
        18,
        super_admin_headers,
    )
    assert len(
        stage_18["snapshot"]["content"]["submission"]["form_data"]["follow_ups"]
    ) == 4

    missing_outcome = client.post(
        f"/pilots/{pilot_id}/stages/19/submit",
        json={},
        headers=super_admin_headers,
    )
    assert missing_outcome.status_code == 422
    incomplete_contract = client.put(
        f"/pilots/{pilot_id}/final-outcome",
        json={"outcome": "contract"},
        headers=super_admin_headers,
    )
    assert incomplete_contract.status_code == 422
    users = client.get("/users", headers=super_admin_headers)
    assert users.status_code == 200
    success_owner_id = users.json()[0]["id"]
    final_outcome = client.put(
        f"/pilots/{pilot_id}/final-outcome",
        json={
            "outcome": "contract",
            "reason": "Pilot value was verified.",
            "success_owner_user_id": success_owner_id,
            "periodic_capture": True,
            "contracted_user_count": 8,
            "first_capture_at": "2027-04-01T08:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert final_outcome.status_code == 200, final_outcome.json()
    unapproved_outcome = client.post(
        f"/pilots/{pilot_id}/stages/19/submit",
        json={},
        headers=super_admin_headers,
    )
    assert unapproved_outcome.status_code == 422

    roles = client.get("/roles", headers=super_admin_headers).json()
    customer_success_role = next(
        role for role in roles if role["name"] == "customer_success"
    )
    customer_success_user = client.post(
        "/users",
        json={
            "mobile": "09154443333",
            "display_name": "Customer success reviewer",
            "role_ids": [customer_success_role["id"]],
        },
        headers=super_admin_headers,
    )
    assert customer_success_user.status_code == 201, customer_success_user.json()
    customer_success_headers = login_with_otp(client, "09154443333")
    invalid_approver = client.post(
        f"/pilots/{pilot_id}/final-outcome/approve",
        json={"confirmed": True},
        headers=customer_success_headers,
    )
    assert invalid_approver.status_code == 403
    assert invalid_approver.json()["code"] == "FINAL_OUTCOME_APPROVER_INVALID"
    missing_confirmation = client.post(
        f"/pilots/{pilot_id}/final-outcome/approve",
        json={"confirmed": False},
        headers=super_admin_headers,
    )
    assert missing_confirmation.status_code == 422
    approved_outcome = client.post(
        f"/pilots/{pilot_id}/final-outcome/approve",
        json={"confirmed": True},
        headers=super_admin_headers,
    )
    assert approved_outcome.status_code == 200, approved_outcome.json()
    assert approved_outcome.json()["pilot_manager_approved"] is True

    stage_19 = submit_and_approve_stage(
        client,
        pilot_id,
        19,
        super_admin_headers,
    )
    final_snapshot = stage_19["snapshot"]["content"]["submission"]["form_data"]
    assert final_snapshot["outcome"] == "contract"
    assert final_snapshot["contracted_user_count"] == 8
    completed_pilot = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert completed_pilot["status"] == "converted"
    assert completed_pilot["current_stage"] == 19
    assert all(stage["status"] == "approved" for stage in completed_pilot["stages"])
    closing_form = client.get(
        f"/pilots/{pilot_id}/forms/f04",
        headers=super_admin_headers,
    )
    assert closing_form.status_code == 200
    assert closing_form.json()["final_result"] == "contract"
    assert closing_form.json()["customer_success_user_id"] == success_owner_id
    assert closing_form.json()["pilot_manager_user_id"] is not None

    changed_outcome = client.put(
        f"/pilots/{pilot_id}/final-outcome",
        json={"outcome": "negotiation"},
        headers=super_admin_headers,
    )
    assert changed_outcome.status_code == 200, changed_outcome.json()
    assert changed_outcome.json()["pilot_manager_approved"] is False
    invalidated_pilot = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert invalidated_pilot["status"] == "proposal_sent"
    assert invalidated_pilot["current_stage"] == 19
    assert invalidated_pilot["stages"][18]["status"] == "needs_revision"
    preserved_snapshots = client.get(
        f"/pilots/{pilot_id}/stages/19/snapshots",
        headers=super_admin_headers,
    )
    assert preserved_snapshots.status_code == 200
    assert len(preserved_snapshots.json()) == 1
    assert preserved_snapshots.json()[0]["content"]["submission"]["form_data"][
        "outcome"
    ] == "contract"

    blocked_resubmission = client.post(
        f"/pilots/{pilot_id}/stages/19/submit",
        json={},
        headers=super_admin_headers,
    )
    assert blocked_resubmission.status_code == 422
    reapproved_outcome = client.post(
        f"/pilots/{pilot_id}/final-outcome/approve",
        json={"confirmed": True},
        headers=super_admin_headers,
    )
    assert reapproved_outcome.status_code == 200, reapproved_outcome.json()
    submit_and_approve_stage(client, pilot_id, 19, super_admin_headers)
    closed_pilot = client.get(
        f"/pilots/{pilot_id}",
        headers=super_admin_headers,
    ).json()
    assert closed_pilot["status"] == "closed"
    final_snapshots = client.get(
        f"/pilots/{pilot_id}/stages/19/snapshots",
        headers=super_admin_headers,
    ).json()
    assert len(final_snapshots) == 2
    assert final_snapshots[1]["content"]["submission"]["form_data"][
        "outcome"
    ] == "negotiation"


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
