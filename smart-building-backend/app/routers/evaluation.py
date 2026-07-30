"""Continuation capture and evaluation APIs for stages 14 and 15."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.models import ContinuationReview, Mission, PilotEvaluation, User
from app.schemas.evaluation import (
    ContinuationReviewRead,
    ContinuationReviewUpdate,
    PilotEvaluationRead,
    PilotEvaluationUpdate,
)
from app.services.evaluation import (
    get_mission,
    get_pilot,
    update_continuation_review,
    update_pilot_evaluation,
)
from app.services.security import AuthContext, require_permission

router = APIRouter(tags=["evaluation"])


def _is_restricted_capture_expert(user: User) -> bool:
    role_names = {role.name for role in user.roles if role.is_active}
    return "capture_expert" in role_names and not role_names.intersection(
        {"super_admin", "operations"}
    )


def _require_mission_access(user: User, mission: Mission) -> None:
    if _is_restricted_capture_expert(user) and mission.expert_user_id != user.id:
        raise SecurityError(
            "MISSION_ACCESS_DENIED",
            "دسترسی به مأموریت کارشناس دیگر مجاز نیست.",
            403,
            [],
        )


@router.get(
    "/missions/{mission_id}/continuation-review",
    response_model=ContinuationReviewRead,
)
def get_continuation_review(
    mission_id: int,
    context: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> ContinuationReview:
    mission = get_mission(db, mission_id)
    _require_mission_access(context.user, mission)
    review = mission.continuation_review
    if review is None:
        raise SecurityError(
            "CONTINUATION_REVIEW_NOT_FOUND",
            "بازبینی ادامه برداشت هنوز ثبت نشده است.",
            404,
            [],
        )
    return review


@router.put(
    "/missions/{mission_id}/continuation-review",
    response_model=ContinuationReviewRead,
)
def put_continuation_review(
    mission_id: int,
    payload: ContinuationReviewUpdate,
    context: AuthContext = Depends(require_permission("missions.manage")),
    db: Session = Depends(get_db),
) -> ContinuationReview:
    _require_mission_access(context.user, get_mission(db, mission_id))
    return update_continuation_review(
        db,
        mission_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get(
    "/pilots/{pilot_id}/evaluation",
    response_model=PilotEvaluationRead,
)
def get_evaluation(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> PilotEvaluation:
    evaluation = get_pilot(db, pilot_id).evaluation
    if evaluation is None:
        raise SecurityError(
            "EVALUATION_NOT_FOUND",
            "ارزیابی پایلوت هنوز ثبت نشده است.",
            404,
            [],
        )
    return evaluation


@router.put(
    "/pilots/{pilot_id}/evaluation",
    response_model=PilotEvaluationRead,
)
def put_evaluation(
    pilot_id: int,
    payload: PilotEvaluationUpdate,
    context: AuthContext = Depends(require_permission("pilots.manage")),
    db: Session = Depends(get_db),
) -> PilotEvaluation:
    return update_pilot_evaluation(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )
