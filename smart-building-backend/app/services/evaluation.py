"""Continuation-review and Stage 15 evaluation business rules."""

from sqlalchemy.orm import Session

from app.exceptions import SecurityError
from app.models import ContinuationReview, Mission, Pilot, PilotEvaluation
from app.schemas.evaluation import (
    ContinuationReviewUpdate,
    PilotEvaluationUpdate,
)
from app.services.security import add_audit_log
from app.services.workflow import invalidate_from_stage


def get_mission(db: Session, mission_id: int) -> Mission:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise SecurityError("MISSION_NOT_FOUND", "مأموریت پیدا نشد.", 404, [])
    return mission


def get_pilot(db: Session, pilot_id: int) -> Pilot:
    pilot = db.get(Pilot, pilot_id)
    if pilot is None:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    return pilot


def update_continuation_review(
    db: Session,
    mission_id: int,
    payload: ContinuationReviewUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> ContinuationReview:
    mission = get_mission(db, mission_id)
    pilot = mission.pilot
    if mission.sequence < 2 or pilot.current_stage < 14:
        raise SecurityError(
            "CONTINUATION_REVIEW_STAGE_LOCKED",
            "بازبینی ادامه برداشت فقط برای مأموریت دوم به بعد و از مرحله ۱۴ مجاز است.",
            409,
            [],
        )
    values = payload.model_dump()
    review = mission.continuation_review
    if review is None:
        review = ContinuationReview(
            mission=mission,
            responsible_user_id=actor_user_id,
            **values,
        )
        db.add(review)
        db.flush()
        changed_fields = set(values)
    else:
        changed_fields = {
            field
            for field, value in values.items()
            if getattr(review, field) != value
        }
        for field, value in values.items():
            setattr(review, field, value)
        review.responsible_user_id = actor_user_id
    if changed_fields:
        invalidate_from_stage(
            db,
            pilot,
            14,
            actor_user_id=actor_user_id,
            reason=f"Continuation review for {mission.code} updated",
        )
    add_audit_log(
        db,
        action="continuation_reviews.saved",
        entity_type="ContinuationReview",
        entity_id=review.id,
        actor_user_id=actor_user_id,
        new_data={
            "mission_code": mission.code,
            "changed_fields": sorted(changed_fields),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(review)
    return review


def update_pilot_evaluation(
    db: Session,
    pilot_id: int,
    payload: PilotEvaluationUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> PilotEvaluation:
    pilot = get_pilot(db, pilot_id)
    if pilot.current_stage < 15:
        raise SecurityError(
            "EVALUATION_STAGE_LOCKED",
            "ثبت ارزیابی پیش از مرحله ۱۵ مجاز نیست.",
            409,
            [],
        )
    values = payload.model_dump()
    evaluation = pilot.evaluation
    if evaluation is None:
        evaluation = PilotEvaluation(
            pilot=pilot,
            responsible_user_id=actor_user_id,
            **values,
        )
        db.add(evaluation)
        db.flush()
        changed_fields = set(values)
    else:
        changed_fields = {
            field
            for field, value in values.items()
            if getattr(evaluation, field) != value
        }
        for field, value in values.items():
            setattr(evaluation, field, value)
        evaluation.responsible_user_id = actor_user_id
    if changed_fields:
        invalidate_from_stage(
            db,
            pilot,
            15,
            actor_user_id=actor_user_id,
            reason="Pilot evaluation updated",
        )
    add_audit_log(
        db,
        action="pilot_evaluations.saved",
        entity_type="PilotEvaluation",
        entity_id=evaluation.id,
        actor_user_id=actor_user_id,
        new_data={"changed_fields": sorted(changed_fields)},
        session_id=session_id,
    )
    db.commit()
    db.refresh(evaluation)
    return evaluation
