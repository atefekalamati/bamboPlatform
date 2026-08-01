"""Commercial proposal, customer follow-up, and final outcome rules."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_app_env
from app.exceptions import SecurityError
from app.models import (
    CommercialProposal,
    CustomerFollowUp,
    FinalOutcome,
    Notification,
    Pilot,
    User,
)
from app.schemas.commercial import (
    CommercialProposalUpdate,
    CustomerFollowUpUpdate,
    FinalOutcomeUpdate,
    FollowUpSlot,
)
from app.services.security import add_audit_log, mask_mobile, utc_now
from app.services.workflow import invalidate_from_stage

FOLLOW_UP_SLOT_ORDER = ("day_0", "day_2", "day_5", "day_7_10")


def get_pilot(db: Session, pilot_id: int, *, lock: bool = False) -> Pilot:
    query = db.query(Pilot).filter(Pilot.id == pilot_id)
    if lock:
        query = query.with_for_update()
    pilot = query.first()
    if pilot is None:
        raise SecurityError(
            "PILOT_NOT_FOUND",
            "پرونده پایلوت پیدا نشد.",
            404,
            [],
        )
    return pilot


def _active_user(db: Session, user_id: int, field: str) -> User:
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
            "USER_NOT_FOUND",
            "کاربر فعال مرجع پیدا نشد.",
            422,
            [{"field": field, "reason": "invalid_active_user"}],
        )
    return user


def _dispatch_follow_up_notification(
    db: Session,
    *,
    pilot: Pilot,
    recipient: User,
    follow_up_at,
) -> Notification:
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
        recipient_user_id=recipient.id,
        recipient_mobile=recipient.mobile,
        template="commercial_follow_up_due",
        payload={
            "pilot_code": pilot.code,
            "follow_up_at": follow_up_at.isoformat(),
        },
        status=status,
        provider_status=provider_status,
        attempts=1,
        last_error=last_error,
        sent_at=sent_at,
    )
    db.add(notification)
    return notification


def update_commercial_proposal(
    db: Session,
    pilot_id: int,
    payload: CommercialProposalUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> CommercialProposal:
    pilot = get_pilot(db, pilot_id, lock=True)
    if pilot.current_stage < 17:
        raise SecurityError(
            "COMMERCIAL_PROPOSAL_STAGE_LOCKED",
            "ثبت پیشنهاد تجاری پیش از مرحله ۱۷ مجاز نیست.",
            409,
            [],
        )
    responsible = _active_user(db, actor_user_id, "responsible_user_id")
    values = payload.model_dump()
    file_fields = {
        "proposal_file_name",
        "proposal_file_size",
        "proposal_file_sha256",
    }
    if not any(values[field] is not None for field in file_fields):
        # Omitting an optional PDF must preserve already-registered metadata.
        # This also accepts the frontend's empty string/zero no-file sentinel.
        for field in file_fields:
            values.pop(field)
    proposal = pilot.commercial_proposal
    if proposal is None:
        proposal = CommercialProposal(
            pilot=pilot,
            responsible_user_id=actor_user_id,
            **values,
        )
        db.add(proposal)
        db.flush()
        changed_fields = set(values)
    else:
        changed_fields = {
            field
            for field, value in values.items()
            if getattr(proposal, field) != value
        }
        for field, value in values.items():
            setattr(proposal, field, value)
        proposal.responsible_user_id = actor_user_id

    if changed_fields:
        invalidate_from_stage(
            db,
            pilot,
            17,
            actor_user_id=actor_user_id,
            reason="Commercial proposal updated",
        )
        form_f04 = pilot.form_f04
        if form_f04 is not None:
            form_f04.project_count = proposal.project_count
            form_f04.user_count = proposal.user_count
            form_f04.usage_frequency = proposal.frequency
            form_f04.decision_maker = proposal.decision_maker
            form_f04.proposal_ready = True
            form_f04.sales_user_id = actor_user_id
            form_f04.next_action = (
                f"Commercial follow-up at {proposal.follow_up_at.isoformat()}"
            )
        notification = _dispatch_follow_up_notification(
            db,
            pilot=pilot,
            recipient=responsible,
            follow_up_at=proposal.follow_up_at,
        )
        db.flush()
        notification_data = {
            "public_id": notification.public_id,
            "recipient": mask_mobile(responsible.mobile),
            "status": notification.status,
        }
    else:
        notification_data = None

    add_audit_log(
        db,
        action="commercial.proposal_saved",
        entity_type="CommercialProposal",
        entity_id=proposal.id,
        actor_user_id=actor_user_id,
        new_data={
            "changed_fields": sorted(changed_fields),
            "proposal_file_name": proposal.proposal_file_name,
            "proposal_file_size": proposal.proposal_file_size,
            "notification": notification_data,
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(proposal)
    return proposal


def _validate_follow_up_schedule(
    proposal: CommercialProposal,
    slot: FollowUpSlot,
    due_at,
) -> None:
    baseline = proposal.follow_up_at.date()
    due_date = due_at.date()
    if slot == "day_0":
        valid = due_date == baseline
    elif slot == "day_2":
        valid = due_date == baseline + timedelta(days=2)
    elif slot == "day_5":
        valid = due_date == baseline + timedelta(days=5)
    else:
        valid = baseline + timedelta(days=7) <= due_date <= baseline + timedelta(days=10)
    if not valid:
        raise SecurityError(
            "FOLLOW_UP_SCHEDULE_INVALID",
            "موعد پیگیری با بازه تعیین‌شده در پیشنهاد تجاری هماهنگ نیست.",
            422,
            [{"field": "due_at", "reason": f"outside_{slot}_window"}],
        )


def update_customer_follow_up(
    db: Session,
    pilot_id: int,
    schedule_slot: FollowUpSlot,
    payload: CustomerFollowUpUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> CustomerFollowUp:
    pilot = get_pilot(db, pilot_id, lock=True)
    if pilot.current_stage < 18:
        raise SecurityError(
            "CUSTOMER_FOLLOW_UP_STAGE_LOCKED",
            "ثبت پیگیری مشتری پیش از مرحله ۱۸ مجاز نیست.",
            409,
            [],
        )
    proposal = pilot.commercial_proposal
    if proposal is None:
        raise SecurityError(
            "COMMERCIAL_PROPOSAL_REQUIRED",
            "پیشنهاد تجاری باید پیش از پیگیری ثبت شود.",
            409,
            [{"field": "commercial_proposal", "reason": "required"}],
        )
    _active_user(db, payload.owner_user_id, "owner_user_id")
    _validate_follow_up_schedule(proposal, schedule_slot, payload.due_at)
    values = payload.model_dump()
    follow_up = (
        db.query(CustomerFollowUp)
        .filter(
            CustomerFollowUp.pilot_id == pilot.id,
            CustomerFollowUp.schedule_slot == schedule_slot,
        )
        .first()
    )
    if follow_up is None:
        follow_up = CustomerFollowUp(
            pilot=pilot,
            schedule_slot=schedule_slot,
            **values,
        )
        db.add(follow_up)
        db.flush()
        changed_fields = set(values)
    else:
        changed_fields = {
            field
            for field, value in values.items()
            if getattr(follow_up, field) != value
        }
        for field, value in values.items():
            setattr(follow_up, field, value)
    if changed_fields:
        invalidate_from_stage(
            db,
            pilot,
            18,
            actor_user_id=actor_user_id,
            reason=f"Customer follow-up {schedule_slot} updated",
        )
    add_audit_log(
        db,
        action="commercial.follow_up_saved",
        entity_type="CustomerFollowUp",
        entity_id=follow_up.id,
        actor_user_id=actor_user_id,
        new_data={
            "schedule_slot": schedule_slot,
            "changed_fields": sorted(changed_fields),
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(follow_up)
    return follow_up


def update_final_outcome(
    db: Session,
    pilot_id: int,
    payload: FinalOutcomeUpdate,
    *,
    actor_user_id: int,
    session_id: int,
) -> FinalOutcome:
    pilot = get_pilot(db, pilot_id, lock=True)
    if pilot.current_stage < 19:
        raise SecurityError(
            "FINAL_OUTCOME_STAGE_LOCKED",
            "ثبت نتیجه نهایی پیش از مرحله ۱۹ مجاز نیست.",
            409,
            [],
        )
    _active_user(db, actor_user_id, "responsible_user_id")
    if payload.success_owner_user_id is not None:
        _active_user(db, payload.success_owner_user_id, "success_owner_user_id")
    values = payload.model_dump()
    outcome = pilot.final_outcome
    if outcome is None:
        outcome = FinalOutcome(
            pilot=pilot,
            responsible_user_id=actor_user_id,
            **values,
        )
        db.add(outcome)
        db.flush()
        changed_fields = set(values)
    else:
        changed_fields = {
            field
            for field, value in values.items()
            if getattr(outcome, field) != value
        }
        for field, value in values.items():
            setattr(outcome, field, value)
        outcome.responsible_user_id = actor_user_id
        if changed_fields:
            outcome.pilot_manager_approved = False
            outcome.approved_by_user_id = None
            outcome.approved_at = None
    if changed_fields:
        invalidate_from_stage(
            db,
            pilot,
            19,
            actor_user_id=actor_user_id,
            reason="Final commercial outcome updated",
        )
        form_f04 = pilot.form_f04
        if form_f04 is not None:
            form_f04.final_result = outcome.outcome
            form_f04.final_reason = outcome.reason
            form_f04.sales_user_id = actor_user_id
            form_f04.customer_success_user_id = outcome.success_owner_user_id
    add_audit_log(
        db,
        action="commercial.final_outcome_saved",
        entity_type="FinalOutcome",
        entity_id=outcome.id,
        actor_user_id=actor_user_id,
        new_data={
            "outcome": outcome.outcome,
            "changed_fields": sorted(changed_fields),
            "pilot_manager_approved": outcome.pilot_manager_approved,
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(outcome)
    return outcome


def approve_final_outcome(
    db: Session,
    pilot_id: int,
    *,
    actor_user_id: int,
    session_id: int,
) -> FinalOutcome:
    pilot = get_pilot(db, pilot_id, lock=True)
    if pilot.current_stage != 19:
        raise SecurityError(
            "FINAL_OUTCOME_STAGE_LOCKED",
            "تأیید نتیجه نهایی فقط در مرحله ۱۹ مجاز است.",
            409,
            [],
        )
    actor = _active_user(db, actor_user_id, "approved_by_user_id")
    role_names = {role.name for role in actor.roles if role.is_active}
    if not role_names.intersection({"pilot_manager", "super_admin"}):
        raise SecurityError(
            "FINAL_OUTCOME_APPROVER_INVALID",
            "تأیید نتیجه نهایی فقط توسط مدیر پایلوت مجاز است.",
            403,
            [],
        )
    outcome = pilot.final_outcome
    if outcome is None:
        raise SecurityError(
            "FINAL_OUTCOME_REQUIRED",
            "نتیجه نهایی باید پیش از تأیید ثبت شود.",
            409,
            [{"field": "outcome", "reason": "required"}],
        )
    changed = not outcome.pilot_manager_approved
    if changed:
        outcome.pilot_manager_approved = True
        outcome.approved_by_user_id = actor_user_id
        outcome.approved_at = utc_now()
        invalidate_from_stage(
            db,
            pilot,
            19,
            actor_user_id=actor_user_id,
            reason="Final outcome manager approval updated",
        )
        if pilot.form_f04 is not None:
            pilot.form_f04.pilot_manager_user_id = actor_user_id
    add_audit_log(
        db,
        action="commercial.final_outcome_approved",
        entity_type="FinalOutcome",
        entity_id=outcome.id,
        actor_user_id=actor_user_id,
        new_data={
            "approved": True,
            "changed": changed,
        },
        session_id=session_id,
    )
    db.commit()
    db.refresh(outcome)
    return outcome
