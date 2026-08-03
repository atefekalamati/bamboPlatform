"""External platform status, customer experience, evidence, and incident services."""

import math
from datetime import timedelta

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
    IncidentList,
    IncidentPatch,
    OutputNotificationCreate,
)
from app.services.notifications import create_notification
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

INCIDENT_TRANSITIONS = {
    "open": {"contained", "resolved"},
    "contained": {"resolved"},
    "resolved": set(),
    "closed": set(),
}

INCIDENT_SORT_COLUMNS = {
    "created_at": Incident.created_at,
    "occurred_at": Incident.occurred_at,
    "response_due_at": Incident.response_due_at,
    "correction_due_at": Incident.correction_due_at,
    "severity": Incident.severity,
    "status": Incident.status,
    "stage_number": Incident.stage_number,
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


def _require_incident_owner(db: Session, user_id: int | None, field: str) -> User | None:
    if user_id is None:
        return None
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active.is_(True),
            User.locked_at.is_(None),
        )
        .first()
    )
    if user is None:
        raise SecurityError(
            "INCIDENT_OWNER_INVALID",
            "مسئول رخداد باید کاربر فعال باشد.",
            422,
            [{"field": field, "reason": "invalid_active_user"}],
        )
    return user


def _notify_incident(
    db: Session,
    *,
    incident: Incident,
    recipient_user: User | None,
    actor_user_id: int,
    event: str,
    title: str,
    body: str,
    priority: str,
    deduplication_key: str,
) -> None:
    if recipient_user is None:
        return
    create_notification(
        db,
        recipient_user=recipient_user,
        actor_user_id=actor_user_id,
        notification_type=event,
        category="INCIDENT",
        priority=priority,
        title=title,
        body=body,
        short_body=f"{incident.code}: {incident.status}",
        entity_type="Incident",
        entity_id=incident.id,
        pilot_id=incident.pilot_id,
        mission_id=incident.mission_id,
        action_url=f"/pilots/{incident.pilot_id}/stages/{incident.stage_number}",
        template_code=event.replace(".", "_"),
        payload={
            "incident_code": incident.code,
            "severity": incident.severity,
            "status": incident.status,
            "response_due_at": incident.response_due_at.isoformat(),
        },
        deduplication_key=deduplication_key,
    )


def _validate_resolved_fields(incident: Incident) -> list[dict]:
    missing = []
    for field in ("corrective_action", "result"):
        if not getattr(incident, field):
            missing.append({"field": field, "reason": "required"})
    if incident.severity in {"important", "critical"} and not incident.root_cause:
        missing.append({"field": "root_cause", "reason": "required_for_severity"})
    return missing


def _apply_incident_status_transition(
    incident: Incident,
    target_status: str,
    *,
    allow_close_override: bool = False,
) -> str | None:
    if target_status == incident.status:
        return None
    if target_status == "closed":
        if incident.status != "resolved" and not allow_close_override:
            raise SecurityError(
                "INVALID_INCIDENT_TRANSITION",
                "رخداد فقط پس از resolved شدن قابل بسته‌شدن است.",
                409,
                [{"field": "status", "reason": f"{incident.status}_to_closed_forbidden"}],
            )
    elif target_status not in INCIDENT_TRANSITIONS[incident.status]:
        raise SecurityError(
            "INVALID_INCIDENT_TRANSITION",
            "تغییر وضعیت رخداد مجاز نیست.",
            409,
            [{"field": "status", "reason": f"{incident.status}_to_{target_status}_forbidden"}],
        )
    if target_status == "contained" and not incident.containment_action:
        raise SecurityError(
            "INCIDENT_CONTAINMENT_REQUIRED",
            "برای مهار رخداد، اقدام مهار اولیه الزامی است.",
            422,
            [{"field": "containment_action", "reason": "required"}],
        )
    if target_status == "resolved":
        missing = _validate_resolved_fields(incident)
        if missing:
            raise SecurityError(
                "INCIDENT_RESOLVE_VALIDATION_FAILED",
                "رخداد قابل حل‌شدن نیست.",
                422,
                missing,
            )
    previous = incident.status
    now = utc_now()
    incident.status = target_status
    if target_status in {"contained", "resolved"} and incident.responded_at is None:
        incident.responded_at = now
    if target_status == "contained":
        incident.contained_at = now
    return previous


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
        "other_issue_description",
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
    notification = create_notification(
        db,
        recipient_user=None,
        recipient_mobile=recipient_mobile,
        actor_user_id=actor_user_id,
        notification_type="pilot.main_output_ready",
        category="PILOT",
        priority="NORMAL",
        title="خروجی پایلوت آماده شد",
        body=f"خروجی پرونده {pilot.code} آماده مشاهده است.",
        short_body=f"خروجی {pilot.code} آماده شد",
        entity_type="Pilot",
        entity_id=pilot.id,
        pilot_id=pilot.id,
        action_url=f"/pilots/{pilot.id}/stages/11",
        template_code="main_output_ready",
        payload={"pilot_code": pilot.code},
        alternate_contact_method=payload.alternate_contact_method,
        deduplication_key=f"pilot.main_output_ready:{pilot.id}:{pilot.current_stage}",
    )
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
            "status": notification.status,
            "provider_status": notification.provider_status,
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


def list_incidents(
    db: Session,
    pilot_id: int,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    incident_type: str | None = None,
    stage_number: int | None = None,
    mission_id: int | None = None,
    owner_user_id: int | None = None,
    reported_by_user_id: int | None = None,
    occurred_from=None,
    occurred_to=None,
    response_overdue: bool | None = None,
    correction_overdue: bool | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> IncidentList:
    get_pilot(db, pilot_id)
    query = db.query(Incident).filter(Incident.pilot_id == pilot_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Incident.code.ilike(pattern),
                Incident.description.ilike(pattern),
                Incident.result.ilike(pattern),
            )
        )
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if incident_type:
        query = query.filter(Incident.incident_type == incident_type)
    if stage_number is not None:
        query = query.filter(Incident.stage_number == stage_number)
    if mission_id is not None:
        query = query.filter(Incident.mission_id == mission_id)
    if owner_user_id is not None:
        query = query.filter(Incident.owner_user_id == owner_user_id)
    if reported_by_user_id is not None:
        query = query.filter(Incident.reported_by_user_id == reported_by_user_id)
    if occurred_from is not None:
        query = query.filter(Incident.occurred_at >= occurred_from)
    if occurred_to is not None:
        query = query.filter(Incident.occurred_at <= occurred_to)

    now = utc_now()
    if response_overdue is True:
        query = query.filter(
            Incident.status != "closed",
            Incident.responded_at.is_(None),
            Incident.response_due_at < now,
        )
    elif response_overdue is False:
        query = query.filter(
            or_(
                Incident.status == "closed",
                Incident.responded_at.is_not(None),
                Incident.response_due_at >= now,
            )
        )
    if correction_overdue is True:
        query = query.filter(
            Incident.status != "closed",
            Incident.correction_due_at.is_not(None),
            Incident.correction_due_at < now,
        )
    elif correction_overdue is False:
        query = query.filter(
            or_(
                Incident.status == "closed",
                Incident.correction_due_at.is_(None),
                Incident.correction_due_at >= now,
            )
        )

    summary_base = db.query(Incident).filter(Incident.pilot_id == pilot_id)
    summary_counts = {
        value: (
            summary_base.filter(Incident.status == value).count()
            if value in {"open", "contained", "resolved", "closed"}
            else 0
        )
        for value in ("open", "contained", "resolved", "closed")
    }
    critical_count = summary_base.filter(Incident.severity == "critical").count()
    overdue_count = summary_base.filter(
        Incident.status != "closed",
        or_(
            and_(Incident.responded_at.is_(None), Incident.response_due_at < now),
            and_(Incident.correction_due_at.is_not(None), Incident.correction_due_at < now),
        ),
    ).count()

    total = query.count()
    sort_column = INCIDENT_SORT_COLUMNS.get(sort_by)
    if sort_column is None:
        raise SecurityError(
            "INCIDENT_SORT_INVALID",
            "مرتب‌سازی رخداد معتبر نیست.",
            422,
            [{"field": "sort_by", "reason": "unsupported"}],
        )
    if sort_order == "desc":
        sort_expression = sort_column.desc()
    elif sort_order == "asc":
        sort_expression = sort_column.asc()
    else:
        raise SecurityError(
            "INCIDENT_SORT_INVALID",
            "جهت مرتب‌سازی رخداد معتبر نیست.",
            422,
            [{"field": "sort_order", "reason": "unsupported"}],
        )
    items = (
        query.order_by(sort_expression, Incident.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return IncidentList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
        summary={
            **summary_counts,
            "critical": critical_count,
            "overdue": overdue_count,
        },
    )


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
                "INCIDENT_MISSION_MISMATCH",
                "مأموریت متعلق به این پایلوت نیست.",
                422,
                [],
            )
    owner = _require_incident_owner(db, payload.owner_user_id, "owner_user_id")
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
        reported_at=utc_now(),
        reported_by_user_id=actor_user_id,
        stage_number=payload.stage_number,
        severity=payload.severity,
        incident_type=payload.incident_type,
        location=payload.location,
        description=payload.description,
        containment_action=payload.containment_action,
        notified_people=payload.notified_people,
        informed_at=payload.informed_at,
        owner_user_id=payload.owner_user_id,
        response_due_at=payload.response_due_at
        or _incident_response_due_at(payload.occurred_at, payload.severity),
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
    recipient = owner or (db.get(User, actor_user_id) if incident.severity == "critical" else None)
    if recipient is not None:
        _notify_incident(
            db,
            incident=incident,
            recipient_user=recipient,
            actor_user_id=actor_user_id,
            event=(
                "incident.critical_created"
                if incident.severity == "critical"
                else "incident.created"
            ),
            priority="CRITICAL" if incident.severity == "critical" else "HIGH",
            title=(
                "رخداد بحرانی جدید"
                if incident.severity == "critical"
                else "رخداد جدید به شما تخصیص داده شد"
            ),
            body=f"رخداد {incident.code} برای پرونده {pilot.code} نیازمند اقدام است.",
            deduplication_key=f"incident.created:{incident.id}:{recipient.id}",
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
    old_values = {field: getattr(incident, field) for field in values}
    old_owner_id = incident.owner_user_id
    _require_incident_owner(db, values.get("owner_user_id"), "owner_user_id")
    for due_field in ("response_due_at", "correction_due_at", "responded_at", "informed_at"):
        due_value = values.get(due_field)
        if due_value and due_value < incident.occurred_at:
            raise SecurityError(
                "INCIDENT_DUE_DATE_INVALID",
                "زمان رخداد و موعدهای ثبت‌شده سازگار نیستند.",
                422,
                [{"field": due_field, "reason": "before_occurred_at"}],
            )
    correction_due_at = values.get("correction_due_at")
    if correction_due_at and correction_due_at < incident.occurred_at:
        raise SecurityError(
            "INCIDENT_CORRECTION_DUE_INVALID",
            "موعد اقدام اصلاحی نمی‌تواند قبل از زمان وقوع رخداد باشد.",
            422,
            [{"field": "correction_due_at", "reason": "before_occurred_at"}],
        )
    target_status = values.pop("status", None)
    changed_fields = set()
    for field, value in values.items():
        if getattr(incident, field) != value:
            setattr(incident, field, value)
            changed_fields.add(field)
    old_status = None
    if target_status is not None:
        old_status = _apply_incident_status_transition(incident, target_status)
        if old_status is not None:
            changed_fields.add("status")
    if not changed_fields:
        return incident
    if incident.severity == "critical":
        invalidate_from_stage(
            db,
            incident.pilot,
            13,
            actor_user_id=actor_user_id,
            reason=f"Critical incident {incident.code} updated",
        )
    new_owner = incident.owner if incident.owner_user_id != old_owner_id else None
    if new_owner is not None:
        _notify_incident(
            db,
            incident=incident,
            recipient_user=new_owner,
            actor_user_id=actor_user_id,
            event="incident.assigned",
            priority="HIGH" if incident.severity != "critical" else "CRITICAL",
            title="رخداد به شما تخصیص داده شد",
            body=f"مسئول پیگیری رخداد {incident.code} شدید.",
            deduplication_key=f"incident.assigned:{incident.id}:{new_owner.id}:{incident.updated_at}",
        )
    if old_status is not None and incident.owner is not None:
        _notify_incident(
            db,
            incident=incident,
            recipient_user=incident.owner,
            actor_user_id=actor_user_id,
            event=f"incident.{incident.status}",
            priority="HIGH" if incident.severity != "critical" else "CRITICAL",
            title=f"وضعیت رخداد {incident.status} شد",
            body=f"وضعیت رخداد {incident.code} به {incident.status} تغییر کرد.",
            deduplication_key=f"incident.status:{incident.id}:{incident.status}",
        )
    add_audit_log(
        db,
        action=f"incidents.{incident.status}" if old_status else "incidents.updated",
        entity_type="Incident",
        entity_id=incident.id,
        actor_user_id=actor_user_id,
        old_data={field: old_values.get(field) for field in changed_fields if field in old_values}
        | ({"status": old_status} if old_status else {}),
        new_data={
            "status": incident.status,
            "changed_fields": sorted(changed_fields),
            "owner_user_id": incident.owner_user_id,
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
    actor_permissions: set[str] | None = None,
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
    actor_permissions = actor_permissions or set()
    if incident.severity == "critical" and "incidents.approve_closure" not in actor_permissions:
        raise SecurityError(
            "CRITICAL_INCIDENT_CLOSURE_FORBIDDEN",
            "بستن رخداد بحرانی نیازمند تأیید مجاز است.",
            403,
            [{"permission": "incidents.approve_closure"}],
        )
    allow_close_override = "incidents.approve_closure" in actor_permissions
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
    incident.root_cause = payload.root_cause
    incident.corrective_action = payload.corrective_action
    incident.preventive_action = payload.preventive_action
    incident.result = payload.result
    incident.evidence = payload.evidence
    incident.lessons_learned = payload.lessons_learned
    incident.closure_note = payload.closure_note
    missing_validation = _validate_resolved_fields(incident)
    if missing_validation and not allow_close_override:
        raise SecurityError(
            "INCIDENT_CLOSE_VALIDATION_FAILED",
            "رخداد قابل بسته‌شدن نیست.",
            422,
            missing_validation,
        )
    old_status = _apply_incident_status_transition(
        incident,
        "closed",
        allow_close_override=allow_close_override,
    )
    incident.closed_by_user_id = actor_user_id
    incident.closed_at = utc_now()
    if "incidents.approve_closure" in actor_permissions:
        incident.closure_approved_by_user_id = actor_user_id
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
        old_data={"status": old_status or incident.status},
        new_data={"status": "closed", "closed_by_user_id": actor_user_id},
        session_id=session_id,
    )
    if incident.owner is not None:
        _notify_incident(
            db,
            incident=incident,
            recipient_user=incident.owner,
            actor_user_id=actor_user_id,
            event="incident.closed",
            priority="HIGH" if incident.severity != "critical" else "CRITICAL",
            title="رخداد بسته شد",
            body=f"رخداد {incident.code} بسته شد.",
            deduplication_key=f"incident.closed:{incident.id}",
        )
    db.commit()
    db.refresh(incident)
    return incident
