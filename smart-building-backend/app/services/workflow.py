"""Business rules for the sequential 19-stage BAMBO pilot workflow."""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import WorkflowError
from app.models import (
    Contact,
    FormF01,
    FormF02,
    ImmutableSnapshot,
    Owner,
    Pilot,
    PilotGate,
    PilotStage,
    Project,
    StageApproval,
    StageSubmission,
)
from app.schemas.workflow import PilotCreate, StageReject, StageSubmit
from app.services.security import add_audit_log
from app.workflow import (
    FINAL_OUTCOMES,
    GATE_DEFINITIONS,
    PILOT_STATUS_AFTER_STAGE,
    STAGE_DEFINITIONS,
    STAGES_BY_NUMBER,
)


def _now() -> datetime:
    return datetime.now(UTC)


def create_pilot(db: Session, payload: PilotCreate, actor_user_id: int | None = None) -> Pilot:
    year = payload.pilot_year or (_now().year - 621)
    sequence = (
        db.query(func.coalesce(func.max(Pilot.sequence), 0))
        .filter(Pilot.pilot_year == year)
        .scalar()
        + 1
    )
    project_number = db.query(func.coalesce(func.max(Pilot.project_number), 0)).scalar() + 1
    code = f"PIL-{year}-{sequence:03d}"
    system_name = f"project-{project_number}"
    display_name = payload.display_name or (
        f"{payload.owner.name} - {payload.project.address[:80]} - {code}"
    )
    pilot = Pilot(
        code=code,
        pilot_year=year,
        sequence=sequence,
        project_number=project_number,
        project_system_name=system_name,
        display_name=display_name,
    )
    owner = Owner(**payload.owner.model_dump())
    owner.contacts.append(
        Contact(
            name=payload.owner.decision_maker_name,
            position=payload.owner.decision_maker_position,
            mobile=payload.owner.primary_mobile,
            is_primary=True,
        )
    )
    pilot.project = Project(
        owner=owner,
        system_name=system_name,
        display_name=display_name,
        **payload.project.model_dump(),
    )
    pilot.stages = [
        PilotStage(
            number=definition.number,
            title=definition.title,
            status="open" if definition.number == 1 else "locked",
        )
        for definition in STAGE_DEFINITIONS
    ]
    pilot.gates = [
        PilotGate(code=code, title=title, after_stage=after_stage)
        for code, title, after_stage in GATE_DEFINITIONS
    ]
    db.add(pilot)
    db.flush()
    add_audit_log(
        db,
        action="pilots.created",
        entity_type="Pilot",
        entity_id=pilot.id,
        actor_user_id=actor_user_id,
        new_data={"code": pilot.code, "project_system_name": pilot.project_system_name},
    )
    db.commit()
    db.refresh(pilot)
    return pilot


def get_stage(db: Session, pilot_id: int, stage_number: int) -> PilotStage:
    stage = (
        db.query(PilotStage)
        .filter(PilotStage.pilot_id == pilot_id, PilotStage.number == stage_number)
        .first()
    )
    if not stage:
        raise WorkflowError(
            code="STAGE_NOT_FOUND",
            message="مرحله برای این پرونده پیدا نشد.",
            stage=stage_number,
            status_code=404,
            errors=[],
        )
    return stage


def _validation_errors(stage_number: int, submission: StageSubmission) -> list[dict[str, str]]:
    definition = STAGES_BY_NUMBER[stage_number]
    errors: list[dict[str, str]] = []
    for key in definition.required_checklist:
        if submission.checklist.get(key) is not True:
            errors.append(
                {
                    "field": f"checklist.{key}",
                    "label": key,
                    "reason": "required_true",
                }
            )
    for key in definition.required_form_fields:
        value = submission.form_data.get(key)
        if value is None or value == "" or value == []:
            errors.append(
                {
                    "field": f"form_data.{key}",
                    "label": key,
                    "reason": "required",
                }
            )
    if stage_number == 3:
        for floor in submission.form_data.get("floors", []):
            if not floor.get("has_valid_dwg"):
                errors.append(
                    {
                        "field": f"floors.{floor['code']}.dwg_file",
                        "label": f"فایل DWG {floor['code']}",
                        "reason": "required_valid_dwg",
                    }
                )
    if stage_number == 19:
        outcome = submission.form_data.get("outcome")
        if outcome and outcome not in FINAL_OUTCOMES:
            errors.append(
                {
                    "field": "form_data.outcome",
                    "label": "نتیجه نهایی",
                    "reason": "invalid_choice",
                }
            )
    return errors


def _canonical_submission_data(
    stage: PilotStage, payload: StageSubmit
) -> tuple[dict, dict[str, bool]]:
    pilot = stage.pilot
    if stage.number in {1, 2}:
        form: FormF01 | None = pilot.form_f01
        if form is None:
            return {}, {}
        if stage.number == 1:
            return (
                {
                    "owner_name": pilot.project.owner.name,
                    "decision_maker": pilot.project.owner.decision_maker_name,
                    "decision_maker_position": pilot.project.owner.decision_maker_position,
                    "owner_mobile": pilot.project.owner.primary_mobile,
                    "project_name": pilot.project.name,
                    "project_address": pilot.project.address,
                    "total_floors": pilot.project.total_floors,
                    "progress_stage": pilot.project.progress_stage,
                    "customer_need": pilot.project.customer_need,
                    "expected_value": pilot.project.expected_value,
                    "result": form.result,
                },
                {
                    "project_active": form.project_active,
                    "imaging_value": form.imaging_value,
                    "decision_maker_available": bool(
                        pilot.project.owner.decision_maker_name
                        and pilot.project.owner.primary_mobile
                    ),
                    "safe_access": form.access_possible,
                    "dwg_available": form.dwg_available,
                    "not_demo_only": form.not_demo_only,
                    "cooperation_capacity": form.continued_capacity,
                },
            )
        return (
            {
                "site_coordinator_name": form.coordinator_name,
                "site_coordinator_phone": form.coordinator_mobile,
                "limitation": form.limitation,
                "result": form.result,
                "referral_deadline": (
                    form.referral_deadline.isoformat() if form.referral_deadline else None
                ),
            },
            {
                "introduction_completed": form.introduction_completed,
                "site_coordinator_registered": bool(
                    form.coordinator_name and form.coordinator_mobile
                ),
                "imaging_consent": form.imaging_accepted,
                "dwg_consent": form.dwg_accepted,
                "feedback_consent": form.feedback_accepted,
                "f01_result_approved": form.result == "approved",
            },
        )
    if stage.number == 3:
        project = pilot.project
        floors = [
            {
                "id": floor.id,
                "code": floor.code,
                "name": floor.name,
                "has_valid_dwg": bool(
                    floor.dwg_file
                    and floor.dwg_file.versions
                    and floor.dwg_file.versions[-1].is_readable
                ),
                "latest_version": (
                    floor.dwg_file.versions[-1].version
                    if floor.dwg_file and floor.dwg_file.versions
                    else None
                ),
            }
            for floor in project.floors
        ]
        return (
            {"project": project.system_name, "floors": floors},
            {
                "floors_registered": len(floors) == project.total_floors,
                "valid_dwg_registered": bool(floors)
                and all(floor["has_valid_dwg"] for floor in floors),
            },
        )
    if stage.number == 4:
        form: FormF02 | None = pilot.form_f02
        if form is None:
            return {}, {}
        return (
            {
                "information_package": form.information_package,
                "progress_status": form.progress_status,
                "limitation": form.limitation,
                "ready_for_capture": form.ready_for_capture,
                "ambiguity": form.ambiguity,
            },
            {
                "main_project_created": form.main_project_registered,
                "floors_created": form.floor_order_confirmed
                and len(pilot.project.floors) == pilot.project.total_floors,
                "main_dwg_configured": form.plan_connections_registered,
                "typical_floors_identified": form.typical_floors_identified,
                "start_point_registered": form.start_point_registered,
                "expert_access_tested": form.expert_access_tested,
                "main_app_display_checked": form.main_app_display_tested,
                "ready_for_capture": form.ready_for_capture,
            },
        )
    if stage.number in {5, 6, 7, 8, 9}:
        mission = pilot.missions[-1] if pilot.missions else None
        if mission is None:
            return {}, {}
        form = mission.form_f03
        floor_states = mission.floor_states
        if stage.number == 5:
            latest_notification = (
                mission.notifications[-1] if mission.notifications else None
            )
            return (
                {
                    "mission_code": mission.code,
                    "scheduled_at": mission.scheduled_start.isoformat(),
                    "scheduled_end": mission.scheduled_end.isoformat(),
                    "expert": {
                        "id": mission.expert.id,
                        "name": mission.expert.display_name,
                    },
                    "floors": [
                        {
                            "id": item.floor.id,
                            "code": item.floor.code,
                            "name": item.floor.name,
                        }
                        for item in floor_states
                    ],
                    "site_contact": {
                        "name": mission.site_contact_name,
                        "mobile": mission.site_contact_mobile,
                    },
                    "location": mission.location,
                    "limitation": mission.limitation,
                    "sla_due_at": mission.sla_due_at.isoformat(),
                    "notification_status": (
                        latest_notification.status if latest_notification else None
                    ),
                },
                {"expert_assignment_confirmed": form.assignment_accepted},
            )
        if stage.number == 6:
            return (
                {
                    "mission_code": mission.code,
                    "stop_condition_reason": form.stop_condition_reason,
                },
                {
                    "assignment_accepted": form.assignment_accepted,
                    "site_entry": form.site_entry_confirmed,
                    "permission": form.permission_confirmed,
                    "ppe": form.ppe_ready,
                    "camera": form.camera_ready,
                    "connection": form.main_app_connected,
                    "charge": form.battery_ready,
                    "storage": form.storage_ready,
                    "project_floor_plan": form.project_floor_plan_confirmed,
                    "test_image": form.test_image_completed,
                    "no_stop_condition": not bool(form.stop_condition_reason),
                },
            )
        if stage.number == 7:
            capture_fields = {
                "correct_floor": "correct_floor",
                "start_point": "start_point_confirmed",
                "main_capture_started": "main_capture_started",
                "continuous_route": "continuous_route",
                "coverage_completed": "coverage_completed",
                "capture_finished": "capture_finished",
                "saved_in_main_app": "saved_in_main_app",
            }
            floor_data = [
                {
                    "floor_id": item.floor_id,
                    "floor_code": item.floor.code,
                    "capture_state": item.capture_state,
                    "capture_started_at": (
                        item.capture_started_at.isoformat()
                        if item.capture_started_at
                        else None
                    ),
                    "capture_finished_at": (
                        item.capture_finished_at.isoformat()
                        if item.capture_finished_at
                        else None
                    ),
                }
                for item in floor_states
            ]
            checklist = {
                checklist_name: bool(floor_states)
                and all(getattr(item, model_field) for item in floor_states)
                for checklist_name, model_field in capture_fields.items()
            }
            checklist["capture_times_registered"] = bool(floor_states) and all(
                item.capture_started_at and item.capture_finished_at
                for item in floor_states
            )
            return (
                {"mission_code": mission.code, "floors": floor_data},
                checklist,
            )
        if stage.number == 8:
            return (
                {
                    "mission_code": mission.code,
                    "floors": [
                        {
                            "floor_id": item.floor_id,
                            "floor_code": item.floor.code,
                            "state": item.capture_state,
                            "failure_reason": item.failure_reason,
                        }
                        for item in floor_states
                    ],
                },
                {
                    "all_floors_resolved": bool(floor_states)
                    and all(
                        item.capture_state != "not_started"
                        for item in floor_states
                    )
                },
            )
        upload_fields = (
            "main_upload_started",
            "main_upload_completed",
            "correct_floor_link",
            "operations_notified",
        )
        return (
            {
                "mission_code": mission.code,
                "floors": [
                    {
                        "floor_id": item.floor_id,
                        "floor_code": item.floor.code,
                        "capture_state": item.capture_state,
                        **{
                            field: getattr(item, field)
                            for field in upload_fields
                        },
                    }
                    for item in floor_states
                ],
            },
            {
                "all_floors_completed": bool(floor_states)
                and all(item.capture_state == "completed" for item in floor_states),
                **{
                    field: bool(floor_states)
                    and all(getattr(item, field) for item in floor_states)
                    for field in upload_fields
                },
                "mission_completed": form.mission_completed,
                "operations_confirmed": form.operations_confirmed,
            },
        )
    return payload.form_data, payload.checklist


def _raise_validation_error(stage_number: int, submission: StageSubmission) -> None:
    errors = _validation_errors(stage_number, submission)
    if errors:
        raise WorkflowError(
            code="STAGE_VALIDATION_FAILED",
            message="مرحله قابل تأیید نیست.",
            stage=stage_number,
            status_code=422,
            errors=errors,
        )


def submit_stage(
    db: Session,
    pilot_id: int,
    stage_number: int,
    payload: StageSubmit,
    submitted_by: str,
    actor_user_id: int | None = None,
) -> tuple[PilotStage, StageSubmission]:
    stage = get_stage(db, pilot_id, stage_number)
    if stage.status == "locked" or stage.pilot.current_stage != stage_number:
        raise WorkflowError(
            code="STAGE_LOCKED",
            message="مرحله قبلی هنوز تأیید نشده است.",
            stage=stage_number,
            status_code=409,
            errors=[],
        )
    if stage.status not in {"open", "needs_revision"}:
        raise WorkflowError(
            code="STAGE_TRANSITION_NOT_ALLOWED",
            message="این مرحله در وضعیت قابل ارسال نیست.",
            stage=stage_number,
            status_code=409,
            errors=[{"field": "stage.status", "label": "وضعیت مرحله", "reason": stage.status}],
        )

    form_data, checklist = _canonical_submission_data(stage, payload)
    submitted_at = _now()
    submission = StageSubmission(
        stage=stage,
        version=stage.latest_version + 1,
        form_data=form_data,
        checklist=checklist,
        submitted_by=submitted_by,
        submitted_at=submitted_at,
    )
    _raise_validation_error(stage_number, submission)
    stage.latest_version = submission.version
    stage.status = "submitted"
    stage.submitted_at = submitted_at
    db.add(submission)
    db.flush()
    add_audit_log(
        db,
        action="stages.submitted",
        entity_type="PilotStage",
        entity_id=stage.id,
        actor_user_id=actor_user_id,
        new_data={"stage": stage.number, "version": submission.version},
    )
    db.commit()
    db.refresh(stage)
    db.refresh(submission)
    return stage, submission


def invalidate_from_stage(
    db: Session,
    pilot: Pilot,
    stage_number: int,
    *,
    actor_user_id: int | None,
    reason: str,
) -> bool:
    target = next(stage for stage in pilot.stages if stage.number == stage_number)
    if pilot.current_stage < stage_number and target.status not in {"submitted", "approved"}:
        return False
    if pilot.current_stage == stage_number and target.status in {"open", "needs_revision"}:
        return False

    for stage in pilot.stages:
        if stage.number == stage_number:
            stage.status = "needs_revision"
            stage.approved_at = None
        elif stage.number > stage_number:
            stage.status = "locked"
            stage.approved_at = None
            stage.submitted_at = None
    for gate in pilot.gates:
        if gate.after_stage >= stage_number:
            gate.status = "locked"
            gate.passed_at = None
    pilot.current_stage = stage_number
    pilot.status = (
        "candidate"
        if stage_number <= 2
        else "waiting_documents"
        if stage_number <= 4
        else "operations"
    )
    add_audit_log(
        db,
        action="stages.invalidated",
        entity_type="Pilot",
        entity_id=pilot.id,
        actor_user_id=actor_user_id,
        old_data={"current_stage": target.number, "status": "approved"},
        new_data={"current_stage": stage_number, "status": "needs_revision"},
        reason=reason,
    )
    return True


def _latest_submission(stage: PilotStage) -> StageSubmission:
    if not stage.submissions:
        raise WorkflowError(
            code="SUBMISSION_NOT_FOUND",
            message="نسخه‌ای برای بازبینی ثبت نشده است.",
            stage=stage.number,
            status_code=409,
            errors=[],
        )
    return stage.submissions[-1]


def approve_stage(
    db: Session,
    pilot_id: int,
    stage_number: int,
    reviewer: str,
    actor_user_id: int | None = None,
    comment: str | None = None,
) -> tuple[PilotStage, StageSubmission, ImmutableSnapshot]:
    stage = get_stage(db, pilot_id, stage_number)
    if stage.status != "submitted":
        raise WorkflowError(
            code="STAGE_TRANSITION_NOT_ALLOWED",
            message="فقط مرحله ارسال‌شده قابل تأیید است.",
            stage=stage_number,
            status_code=409,
            errors=[],
        )
    submission = _latest_submission(stage)
    _raise_validation_error(stage_number, submission)

    reviewed_at = _now()
    approval = StageApproval(
        submission=submission,
        decision="approved",
        reviewer=reviewer,
        reviewed_at=reviewed_at,
    )
    content = {
        "pilot": {
            "id": stage.pilot.id,
            "code": stage.pilot.code,
            "project_system_name": stage.pilot.project_system_name,
        },
        "stage": {"number": stage.number, "title": stage.title},
        "submission": {
            "version": submission.version,
            "form_data": submission.form_data,
            "checklist": submission.checklist,
            "submitted_by": submission.submitted_by,
            "submitted_at": submission.submitted_at.isoformat(),
        },
        "approval": {"reviewer": reviewer, "approved_at": reviewed_at.isoformat()},
    }
    serialized = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snapshot = ImmutableSnapshot(
        approval=approval,
        pilot_id=stage.pilot.id,
        stage_number=stage.number,
        version=submission.version,
        name=(
            f"{stage.pilot.code}_STAGE-{stage.number}_V{submission.version}_"
            f"{reviewed_at.strftime('%Y%m%dT%H%M%SZ')}.json"
        ),
        content=content,
        content_hash=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        created_at=reviewed_at,
    )

    submission.status = "approved"
    stage.status = "approved"
    stage.approved_at = reviewed_at
    gate = next((gate for gate in stage.pilot.gates if gate.after_stage == stage.number), None)
    if gate:
        gate.status = "passed"
        gate.passed_at = reviewed_at

    if stage.number < len(STAGE_DEFINITIONS):
        next_stage = next(item for item in stage.pilot.stages if item.number == stage.number + 1)
        next_stage.status = "open"
        stage.pilot.current_stage = next_stage.number
        stage.pilot.status = PILOT_STATUS_AFTER_STAGE.get(stage.number, stage.pilot.status)
    else:
        outcome = submission.form_data["outcome"]
        stage.pilot.status = "converted" if outcome == "contract" else "closed"

    db.add(snapshot)
    db.flush()
    add_audit_log(
        db,
        action="stages.approved",
        entity_type="PilotStage",
        entity_id=stage.id,
        actor_user_id=actor_user_id,
        new_data={"stage": stage.number, "version": submission.version},
        reason=comment,
    )
    db.commit()
    db.refresh(stage)
    db.refresh(submission)
    db.refresh(snapshot)
    return stage, submission, snapshot


def reject_stage(
    db: Session,
    pilot_id: int,
    stage_number: int,
    payload: StageReject,
    reviewer: str,
    actor_user_id: int | None = None,
) -> tuple[PilotStage, StageSubmission]:
    stage = get_stage(db, pilot_id, stage_number)
    if stage.status != "submitted":
        raise WorkflowError(
            code="STAGE_TRANSITION_NOT_ALLOWED",
            message="فقط مرحله ارسال‌شده قابل رد است.",
            stage=stage_number,
            status_code=409,
            errors=[],
        )
    submission = _latest_submission(stage)
    review = StageApproval(
        submission=submission,
        decision="rejected",
        reviewer=reviewer,
        reason=payload.reason,
        correction_items=payload.correction_items,
    )
    submission.status = "rejected"
    stage.status = "needs_revision"
    db.add(review)
    db.flush()
    add_audit_log(
        db,
        action="stages.rejected",
        entity_type="PilotStage",
        entity_id=stage.id,
        actor_user_id=actor_user_id,
        old_data={"status": "submitted"},
        new_data={"status": "needs_revision", "version": submission.version},
        reason=payload.reason or "; ".join(payload.correction_items),
    )
    db.commit()
    db.refresh(stage)
    db.refresh(submission)
    return stage, submission
