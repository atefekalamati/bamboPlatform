"""Pilot and stage workflow API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.policies import active_role_names, can_review_stage
from app.database import get_db
from app.exceptions import SecurityError
from app.models import ImmutableSnapshot, Pilot
from app.schemas.workflow import (
    PilotCreate,
    PilotDetail,
    PilotRead,
    SnapshotRead,
    StageActionResult,
    StageDecision,
    StageReject,
    StageSubmit,
)
from app.services.workflow import approve_stage, create_pilot, reject_stage, submit_stage
from app.services.security import AuthContext, require_permission

router = APIRouter(prefix="/pilots", tags=["pilots"])


def _require_stage_reviewer(context: AuthContext, stage_number: int, action: str) -> None:
    if not can_review_stage(active_role_names(context.user), stage_number, action):
        raise SecurityError(
            code="STAGE_REVIEWER_DENIED",
            message="این کاربر تأییدکننده مجاز این مرحله نیست.",
            status_code=403,
            errors=[
                {
                    "field": "stage_number",
                    "reason": "reviewer_role_not_allowed",
                }
            ],
        )


@router.post("", response_model=PilotDetail, status_code=status.HTTP_201_CREATED)
def create_pilot_endpoint(
    payload: PilotCreate,
    context: AuthContext = Depends(require_permission("pilots.create")),
    db: Session = Depends(get_db),
) -> Pilot:
    return create_pilot(db, payload, actor_user_id=context.user.id)


@router.get("", response_model=list[PilotRead])
def list_pilots(
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[Pilot]:
    return db.query(Pilot).order_by(Pilot.id).all()


@router.get("/{pilot_id}", response_model=PilotDetail)
def get_pilot(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> Pilot:
    pilot = db.get(Pilot, pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return pilot


@router.post("/{pilot_id}/stages/{stage_number}/submit", response_model=StageActionResult)
def submit_stage_endpoint(
    pilot_id: int,
    stage_number: int,
    payload: StageSubmit,
    context: AuthContext = Depends(require_permission("checklists.manage")),
    db: Session = Depends(get_db),
) -> StageActionResult:
    stage, submission = submit_stage(
        db,
        pilot_id,
        stage_number,
        payload,
        submitted_by=context.user.display_name,
        actor_user_id=context.user.id,
    )
    return StageActionResult(stage=stage, submission=submission)


@router.post("/{pilot_id}/stages/{stage_number}/approve", response_model=StageActionResult)
def approve_stage_endpoint(
    pilot_id: int,
    stage_number: int,
    payload: StageDecision,
    context: AuthContext = Depends(require_permission("gate_approval.approve")),
    db: Session = Depends(get_db),
) -> StageActionResult:
    _require_stage_reviewer(context, stage_number, "approve")
    stage, submission, snapshot = approve_stage(
        db,
        pilot_id,
        stage_number,
        reviewer=context.user.display_name,
        actor_user_id=context.user.id,
        comment=payload.comment,
    )
    return StageActionResult(stage=stage, submission=submission, snapshot=snapshot)


@router.post("/{pilot_id}/stages/{stage_number}/reject", response_model=StageActionResult)
def reject_stage_endpoint(
    pilot_id: int,
    stage_number: int,
    payload: StageReject,
    context: AuthContext = Depends(require_permission("gate_approval.reject")),
    db: Session = Depends(get_db),
) -> StageActionResult:
    _require_stage_reviewer(context, stage_number, "reject")
    stage, submission = reject_stage(
        db,
        pilot_id,
        stage_number,
        payload,
        reviewer=context.user.display_name,
        actor_user_id=context.user.id,
    )
    return StageActionResult(stage=stage, submission=submission)


@router.get(
    "/{pilot_id}/stages/{stage_number}/snapshots",
    response_model=list[SnapshotRead],
)
def list_stage_snapshots(
    pilot_id: int,
    stage_number: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[ImmutableSnapshot]:
    return (
        db.query(ImmutableSnapshot)
        .filter(
            ImmutableSnapshot.pilot_id == pilot_id,
            ImmutableSnapshot.stage_number == stage_number,
        )
        .order_by(ImmutableSnapshot.version)
        .all()
    )
