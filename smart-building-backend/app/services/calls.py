"""Provider-neutral call policy, lifecycle, scope, audit, and webhook handling."""

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import os
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import SecurityError, WorkflowError
from app.models import Call, CallAttempt, CallOutcome, CallWebhookEvent, Pilot, PilotStage
from app.providers.calls import get_call_provider
from app.schemas.calls import CallCreate, CallOutcomeUpdate, CallOverride, MockWebhookPayload
from app.schemas.security import normalize_mobile
from app.services.access import require_pilot_access
from app.services.security import AuthContext, add_audit_log


TECHNICAL_STATUSES = {
    "pending", "initiating", "ringing", "answered", "completed", "no_answer",
    "busy", "invalid_number", "failed", "cancelled", "retry_required",
}
SUCCESSFUL_OUTCOMES = {"customer_confirmed", "customer_rejected", "follow_up_completed"}


@dataclass(frozen=True)
class StageCallPolicy:
    enabled: bool = False
    required: bool = False
    purpose: str = "customer_contact"
    summary_required: bool = True
    next_action_outcomes: tuple[str, ...] = ("callback_requested", "revision_requested", "contract_follow_up")
    minimum_successful_calls: int = 0
    max_retry_count: int = 3
    manager_override_allowed: bool = True
    recording_allowed: bool = False
    recording_consent_required: bool = True
    allowed_roles: tuple[str, ...] = ()


STAGE_CALL_POLICIES = {
    2: StageCallPolicy(True, False, "initial_coordination", allowed_roles=("sales", "support")),
    5: StageCallPolicy(True, False, "mission_scheduling", allowed_roles=("operations",)),
    11: StageCallPolicy(True, False, "delivery_fallback", allowed_roles=("support",)),
    13: StageCallPolicy(True, False, "customer_success_follow_up", allowed_roles=("customer_success", "support")),
    16: StageCallPolicy(True, False, "decision_confirmation", allowed_roles=("customer_success", "sales")),
    18: StageCallPolicy(True, True, "commercial_follow_up", minimum_successful_calls=1,
                        recording_allowed=True, allowed_roles=("sales", "pilot_manager")),
}


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def mask_phone(phone: str) -> str:
    return f"{phone[:4]}***{phone[-4:]}"


def stage_call_policy(stage_number: int) -> StageCallPolicy:
    return STAGE_CALL_POLICIES.get(stage_number, StageCallPolicy())


def map_provider_status(provider: str, status: str) -> str:
    """Map only documented internal/mock values; Astel mapping awaits its contract."""
    normalized = status.strip().lower()
    if provider == "mock" and normalized in TECHNICAL_STATUSES:
        return normalized
    if provider == "astel":
        raise ValueError("Official Astel status mapping is not configured")
    return "failed"


def _call_for_context(db: Session, context: AuthContext, public_id: str) -> Call:
    call = db.query(Call).filter(Call.public_id == public_id).first()
    if call is None:
        raise SecurityError("CALL_NOT_FOUND", "تماس پیدا نشد.", 404, [])
    require_pilot_access(db, context, call.pilot_id)
    return call


def _create_attempt(db: Session, call: Call) -> CallAttempt:
    policy = stage_call_policy(call.stage_number)
    attempt_number = len(call.attempts) + 1
    if attempt_number > policy.max_retry_count:
        raise WorkflowError("CALL_RETRY_LIMIT", "حداکثر تعداد تلاش تماس انجام شده است.", call.stage_number, 409, [])
    provider = get_call_provider()
    attempt = CallAttempt(call=call, attempt_number=attempt_number, provider=provider.name, status="initiating")
    db.add(attempt)
    result = provider.initiate(
        destination=call.destination_phone,
        callback_url=os.getenv("ASTEL_CALLBACK_URL") or None,
        recording=bool(
            call.recording_consent
            and policy.recording_allowed
            and os.getenv("ASTEL_RECORDING_ENABLED", "false").lower() == "true"
        ),
    )
    attempt.provider_call_id = result.provider_call_id
    attempt.status = result.status if result.status in TECHNICAL_STATUSES else "failed"
    attempt.failure_code = result.failure_code
    attempt.failure_reason = result.failure_reason
    call.provider = result.provider
    call.technical_status = attempt.status
    if not result.accepted:
        call.technical_status = "failed"
    return attempt


def initiate_call(db: Session, context: AuthContext, pilot_id: int, stage_number: int, payload: CallCreate) -> Call:
    pilot = require_pilot_access(db, context, pilot_id)
    policy = stage_call_policy(stage_number)
    if not policy.enabled:
        raise WorkflowError("CALL_NOT_ENABLED", "تماس برای این مرحله فعال نیست.", stage_number, 409, [])
    role_names = {role.name for role in context.user.roles if role.is_active}
    if "super_admin" not in role_names and not role_names.intersection(policy.allowed_roles):
        raise SecurityError("CALL_ROLE_DENIED", "نقش کاربر مجاز به تماس در این مرحله نیست.", 403, [])
    stage = db.query(PilotStage).filter(PilotStage.pilot_id == pilot_id, PilotStage.number == stage_number).first()
    if stage is None:
        raise WorkflowError("STAGE_NOT_FOUND", "مرحله پیدا نشد.", stage_number, 404, [])
    if stage_number > pilot.current_stage or stage.status == "locked":
        raise WorkflowError("CALL_STAGE_INVALID", "مرحله در وضعیت مجاز تماس نیست.", stage_number, 409, [])
    existing = db.query(Call).filter(Call.idempotency_key == payload.idempotency_key).first()
    if existing:
        if existing.pilot_id != pilot_id or existing.stage_number != stage_number:
            raise WorkflowError("CALL_IDEMPOTENCY_CONFLICT", "کلید تکرار برای درخواست دیگری استفاده شده است.", stage_number, 409, [])
        return existing
    try:
        phone = normalize_mobile(pilot.project.owner.primary_mobile)
    except ValueError as exc:
        raise WorkflowError("CALL_PHONE_INVALID", "شماره تماس مالک معتبر نیست.", stage_number, 422, [{"field": "owner.primary_mobile", "reason": "invalid_phone"}]) from exc
    if payload.recording_consent and not policy.recording_allowed:
        raise WorkflowError("CALL_RECORDING_NOT_ALLOWED", "ضبط تماس برای این مرحله فعال نیست.", stage_number, 422, [])
    call = Call(
        public_id=str(uuid4()), pilot_id=pilot_id, stage_id=stage.id, stage_number=stage_number,
        owner_id=pilot.project.owner_id, initiated_by_user_id=context.user.id,
        provider=os.getenv("CALL_PROVIDER", "mock").lower(), destination_phone=phone,
        destination_masked=mask_phone(phone), purpose=payload.purpose or policy.purpose,
        recording_consent=payload.recording_consent, idempotency_key=payload.idempotency_key,
    )
    db.add(call)
    _create_attempt(db, call)
    add_audit_log(db, action="calls.initiated", entity_type="Call", entity_id=call.public_id,
                  actor_user_id=context.user.id, pilot_id=pilot_id,
                  new_data={"stage_number": stage_number, "destination": call.destination_masked, "provider": call.provider})
    db.commit()
    db.refresh(call)
    if call.technical_status == "failed":
        raise WorkflowError(
            "CALL_PROVIDER_UNAVAILABLE",
            "سرویس تماس در دسترس نیست.",
            stage_number,
            503,
            [{"field": "call_id", "reason": "provider_failed", "value": call.public_id}],
        )
    return call


def list_stage_calls(db: Session, context: AuthContext, pilot_id: int, stage_number: int) -> list[Call]:
    require_pilot_access(db, context, pilot_id)
    return db.query(Call).filter(Call.pilot_id == pilot_id, Call.stage_number == stage_number).order_by(Call.created_at.desc()).all()


def get_call(db: Session, context: AuthContext, public_id: str) -> Call:
    return _call_for_context(db, context, public_id)


def record_outcome(db: Session, context: AuthContext, public_id: str, payload: CallOutcomeUpdate) -> Call:
    call = _call_for_context(db, context, public_id)
    if call.technical_status not in {"answered", "completed", "no_answer", "busy", "failed"}:
        raise WorkflowError("CALL_OUTCOME_NOT_ALLOWED", "ابتدا وضعیت فنی تماس باید مشخص شود.", call.stage_number, 409, [])
    outcome = CallOutcome(call=call, outcome=payload.outcome, summary=payload.summary,
                          next_action=payload.next_action, callback_at=payload.callback_at,
                          recorded_by_user_id=context.user.id)
    call.business_outcome = payload.outcome
    call.summary = payload.summary
    call.next_action = payload.next_action
    call.callback_at = payload.callback_at
    db.add(outcome)
    add_audit_log(db, action="calls.outcome_recorded", entity_type="Call", entity_id=call.public_id,
                  actor_user_id=context.user.id, pilot_id=call.pilot_id,
                  new_data={"outcome": payload.outcome, "callback_at": payload.callback_at.isoformat() if payload.callback_at else None})
    db.commit(); db.refresh(call)
    return call


def retry_call(db: Session, context: AuthContext, public_id: str) -> Call:
    call = _call_for_context(db, context, public_id)
    if call.technical_status not in {"no_answer", "busy", "failed", "retry_required"}:
        raise WorkflowError("CALL_RETRY_NOT_ALLOWED", "تلاش مجدد برای این وضعیت مجاز نیست.", call.stage_number, 409, [])
    _create_attempt(db, call)
    add_audit_log(db, action="calls.retried", entity_type="Call", entity_id=call.public_id,
                  actor_user_id=context.user.id, pilot_id=call.pilot_id,
                  new_data={"attempt_number": len(call.attempts)})
    db.commit(); db.refresh(call)
    return call


def override_call_requirement(db: Session, context: AuthContext, public_id: str, payload: CallOverride) -> Call:
    call = _call_for_context(db, context, public_id)
    if not stage_call_policy(call.stage_number).manager_override_allowed:
        raise WorkflowError("CALL_OVERRIDE_NOT_ALLOWED", "Override برای این مرحله مجاز نیست.", call.stage_number, 409, [])
    call.override_reason = payload.reason.strip()
    call.overridden_by_user_id = context.user.id
    call.overridden_at = utc_now()
    add_audit_log(db, action="calls.requirement_overridden", entity_type="Call", entity_id=call.public_id,
                  actor_user_id=context.user.id, pilot_id=call.pilot_id, reason=call.override_reason)
    db.commit(); db.refresh(call)
    return call


def stage_call_requirement_met(db: Session, pilot_id: int, stage_number: int) -> bool:
    policy = stage_call_policy(stage_number)
    if not policy.required:
        return True
    calls = db.query(Call).filter(Call.pilot_id == pilot_id, Call.stage_number == stage_number).all()
    if any(call.overridden_at is not None and call.override_reason for call in calls):
        return True
    successful = [call for call in calls if call.technical_status in {"answered", "completed"}
                  and call.business_outcome in SUCCESSFUL_OUTCOMES and bool(call.summary and call.summary.strip())]
    return len(successful) >= policy.minimum_successful_calls


def process_mock_webhook(db: Session, raw_body: bytes, signature: str | None, payload: MockWebhookPayload) -> tuple[Call, bool]:
    if os.getenv("CALL_PROVIDER", "mock").lower() != "mock" or os.getenv("APP_ENV", "development").lower() == "production":
        raise SecurityError("CALL_WEBHOOK_NOT_CONFIGURED", "قرارداد رسمی Webhook Astel تنظیم نشده است.", 503, [])
    secret = os.getenv("MOCK_CALL_WEBHOOK_SECRET", "test-call-webhook-secret")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected):
        raise SecurityError("CALL_WEBHOOK_INVALID", "امضای Webhook معتبر نیست.", 401, [])
    existing = db.query(CallWebhookEvent).filter(CallWebhookEvent.provider == "mock", CallWebhookEvent.event_id == payload.event_id).first()
    if existing:
        call = db.query(Call).join(CallAttempt).filter(CallAttempt.provider_call_id == payload.provider_call_id).first()
        if call is None:
            raise SecurityError("CALL_NOT_FOUND", "تماس پیدا نشد.", 404, [])
        return call, True
    attempt = db.query(CallAttempt).filter(CallAttempt.provider_call_id == payload.provider_call_id).first()
    if attempt is None:
        raise SecurityError("CALL_NOT_FOUND", "تماس پیدا نشد.", 404, [])
    event = CallWebhookEvent(provider="mock", event_id=payload.event_id, provider_call_id=payload.provider_call_id,
                             event_type=payload.event_type, payload_sanitized={"status": payload.status}, processed=True,
                             processed_at=utc_now())
    db.add(event)
    call = attempt.call
    order = {"initiating": 1, "ringing": 2, "answered": 3, "completed": 4,
             "no_answer": 4, "busy": 4, "failed": 4, "cancelled": 4}
    if order.get(payload.status, 0) >= order.get(attempt.status, 0):
        mapped_status = map_provider_status("mock", payload.status)
        attempt.status = mapped_status; call.technical_status = mapped_status
        occurred = payload.occurred_at.replace(tzinfo=None) if payload.occurred_at and payload.occurred_at.tzinfo else payload.occurred_at or utc_now()
        if payload.status == "ringing": attempt.started_at = attempt.started_at or occurred; call.started_at = call.started_at or occurred
        if payload.status == "answered": attempt.answered_at = occurred; call.answered_at = occurred
        if payload.status in {"completed", "no_answer", "busy", "failed", "cancelled"}:
            attempt.ended_at = occurred; call.ended_at = occurred
        if payload.duration_seconds is not None:
            attempt.duration_seconds = payload.duration_seconds; call.duration_seconds = payload.duration_seconds
        if payload.recording_reference and call.recording_consent:
            call.recording_reference = payload.recording_reference
    add_audit_log(db, action="calls.webhook_processed", entity_type="Call", entity_id=call.public_id,
                  pilot_id=call.pilot_id, new_data={"event_id": payload.event_id, "status": payload.status})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return call, True
    db.refresh(call)
    return call, False
