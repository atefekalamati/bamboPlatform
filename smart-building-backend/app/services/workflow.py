"""Business rules for the sequential 19-stage BAMBO pilot workflow."""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import WorkflowError
from app.models import (
    ImmutableSnapshot,
    Pilot,
    PilotGate,
    PilotStage,
    StageApproval,
    StageSubmission,
)
from app.schemas.workflow import PilotCreate, StageReject, StageSubmit
from app.workflow import (
    FINAL_OUTCOMES,
    GATE_DEFINITIONS,
    PILOT_STATUS_AFTER_STAGE,
    STAGE_DEFINITIONS,
    STAGES_BY_NUMBER,
)


def _now() -> datetime:
    return datetime.now(UTC)


def create_pilot(db: Session, payload: PilotCreate) -> Pilot:
    year = payload.pilot_year or (_now().year - 621)
    sequence = (
        db.query(func.coalesce(func.max(Pilot.sequence), 0))
        .filter(Pilot.pilot_year == year)
        .scalar()
        + 1
    )
    project_number = db.query(func.coalesce(func.max(Pilot.project_number), 0)).scalar() + 1
    pilot = Pilot(
        code=f"PIL-{year}-{sequence:03d}",
        pilot_year=year,
        sequence=sequence,
        project_number=project_number,
        project_system_name=f"project-{project_number}",
        display_name=payload.display_name,
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
    db: Session, pilot_id: int, stage_number: int, payload: StageSubmit
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

    submitted_at = _now()
    submission = StageSubmission(
        stage=stage,
        version=stage.latest_version + 1,
        form_data=payload.form_data,
        checklist=payload.checklist,
        submitted_by=payload.submitted_by,
        submitted_at=submitted_at,
    )
    _raise_validation_error(stage_number, submission)
    stage.latest_version = submission.version
    stage.status = "submitted"
    stage.submitted_at = submitted_at
    db.add(submission)
    db.commit()
    db.refresh(stage)
    db.refresh(submission)
    return stage, submission


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
    db: Session, pilot_id: int, stage_number: int, reviewer: str
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
    db.commit()
    db.refresh(stage)
    db.refresh(submission)
    db.refresh(snapshot)
    return stage, submission, snapshot


def reject_stage(
    db: Session, pilot_id: int, stage_number: int, payload: StageReject
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
        reviewer=payload.reviewer,
        reason=payload.reason,
        correction_items=payload.correction_items,
    )
    submission.status = "rejected"
    stage.status = "needs_revision"
    db.add(review)
    db.commit()
    db.refresh(stage)
    db.refresh(submission)
    return stage, submission
