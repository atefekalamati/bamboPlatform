"""Mission scheduling, F03, and per-Floor operations APIs."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.models import Mission, Pilot, User
from app.schemas.operations import (
    CaptureExpertRead,
    FormF03Read,
    FormF03Update,
    MissionCreate,
    MissionFloorRead,
    MissionFloorUpdate,
    MissionRead,
    MissionReschedule,
)
from app.services.operations import (
    create_mission,
    get_mission,
    reschedule_mission,
    update_f03,
    update_mission_floor,
)
from app.services.security import AuthContext, require_permission
from app.services.access import enforce_path_pilot_access

router = APIRouter(tags=["missions"], dependencies=[Depends(enforce_path_pilot_access)])


def _is_restricted_capture_expert(user: User) -> bool:
    role_names = {role.name for role in user.roles if role.is_active}
    return "capture_expert" in role_names and not role_names.intersection(
        {"super_admin", "operations"}
    )


def _require_coordinator(user: User) -> None:
    if _is_restricted_capture_expert(user):
        raise SecurityError(
            "MISSION_ACCESS_DENIED",
            "کارشناس برداشت اجازه ایجاد یا زمان‌بندی مجدد مأموریت را ندارد.",
            403,
            [],
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
    "/missions/capture-experts",
    response_model=list[CaptureExpertRead],
)
def list_capture_experts(
    context: AuthContext = Depends(require_permission("missions.manage")),
    db: Session = Depends(get_db),
) -> list[User]:
    _require_coordinator(context.user)
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.locked_at.is_(None))
        .filter(User.roles.any(name="capture_expert", is_active=True))
        .order_by(User.display_name, User.id)
        .all()
    )


@router.post(
    "/pilots/{pilot_id}/missions",
    response_model=MissionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_mission_endpoint(
    pilot_id: int,
    payload: MissionCreate,
    context: AuthContext = Depends(require_permission("missions.manage")),
    db: Session = Depends(get_db),
) -> Mission:
    _require_coordinator(context.user)
    return create_mission(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get("/pilots/{pilot_id}/missions", response_model=list[MissionRead])
def list_missions(
    pilot_id: int,
    context: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[Mission]:
    if db.get(Pilot, pilot_id) is None:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    query = db.query(Mission).filter(Mission.pilot_id == pilot_id)
    if _is_restricted_capture_expert(context.user):
        query = query.filter(Mission.expert_user_id == context.user.id)
    return query.order_by(Mission.sequence).all()


@router.get("/missions/{mission_id}", response_model=MissionRead)
def get_mission_endpoint(
    mission_id: int,
    context: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> Mission:
    mission = get_mission(db, mission_id)
    _require_mission_access(context.user, mission)
    return mission


@router.patch("/missions/{mission_id}", response_model=MissionRead)
def reschedule_mission_endpoint(
    mission_id: int,
    payload: MissionReschedule,
    context: AuthContext = Depends(require_permission("missions.manage")),
    db: Session = Depends(get_db),
) -> Mission:
    _require_coordinator(context.user)
    return reschedule_mission(
        db,
        mission_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get("/missions/{mission_id}/forms/f03", response_model=FormF03Read)
def get_f03(
    mission_id: int,
    context: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
):
    mission = get_mission(db, mission_id)
    _require_mission_access(context.user, mission)
    return mission.form_f03


@router.put("/missions/{mission_id}/forms/f03", response_model=FormF03Read)
def put_f03(
    mission_id: int,
    payload: FormF03Update,
    context: AuthContext = Depends(require_permission("missions.manage")),
    db: Session = Depends(get_db),
):
    mission = get_mission(db, mission_id)
    _require_mission_access(context.user, mission)
    return update_f03(
        db,
        mission_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.put(
    "/missions/{mission_id}/floors/{floor_id}",
    response_model=MissionFloorRead,
)
def put_mission_floor(
    mission_id: int,
    floor_id: int,
    payload: MissionFloorUpdate,
    context: AuthContext = Depends(require_permission("missions.manage")),
    db: Session = Depends(get_db),
):
    mission = get_mission(db, mission_id)
    _require_mission_access(context.user, mission)
    return update_mission_floor(
        db,
        mission_id,
        floor_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )
