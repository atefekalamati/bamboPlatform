"""Pilot and stage workflow API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
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

router = APIRouter(prefix="/pilots", tags=["pilots"])


@router.post("", response_model=PilotDetail, status_code=status.HTTP_201_CREATED)
def create_pilot_endpoint(payload: PilotCreate, db: Session = Depends(get_db)) -> Pilot:
    return create_pilot(db, payload)


@router.get("", response_model=list[PilotRead])
def list_pilots(db: Session = Depends(get_db)) -> list[Pilot]:
    return db.query(Pilot).order_by(Pilot.id).all()


@router.get("/{pilot_id}", response_model=PilotDetail)
def get_pilot(pilot_id: int, db: Session = Depends(get_db)) -> Pilot:
    pilot = db.get(Pilot, pilot_id)
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return pilot


@router.post("/{pilot_id}/stages/{stage_number}/submit", response_model=StageActionResult)
def submit_stage_endpoint(
    pilot_id: int,
    stage_number: int,
    payload: StageSubmit,
    db: Session = Depends(get_db),
) -> StageActionResult:
    stage, submission = submit_stage(db, pilot_id, stage_number, payload)
    return StageActionResult(stage=stage, submission=submission)


@router.post("/{pilot_id}/stages/{stage_number}/approve", response_model=StageActionResult)
def approve_stage_endpoint(
    pilot_id: int,
    stage_number: int,
    payload: StageDecision,
    db: Session = Depends(get_db),
) -> StageActionResult:
    stage, submission, snapshot = approve_stage(db, pilot_id, stage_number, payload.reviewer)
    return StageActionResult(stage=stage, submission=submission, snapshot=snapshot)


@router.post("/{pilot_id}/stages/{stage_number}/reject", response_model=StageActionResult)
def reject_stage_endpoint(
    pilot_id: int,
    stage_number: int,
    payload: StageReject,
    db: Session = Depends(get_db),
) -> StageActionResult:
    stage, submission = reject_stage(db, pilot_id, stage_number, payload)
    return StageActionResult(stage=stage, submission=submission)


@router.get(
    "/{pilot_id}/stages/{stage_number}/snapshots",
    response_model=list[SnapshotRead],
)
def list_stage_snapshots(
    pilot_id: int, stage_number: int, db: Session = Depends(get_db)
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
