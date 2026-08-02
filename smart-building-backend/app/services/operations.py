"""Mission scheduling, F03 state, Floor operations, and notification services."""

from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import SecurityError
from app.models import (
    Floor,
    FormF03,
    Mission,
    MissionFloor,
    Notification,
    Pilot,
    User,
)
from app.schemas.operations import (
    FormF03Update,
    MissionCreate,
    MissionFloorUpdate,
    MissionReschedule,
)
from app.services.security import add_audit_log, utc_now
from app.services.notifications import create_notification
from app.services.workflow import invalidate_from_stage


def get_mission(db: Session, mission_id: int) -> Mission:
    mission = db.get(Mission, mission_id)
    if not mission:
        raise SecurityError(
            "MISSION_NOT_FOUND",
            "مأموریت پیدا نشد.",
            404,
            [],
        )
    return mission


def _mission_invalidation_stage(mission: Mission, initial_stage: int) -> int:
    return 14 if mission.sequence > 1 else initial_stage


def _capture_expert(db: Session, user_id: int) -> User:
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .with_for_update()
        .first()
    )
    if (
        user is None
        or not user.is_active
        or user.locked_at is not None
        or not any(role.name == "capture_expert" and role.is_active for role in user.roles)
    ):
        raise SecurityError(
            "CAPTURE_EXPERT_INVALID",
            "کارشناس برداشت فعال و معتبر پیدا نشد.",
            422,
            [{"field": "expert_user_id", "reason": "invalid_capture_expert"}],
        )
    return user


def _mission_floors(db: Session, pilot: Pilot, floor_ids: list[int]) -> list[Floor]:
    floors = (
        db.query(Floor)
        .filter(
            Floor.project_id == pilot.project.id,
            Floor.id.in_(floor_ids),
        )
        .order_by(Floor.level_order)
        .all()
    )
    if len(floors) != len(floor_ids):
        raise SecurityError(
            "MISSION_FLOOR_INVALID",
            "یک یا چند Floor متعلق به این پروژه نیست.",
            422,
            [{"field": "floor_ids", "reason": "invalid_project_floor"}],
        )
    return floors


def _ensure_no_expert_conflict(
    db: Session,
    *,
    expert_user_id: int,
    scheduled_start,
    scheduled_end,
    exclude_mission_id: int | None = None,
) -> None:
    query = db.query(Mission).filter(
        Mission.expert_user_id == expert_user_id,
        Mission.status != "cancelled",
        Mission.scheduled_start < scheduled_end,
        Mission.scheduled_end > scheduled_start,
    )
    if exclude_mission_id is not None:
        query = query.filter(Mission.id != exclude_mission_id)
    conflict = query.order_by(Mission.scheduled_start).first()
    if conflict:
        raise SecurityError(
            "MISSION_EXPERT_CONFLICT",
            "کارشناس در بازه زمانی انتخاب‌شده مأموریت دیگری دارد.",
            409,
            [
                {
                    "field": "scheduled_start",
                    "reason": "expert_schedule_conflict",
                    "mission_code": conflict.code,
                }
            ],
        )


def _dispatch_mission_notification(
    db: Session,
    mission: Mission,
    *,
    template: str,
) -> Notification:
    event_type = "mission.assigned" if template == "mission_created" else "mission.rescheduled"
    title = "مأموریت جدید" if template == "mission_created" else "زمان مأموریت تغییر کرد"
    return create_notification(
        db,
        recipient_user=mission.expert,
        notification_type=event_type,
        category="MISSION",
        priority="HIGH",
        title=title,
        body=f"{title} برای پرونده {mission.pilot.code}: {mission.code}",
        short_body=f"{title}: {mission.code}",
        entity_type="Mission",
        entity_id=mission.id,
        pilot_id=mission.pilot_id,
        mission_id=mission.id,
        action_url=f"/pilots/{mission.pilot_id}/stages/5",
        template_code=template,
        payload={
            "mission_code": mission.code,
            "scheduled_start": mission.scheduled_start.isoformat(),
            "scheduled_end": mission.scheduled_end.isoformat(),
        },
        deduplication_key=f"{event_type}:{mission.id}:{mission.updated_at.isoformat()}",
    )


def create_mission(
    db: Session,
    pilot_id: int,
    payload: MissionCreate,
    *,
    actor_user_id: int,
    session_id: int,
) -> Mission:
    pilot = (
        db.query(Pilot)
        .filter(Pilot.id == pilot_id)
        .with_for_update()
        .first()
    )
    if not pilot:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    is_initial_mission = pilot.current_stage == 5 and not pilot.missions
    is_continuation_mission = pilot.current_stage == 14 and bool(pilot.missions)
    if not (is_initial_mission or is_continuation_mission):
        raise SecurityError(
            "MISSION_STAGE_LOCKED",
            "مأموریت اولیه در مرحله ۵ و مأموریت ادامه برداشت در مرحله ۱۴ ثبت می‌شود.",
            409,
            [
                {
                    "field": "pilot.current_stage",
                    "reason": "stage_5_or_14_required",
                }
            ],
        )
    expert = _capture_expert(db, payload.expert_user_id)
    floors = _mission_floors(db, pilot, payload.floor_ids)
    _ensure_no_expert_conflict(
        db,
        expert_user_id=expert.id,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
    )
    sequence = (
        db.query(func.coalesce(func.max(Mission.sequence), 0))
        .filter(Mission.pilot_id == pilot.id)
        .scalar()
        + 1
    )
    mission = Mission(
        pilot=pilot,
        sequence=sequence,
        code=f"MIS-{pilot.code}-{sequence:02d}",
        expert=expert,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        location=payload.location,
        site_contact_name=payload.site_contact_name,
        site_contact_mobile=payload.site_contact_mobile,
        limitation=payload.limitation,
        sla_due_at=utc_now() + timedelta(days=1),
        created_by_user_id=actor_user_id,
        floor_states=[MissionFloor(floor=floor) for floor in floors],
        form_f03=FormF03(responsible_user_id=expert.id),
    )
    db.add(mission)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecurityError(
            "MISSION_CREATE_CONFLICT",
            "ثبت هم‌زمان مأموریت با تعارض روبه‌رو شد؛ دوباره تلاش کنید.",
            409,
            [],
        ) from exc
    notification = _dispatch_mission_notification(
        db,
        mission,
        template="mission_created",
    )
    invalidate_from_stage(
        db,
        pilot,
        14 if is_continuation_mission else 5,
        actor_user_id=actor_user_id,
        reason="Mission created",
    )
    add_audit_log(
        db,
        action="missions.created",
        entity_type="Mission",
        entity_id=mission.id,
        actor_user_id=actor_user_id,
        new_data={
            "code": mission.code,
            "expert_user_id": expert.id,
            "floor_ids": [floor.id for floor in floors],
            "notification_status": notification.status,
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(mission)
    return mission


def reschedule_mission(
    db: Session,
    mission_id: int,
    payload: MissionReschedule,
    *,
    actor_user_id: int,
    session_id: int,
) -> Mission:
    mission = (
        db.query(Mission)
        .filter(Mission.id == mission_id)
        .with_for_update()
        .first()
    )
    if not mission:
        raise SecurityError("MISSION_NOT_FOUND", "مأموریت پیدا نشد.", 404, [])
    if mission.status in {"completed", "cancelled"}:
        raise SecurityError(
            "MISSION_UPDATE_NOT_ALLOWED",
            "مأموریت تکمیل‌شده یا لغوشده قابل زمان‌بندی مجدد نیست.",
            409,
            [],
        )

    values = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    expert = (
        _capture_expert(db, values["expert_user_id"])
        if "expert_user_id" in values
        else mission.expert
    )
    scheduled_start = values.get("scheduled_start", mission.scheduled_start)
    scheduled_end = values.get("scheduled_end", mission.scheduled_end)
    _ensure_no_expert_conflict(
        db,
        expert_user_id=expert.id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        exclude_mission_id=mission.id,
    )
    old_data = {
        field: getattr(mission, field)
        for field in values
    }
    changed = {
        field: value
        for field, value in values.items()
        if getattr(mission, field) != value
    }
    if not changed:
        raise SecurityError(
            "MISSION_NO_CHANGES",
            "تغییری در مأموریت ثبت نشده است.",
            409,
            [],
        )
    for field, value in changed.items():
        setattr(mission, field, value)
    if "expert_user_id" in changed:
        mission.expert = expert
        mission.form_f03.responsible_user_id = expert.id

    notification = None
    if {"expert_user_id", "scheduled_start", "scheduled_end"} & changed.keys():
        db.flush()
        notification = _dispatch_mission_notification(
            db,
            mission,
            template="mission_rescheduled",
        )
    invalidate_from_stage(
        db,
        mission.pilot,
        _mission_invalidation_stage(mission, 5),
        actor_user_id=actor_user_id,
        reason=payload.reason,
    )
    add_audit_log(
        db,
        action="missions.updated",
        entity_type="Mission",
        entity_id=mission.id,
        actor_user_id=actor_user_id,
        old_data={
            field: value.isoformat() if hasattr(value, "isoformat") else value
            for field, value in old_data.items()
            if field in changed
        },
        new_data={
            field: value.isoformat() if hasattr(value, "isoformat") else value
            for field, value in changed.items()
        }
        | (
            {"notification_status": notification.status}
            if notification is not None
            else {}
        ),
        reason=payload.reason,
        session_id=session_id,
    )
    db.commit()
    db.refresh(mission)
    return mission


def update_f03(
    db: Session,
    mission_id: int,
    payload: FormF03Update,
    *,
    actor_user_id: int,
    session_id: int,
) -> FormF03:
    mission = get_mission(db, mission_id)
    form = mission.form_f03
    values = payload.model_dump()
    changed_fields = {
        field for field, value in values.items() if getattr(form, field) != value
    }
    if not changed_fields:
        return form
    for field, value in values.items():
        setattr(form, field, value)

    readiness_fields = {
        "site_entry_confirmed",
        "permission_confirmed",
        "ppe_ready",
        "camera_ready",
        "main_app_connected",
        "battery_ready",
        "storage_ready",
        "project_floor_plan_confirmed",
        "test_image_completed",
        "stop_condition_reason",
    }
    if "assignment_accepted" in changed_fields:
        invalidation_stage = 5
    elif changed_fields & readiness_fields:
        invalidation_stage = 6
    elif changed_fields & {"started_at", "finished_at"}:
        invalidation_stage = 7
    else:
        invalidation_stage = 9
    invalidate_from_stage(
        db,
        mission.pilot,
        _mission_invalidation_stage(mission, invalidation_stage),
        actor_user_id=actor_user_id,
        reason="F03 updated",
    )

    readiness_values = (
        form.assignment_accepted,
        form.site_entry_confirmed,
        form.permission_confirmed,
        form.ppe_ready,
        form.camera_ready,
        form.main_app_connected,
        form.battery_ready,
        form.storage_ready,
        form.project_floor_plan_confirmed,
        form.test_image_completed,
    )
    if form.mission_completed:
        mission.status = "completed"
    elif form.started_at:
        mission.status = "in_progress"
    elif all(readiness_values) and not form.stop_condition_reason:
        mission.status = "ready"
    elif form.assignment_accepted:
        mission.status = "assigned"
    else:
        mission.status = "scheduled"

    add_audit_log(
        db,
        action="forms.f03_saved",
        entity_type="Mission",
        entity_id=mission.id,
        actor_user_id=actor_user_id,
        new_data={
            "changed_fields": sorted(changed_fields),
            "mission_status": mission.status,
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(form)
    return form


def update_mission_floor(
    db: Session,
    mission_id: int,
    floor_id: int,
    payload: MissionFloorUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> MissionFloor:
    mission = get_mission(db, mission_id)
    state = next(
        (item for item in mission.floor_states if item.floor_id == floor_id),
        None,
    )
    if state is None:
        raise SecurityError(
            "MISSION_FLOOR_NOT_FOUND",
            "Floor در این مأموریت ثبت نشده است.",
            404,
            [],
        )
    values = payload.model_dump()
    changed_fields = {
        field for field, value in values.items() if getattr(state, field) != value
    }
    if not changed_fields:
        return state
    for field, value in values.items():
        setattr(state, field, value)
    upload_fields = {
        "main_upload_started",
        "main_upload_completed",
        "correct_floor_link",
        "operations_notified",
    }
    invalidation_stage = 9 if changed_fields <= upload_fields else 7
    invalidate_from_stage(
        db,
        mission.pilot,
        _mission_invalidation_stage(mission, invalidation_stage),
        actor_user_id=actor_user_id,
        reason=f"Mission Floor {state.floor.code} updated",
    )
    if state.main_capture_started and mission.status in {"scheduled", "assigned", "ready"}:
        mission.status = "in_progress"
    add_audit_log(
        db,
        action="missions.floor_updated",
        entity_type="MissionFloor",
        entity_id=state.id,
        actor_user_id=actor_user_id,
        new_data={
            "floor_id": floor_id,
            "capture_state": state.capture_state,
            "changed_fields": sorted(changed_fields),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(state)
    return state
