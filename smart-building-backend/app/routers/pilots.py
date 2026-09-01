"""Pilot and stage workflow API."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.policies import active_role_names, can_review_stage, can_submit_stage
from app.database import get_db
from app.exceptions import SecurityError
from app.models import ImmutableSnapshot, Pilot
from app.schemas.workflow import (
    PilotCreate,
    PilotDetail,
    PilotPage,
    PilotRead,
    SnapshotRead,
    StageActionResult,
    StageDecision,
    StageReject,
    StageSubmit,
)
from app.services.workflow import approve_stage, create_pilot, reject_stage, submit_stage
from app.services.access import enforce_path_pilot_access, scoped_pilot_query
from app.services.security import AuthContext, require_permission

router = APIRouter(
    prefix="/pilots",
    tags=["pilots"],
    dependencies=[Depends(enforce_path_pilot_access)],
)
versioned_router = APIRouter(
    prefix="/api/v1/pilots",
    tags=["pilots"],
    dependencies=[Depends(enforce_path_pilot_access)],
)


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


def _require_stage_submitter(context: AuthContext, stage_number: int) -> None:
    if not can_submit_stage(active_role_names(context.user), stage_number):
        raise SecurityError(
            code="STAGE_SUBMITTER_DENIED",
            message="این کاربر ارسال‌کننده مجاز این مرحله نیست.",
            status_code=403,
            errors=[{"field": "stage_number", "reason": "submitter_role_not_allowed"}],
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
    context: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[Pilot]:
    return scoped_pilot_query(db, context).order_by(Pilot.id).all()


@versioned_router.get("", response_model=PilotPage)
def list_pilots_page(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=160),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    context: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> PilotPage:
    query = scoped_pilot_query(db, context)
    normalized = (q or "").strip()
    if normalized:
        pattern = f"%{normalized}%"
        query = query.filter(
            or_(
                Pilot.code.ilike(pattern),
                Pilot.display_name.ilike(pattern),
                Pilot.project_system_name.ilike(pattern),
            )
        )
    if status_filter:
        query = query.filter(Pilot.status == status_filter)
    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = min(page, total_pages)
    items = query.order_by(Pilot.id).offset((safe_page - 1) * page_size).limit(page_size).all()
    return PilotPage(
        items=items,
        page=safe_page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


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
    context: AuthContext = Depends(require_permission("stages.submit")),
    db: Session = Depends(get_db),
) -> StageActionResult:
    _require_stage_submitter(context, stage_number)
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
