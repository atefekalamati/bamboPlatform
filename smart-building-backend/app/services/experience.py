"""External platform status, customer experience, evidence, and incident services."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_app_env
from app.exceptions import SecurityError
from app.models import (
    ExternalEvidenceCheck,
    ExternalPlatformReference,
    FormF04,
    Incident,
    Mission,
    Notification,
    Pilot,
    User,
)
from app.schemas.experience import (
    CUSTOMER_SUCCESS_EVIDENCE_CAPABILITIES,
    EVIDENCE_CAPABILITIES,
    ExternalEvidenceUpdate,
    ExternalPlatformUpdate,
    FormF04Patch,
    IncidentClose,
    IncidentCreate,
    IncidentPatch,
    OutputNotificationCreate,
)
from app.services.security import add_audit_log, mask_mobile, utc_now
from app.services.workflow import invalidate_from_stage

ISSUE_ROUTES = {
    "access": "support",
    "platform": "technical",
    "coverage_quality": "operations",
    "training": "training",
    "capability": "product",
    "continuation": "sales",
}


def get_pilot(db: Session, pilot_id: int, *, lock: bool = False) -> Pilot:
    query = db.query(Pilot).filter(Pilot.id == pilot_id)
    if lock:
        query = query.with_for_update()
    pilot = query.first()
    if not pilot:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    return pilot


def get_incident(db: Session, incident_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise SecurityError("INCIDENT_NOT_FOUND", "رخداد پیدا نشد.", 404, [])
    return incident


def _active_users(db: Session, user_ids: list[int | None]) -> dict[int, User]:
    ids = {user_id for user_id in user_ids if user_id is not None}
    if not ids:
        return {}
    users = (
        db.query(User)
        .filter(
            User.id.in_(ids),
            User.is_active.is_(True),
            User.locked_at.is_(None),
        )
        .all()
    )
    by_id = {user.id: user for user in users}
    if set(by_id) != ids:
        raise SecurityError(
            "USER_NOT_FOUND",
            "یک یا چند کاربر فعال مرجع پیدا نشد.",
            422,
            [{"field": "user_id", "reason": "invalid_active_user"}],
        )
    return by_id


def update_external_platform_reference(
    db: Session,
    pilot_id: int,
    payload: ExternalPlatformUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> ExternalPlatformReference:
    pilot = get_pilot(db, pilot_id)
    if pilot.current_stage < 10:
        raise SecurityError(
            "EXTERNAL_STATUS_STAGE_LOCKED",
            "ثبت وضعیت پلتفرم اصلی پیش از عبور از G3 مجاز نیست.",
            409,
            [],
        )
    reference = pilot.external_platform_reference
    values = payload.model_dump()
    was_existing = reference is not None
    if reference is None:
        reference = ExternalPlatformReference(
            pilot=pilot,
            checked_by_user_id=actor_user_id,
            **values,
        )
        db.add(reference)
        db.flush()
        changed_fields = set(values)
    else:
        changed_fields = {
            field
            for field, value in values.items()
            if getattr(reference, field) != value
        }
        for field, value in values.items():
            setattr(reference, field, value)
        reference.checked_by_user_id = actor_user_id
    if was_existing and changed_fields:
        invalidate_from_stage(
            db,
            pilot,
            10,
            actor_user_id=actor_user_id,
            reason="External platform status updated",
        )
    add_audit_log(
        db,
        action="external_platform.status_saved",
        entity_type="ExternalPlatformReference",
        entity_id=reference.id,
        actor_user_id=actor_user_id,
        new_data={
            "platform_status": reference.platform_status,
            "changed_fields": sorted(changed_fields),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(reference)
    return reference


def patch_f04(
    db: Session,
    pilot_id: int,
    payload: FormF04Patch,
    *,
    actor_user_id: int,
    session_id: int,
) -> FormF04:
    pilot = get_pilot(db, pilot_id, lock=True)
    if pilot.current_stage < 11:
        raise SecurityError(
            "F04_STAGE_LOCKED",
            "ثبت F04 پیش از مرحله اطلاع‌رسانی مجاز نیست.",
            409,
            [],
        )
    values = payload.model_dump(exclude_unset=True)
    for field in ("issue_owner_user_id", "customer_success_user_id"):
        referenced_user_id = values.get(field)
        if referenced_user_id is not None and referenced_user_id != actor_user_id:
            raise SecurityError(
                "F04_ACTOR_REFERENCE_INVALID",
                "مسئول ثبت‌شده در F04 باید همان کاربر انجام‌دهنده عملیات باشد.",
                403,
                [{"field": field, "reason": "must_match_actor"}],
            )
    users = _active_users(
        db,
        [
            values.get("issue_owner_user_id"),
            values.get("customer_success_user_id"),
        ],
    )
    form = pilot.form_f04
    was_existing = form is not None
    if form is None:
        form = FormF04(
            pilot=pilot,
            responsible_user_id=actor_user_id,
        )
        db.add(form)
        db.flush()
    changed_fields = {
        field for field, value in values.items() if getattr(form, field) != value
    }
    for field, value in values.items():
        setattr(form, field, value)
    if (
        form.first_follow_up_at
        and form.second_follow_up_at
        and form.second_follow_up_at < form.first_follow_up_at
    ):
        raise SecurityError(
            "F04_FOLLOW_UP_ORDER_INVALID",
            "پیگیری دوم نمی‌تواند قبل از پیگیری اول باشد.",
            422,
            [{"field": "second_follow_up_at", "reason": "before_first_follow_up"}],
        )
    if form.issue_description and not (
        form.issue_category
        and form.issue_route
        and form.issue_owner_user_id
        and form.issue_due_at
    ):
        raise SecurityError(
            "F04_ISSUE_ROUTING_REQUIRED",
            "برای مشکل ثبت‌شده، مسیر ارجاع، مسئول و موعد الزامی است.",
            422,
            [{"field": "issue_description", "reason": "routing_required"}],
        )
    if form.issue_category and (
        form.issue_route != ISSUE_ROUTES[form.issue_category]
    ):
        raise SecurityError(
            "F04_ISSUE_ROUTE_INVALID",
            "مسیر ارجاع با دسته مشکل ثبت‌شده مطابقت ندارد.",
            422,
            [{"field": "issue_route", "reason": "category_route_mismatch"}],
        )

    training_fields = {
        "training_completed",
        "login_trained",
        "project_trained",
        "floor_trained",
        "plan_trained",
        "tour_trained",
        "navigation_trained",
        "support_trained",
        "independent_use_confirmed",
    }
    experience_fields = {
        "owner_logged_in",
        "project_opened",
        "main_tour_viewed",
        "viewing_result",
        "issue_description",
        "issue_category",
        "issue_route",
        "issue_owner_user_id",
        "issue_due_at",
        "first_follow_up_at",
        "second_follow_up_at",
        "useful",
        "coverage_score",
        "quality_score",
        "most_useful_part",
        "missing_part",
        "other_users",
        "more_training_needed",
        "satisfaction_score",
        "customer_success_user_id",
    }
    if was_existing and changed_fields:
        if changed_fields & training_fields:
            invalidation_stage = 12
        elif changed_fields & experience_fields:
            invalidation_stage = 13
        else:
            invalidation_stage = 16
        invalidate_from_stage(
            db,
            pilot,
            invalidation_stage,
            actor_user_id=actor_user_id,
            reason="F04 updated",
        )
    add_audit_log(
        db,
        action="forms.f04_saved",
        entity_type="Pilot",
        entity_id=pilot.id,
        actor_user_id=actor_user_id,
        new_data={
            "changed_fields": sorted(changed_fields),
            "referenced_user_ids": sorted(users),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(form)
    return form


def upsert_external_evidence(
    db: Session,
    pilot_id: int,
    capability: str,
    payload: ExternalEvidenceUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> ExternalEvidenceCheck:
    if capability not in EVIDENCE_CAPABILITIES:
        raise SecurityError(
            "EVIDENCE_CAPABILITY_INVALID",
            "قابلیت یا گزارش مرجع معتبر نیست.",
            422,
            [{"field": "capability", "reason": "unsupported"}],
        )
    pilot = get_pilot(db, pilot_id, lock=True)
    evidence_stage = (
        13 if capability in CUSTOMER_SUCCESS_EVIDENCE_CAPABILITIES else 15
    )
    if pilot.current_stage < evidence_stage:
        raise SecurityError(
            "EXTERNAL_EVIDENCE_STAGE_LOCKED",
            "ثبت این بررسی پیش از مرحله مرتبط مجاز نیست.",
            409,
            [],
        )
    evidence = (
        db.query(ExternalEvidenceCheck)
        .filter(
            ExternalEvidenceCheck.pilot_id == pilot.id,
            ExternalEvidenceCheck.capability == capability,
        )
        .first()
    )
    values = payload.model_dump()
    if evidence is None:
        evidence = ExternalEvidenceCheck(
            pilot=pilot,
            capability=capability,
            checked_by_user_id=actor_user_id,
            **values,
        )
        db.add(evidence)
        db.flush()
        changed = True
    else:
        changed = any(
            getattr(evidence, field) != value for field, value in values.items()
        )
        for field, value in values.items():
            setattr(evidence, field, value)
        evidence.checked_by_user_id = actor_user_id
    if changed:
        invalidate_from_stage(
            db,
            pilot,
            evidence_stage,
            actor_user_id=actor_user_id,
            reason=f"External evidence {capability} updated",
        )
    add_audit_log(
        db,
        action="external_evidence.saved",
        entity_type="ExternalEvidenceCheck",
        entity_id=evidence.id,
        actor_user_id=actor_user_id,
        new_data={"capability": capability, "status": evidence.status},
        session_id=session_id,
    )
    db.commit()
    db.refresh(evidence)
    return evidence


def create_main_output_notification(
    db: Session,
    pilot_id: int,
    payload: OutputNotificationCreate,
    *,
    actor_user_id: int,
    session_id: int,
) -> Notification:
    pilot = get_pilot(db, pilot_id)
    if pilot.current_stage < 11:
        raise SecurityError(
            "NOTIFICATION_STAGE_LOCKED",
            "اعلان آماده‌شدن خروجی پیش از مرحله ۱۱ مجاز نیست.",
            409,
            [],
        )
    recipient_mobile = payload.recipient_mobile or pilot.project.owner.primary_mobile
    now = utc_now()
    if get_app_env() in {"development", "test"}:
        status = "delivered"
        provider_status = "accepted:console"
        last_error = None
        sent_at = now
    else:
        status = "failed"
        provider_status = "unconfigured"
        last_error = "SMS provider is not configured"
        sent_at = None
    notification = Notification(
        public_id=str(uuid4()),
        pilot=pilot,
        recipient_mobile=recipient_mobile,
        template="main_output_ready",
        payload={"pilot_code": pilot.code},
        status=status,
        provider_status=provider_status,
        attempts=1,
        last_error=last_error,
        alternate_contact_method=payload.alternate_contact_method,
        sent_at=sent_at,
    )
    db.add(notification)
    invalidate_from_stage(
        db,
        pilot,
        11,
        actor_user_id=actor_user_id,
        reason="Main output notification created",
    )
    add_audit_log(
        db,
        action="notifications.main_output_created",
        entity_type="Notification",
        entity_id=notification.public_id,
        actor_user_id=actor_user_id,
        new_data={
            "recipient": mask_mobile(recipient_mobile),
            "status": status,
            "provider_status": provider_status,
            "alternate_contact_registered": bool(payload.alternate_contact_method),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(notification)
    return notification


def _incident_response_due_at(occurred_at, severity: str):
    if severity == "critical":
        return occurred_at + timedelta(minutes=30)
    if severity == "important":
        return occurred_at + timedelta(hours=4)
    return occurred_at.replace(hour=23, minute=59, second=59, microsecond=999999)


def create_incident(
    db: Session,
    pilot_id: int,
    payload: IncidentCreate,
    *,
    actor_user_id: int,
    session_id: int,
) -> Incident:
    pilot = (
        db.query(Pilot)
        .filter(Pilot.id == pilot_id)
        .with_for_update()
        .first()
    )
    if not pilot:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    if payload.stage_number > pilot.current_stage:
        raise SecurityError(
            "INCIDENT_STAGE_INVALID",
            "رخداد را نمی‌توان برای مرحله‌ای ثبت کرد که هنوز آغاز نشده است.",
            422,
            [{"field": "stage_number", "reason": "future_stage"}],
        )
    mission = None
    if payload.mission_id is not None:
        mission = db.get(Mission, payload.mission_id)
        if mission is None or mission.pilot_id != pilot.id:
            raise SecurityError(
                "INCIDENT_MISSION_INVALID",
                "مأموریت متعلق به این پایلوت نیست.",
                422,
                [],
            )
    _active_users(db, [payload.owner_user_id])
    sequence = (
        db.query(func.coalesce(func.max(Incident.sequence), 0))
        .filter(Incident.pilot_id == pilot.id)
        .scalar()
        + 1
    )
    incident = Incident(
        pilot=pilot,
        mission=mission,
        sequence=sequence,
        code=f"INC-{pilot.code}-{sequence:02d}",
        occurred_at=payload.occurred_at,
        reported_by_user_id=actor_user_id,
        stage_number=payload.stage_number,
        severity=payload.severity,
        incident_type=payload.incident_type,
        description=payload.description,
        containment_action=payload.containment_action,
        notified_people=payload.notified_people,
        owner_user_id=payload.owner_user_id,
        response_due_at=_incident_response_due_at(
            payload.occurred_at,
            payload.severity,
        ),
        correction_due_at=payload.correction_due_at,
    )
    db.add(incident)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecurityError(
            "INCIDENT_CREATE_CONFLICT",
            "ثبت هم‌زمان رخداد با تعارض روبه‌رو شد؛ دوباره تلاش کنید.",
            409,
            [],
        ) from exc
    if incident.severity == "critical":
        invalidate_from_stage(
            db,
            pilot,
            13,
            actor_user_id=actor_user_id,
            reason=f"Critical incident {incident.code} opened",
        )
    add_audit_log(
        db,
        action="incidents.created",
        entity_type="Incident",
        entity_id=incident.id,
        actor_user_id=actor_user_id,
        new_data={
            "code": incident.code,
            "severity": incident.severity,
            "type": incident.incident_type,
            "response_due_at": incident.response_due_at.isoformat(),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(incident)
    return incident


def patch_incident(
    db: Session,
    incident_id: int,
    payload: IncidentPatch,
    *,
    actor_user_id: int,
    session_id: int,
) -> Incident:
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .with_for_update()
        .first()
    )
    if not incident:
        raise SecurityError("INCIDENT_NOT_FOUND", "رخداد پیدا نشد.", 404, [])
    if incident.status == "closed":
        raise SecurityError(
            "INCIDENT_ALREADY_CLOSED",
            "رخداد بسته‌شده قابل ویرایش نیست.",
            409,
            [],
        )
    values = payload.model_dump(exclude_unset=True)
    _active_users(db, [values.get("owner_user_id")])
    correction_due_at = values.get("correction_due_at")
    if correction_due_at and correction_due_at < incident.occurred_at:
        raise SecurityError(
            "INCIDENT_CORRECTION_DUE_INVALID",
            "موعد اقدام اصلاحی نمی‌تواند قبل از زمان وقوع رخداد باشد.",
            422,
            [{"field": "correction_due_at", "reason": "before_occurred_at"}],
        )
    changed_fields = {
        field
        for field, value in values.items()
        if getattr(incident, field) != value
    }
    if not changed_fields:
        return incident
    for field, value in values.items():
        setattr(incident, field, value)
    if incident.severity == "critical":
        invalidate_from_stage(
            db,
            incident.pilot,
            13,
            actor_user_id=actor_user_id,
            reason=f"Critical incident {incident.code} updated",
        )
    add_audit_log(
        db,
        action="incidents.updated",
        entity_type="Incident",
        entity_id=incident.id,
        actor_user_id=actor_user_id,
        new_data={
            "status": incident.status,
            "changed_fields": sorted(changed_fields),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(incident)
    return incident


def close_incident(
    db: Session,
    incident_id: int,
    payload: IncidentClose,
    *,
    actor_user_id: int,
    session_id: int,
) -> Incident:
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .with_for_update()
        .first()
    )
    if not incident:
        raise SecurityError("INCIDENT_NOT_FOUND", "رخداد پیدا نشد.", 404, [])
    if incident.status == "closed":
        raise SecurityError(
            "INCIDENT_ALREADY_CLOSED",
            "رخداد قبلاً بسته شده است.",
            409,
            [],
        )
    missing_close_fields = [
        field
        for field, value in (
            ("owner_user_id", incident.owner_user_id),
            ("correction_due_at", incident.correction_due_at),
        )
        if value is None
    ]
    if missing_close_fields:
        raise SecurityError(
            "INCIDENT_CLOSE_INCOMPLETE",
            "برای بستن رخداد، مسئول و موعد اقدام اصلاحی باید ثبت شده باشد.",
            422,
            [
                {"field": field, "reason": "required_before_close"}
                for field in missing_close_fields
            ],
        )
    old_status = incident.status
    incident.root_cause = payload.root_cause
    incident.corrective_action = payload.corrective_action
    incident.result = payload.result
    incident.evidence = payload.evidence
    incident.lessons_learned = payload.lessons_learned
    incident.status = "closed"
    incident.closed_by_user_id = actor_user_id
    incident.closed_at = utc_now()
    if incident.severity == "critical":
        invalidate_from_stage(
            db,
            incident.pilot,
            13,
            actor_user_id=actor_user_id,
            reason=f"Critical incident {incident.code} closed",
        )
    add_audit_log(
        db,
        action="incidents.closed",
        entity_type="Incident",
        entity_id=incident.id,
        actor_user_id=actor_user_id,
        old_data={"status": old_status},
        new_data={"status": "closed", "closed_by_user_id": actor_user_id},
        session_id=session_id,
    )
    db.commit()
    db.refresh(incident)
    return incident
