"""In-app and SMS notification orchestration."""

from __future__ import annotations

import math
import os
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_app_env, get_bool_setting
from app.exceptions import SecurityError
from app.models import Notification, NotificationDelivery, User, UserPreference
from app.providers.sms import get_sms_provider
from app.schemas.security import normalize_mobile
from app.schemas.notifications import (
    DEFAULT_CRITICAL_SMS_ENABLED,
    DEFAULT_IN_APP_ENABLED,
    DEFAULT_SMS_CATEGORIES as SCHEMA_DEFAULT_SMS_CATEGORIES,
    DEFAULT_SMS_ENABLED,
    NotificationPreferences,
)
from app.services.security import mask_mobile, utc_now

IN_APP_ACTION_REQUIRED_SMS_BASE = (
    "یادآوری بامبو:\n"
    "لطفاً اعلان جدید سامانه را بررسی کرده و اقدام الزامی خود را انجام دهید."
)
PLATFORM_CONTRACT_REVIEW_TEMPLATE = "platform_contract_review_reminder"
PLATFORM_CONTRACT_REVIEW_TITLE = "یادآوری بررسی قرارداد پلتفرم"
PLATFORM_CONTRACT_REVIEW_SMS_BASE = IN_APP_ACTION_REQUIRED_SMS_BASE

# Re-exported so existing importers keep working; the policy itself lives with
# the schema so preference defaults have exactly one definition.
DEFAULT_SMS_CATEGORIES = SCHEMA_DEFAULT_SMS_CATEGORIES


def get_platform_login_url() -> str | None:
    value = os.getenv("PLATFORM_LOGIN_URL", "").strip()
    return value or None


def build_in_app_action_required_sms() -> str:
    login_url = get_platform_login_url()
    return f"{IN_APP_ACTION_REQUIRED_SMS_BASE}\n{login_url}" if login_url else IN_APP_ACTION_REQUIRED_SMS_BASE


def build_platform_contract_review_sms() -> str:
    return build_in_app_action_required_sms()


def _merge_sms_categories(stored: object) -> dict[str, bool]:
    """Explicit per-category choices win; unset categories keep their default.

    Rows written before the defaults were shared can hold ``{}``, which must not
    be read as "every category is off".
    """
    merged = dict(DEFAULT_SMS_CATEGORIES)
    if isinstance(stored, dict):
        merged.update(
            {key: bool(value) for key, value in stored.items() if key in merged}
        )
    return merged


def _preferences_dict(user: User | None) -> dict:
    if user is None or user.preferences is None:
        return NotificationPreferences().model_dump()
    raw = user.preferences.notification_preferences or {}
    # A missing key means the user never made a choice, so fall back to the
    # shared defaults. Only an explicitly stored value overrides them.
    return NotificationPreferences(
        in_app_enabled=raw.get("in_app_enabled", DEFAULT_IN_APP_ENABLED),
        sms_enabled=raw.get("sms_enabled", DEFAULT_SMS_ENABLED),
        sms_categories=_merge_sms_categories(raw.get("sms_categories")),
        critical_sms_enabled=raw.get("critical_sms_enabled", DEFAULT_CRITICAL_SMS_ENABLED),
        quiet_hours_start=raw.get("quiet_hours_start"),
        quiet_hours_end=raw.get("quiet_hours_end"),
    ).model_dump()


def get_preferences(user: User) -> NotificationPreferences:
    return NotificationPreferences(**_preferences_dict(user))


def update_preferences(db: Session, user: User, payload: NotificationPreferences) -> UserPreference:
    preference = user.preferences
    if preference is None:
        preference = UserPreference(user=user)
        db.add(preference)
        db.flush()
    preference.notification_preferences = payload.model_dump()
    return preference


def sms_allowed(user: User | None, *, category: str, priority: str) -> bool:
    if user is None:
        return True
    prefs = _preferences_dict(user)
    if priority == "CRITICAL":
        return bool(prefs["critical_sms_enabled"])
    if not prefs["sms_enabled"]:
        return False
    return bool(prefs["sms_categories"].get(category, False))


def create_notification(
    db: Session,
    *,
    recipient_user: User | None,
    recipient_mobile: str | None = None,
    actor_user_id: int | None = None,
    notification_type: str,
    category: str,
    priority: str = "NORMAL",
    title: str,
    body: str,
    short_body: str | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    pilot_id: int | None = None,
    mission_id: int | None = None,
    action_url: str | None = None,
    template_code: str,
    payload: dict | None = None,
    deduplication_key: str | None = None,
    alternate_contact_method: str | None = None,
    send_sms: bool = True,
) -> Notification:
    if deduplication_key and recipient_user is not None:
        existing = (
            db.query(Notification)
            .filter(
                Notification.recipient_user_id == recipient_user.id,
                Notification.deduplication_key == deduplication_key,
                Notification.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            return existing

    mobile = recipient_mobile or (recipient_user.mobile if recipient_user is not None else None)
    notification = Notification(
        public_id=str(uuid4()),
        mission_id=mission_id,
        pilot_id=pilot_id,
        recipient_user_id=recipient_user.id if recipient_user else None,
        actor_user_id=actor_user_id,
        recipient_mobile=mobile or "",
        channel="IN_APP,SMS" if mobile and send_sms else "IN_APP",
        notification_type=notification_type,
        category=category,
        priority=priority,
        title=title,
        body=body,
        short_body=short_body,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        action_url=action_url,
        template=template_code,
        payload=payload or {},
        status="pending",
        provider_status="in_app_created",
        alternate_contact_method=alternate_contact_method,
        deduplication_key=deduplication_key,
    )
    db.add(notification)
    db.flush()

    if recipient_user is not None and _preferences_dict(recipient_user)["in_app_enabled"]:
        now = utc_now()
        db.add(
            NotificationDelivery(
                notification=notification,
                channel="IN_APP",
                recipient_address=str(recipient_user.id),
                provider="bambo",
                template_code=template_code,
                status="DELIVERED",
                attempt_count=1,
                sent_at=now,
                delivered_at=now,
            )
        )

    _create_sms_delivery(
        db,
        notification=notification,
        recipient_user=recipient_user,
        mobile=mobile,
        category=category,
        priority=priority,
        template_code=template_code,
        body=build_in_app_action_required_sms() if recipient_user is not None else short_body or body,
        send_sms=send_sms,
    )
    return notification


def _create_sms_delivery(
    db: Session,
    *,
    notification: Notification,
    recipient_user: User | None,
    mobile: str | None,
    category: str,
    priority: str,
    template_code: str,
    body: str,
    send_sms: bool,
) -> None:
    now = utc_now()
    result = None
    failure_code = None
    failure_reason = None
    normalized_mobile = None
    if not send_sms:
        status = "SKIPPED"
        failure_code = "SMS_DISABLED_FOR_EVENT"
        failure_reason = "SMS delivery was not requested for this event"
    elif recipient_user is not None and not recipient_user.is_active:
        # Keep the in-app record for history; a disabled account gets no SMS.
        status = "SKIPPED"
        failure_code = "USER_INACTIVE"
        failure_reason = "Recipient account is disabled"
    elif not mobile:
        status = "SKIPPED"
        failure_code = "SMS_RECIPIENT_MISSING"
        failure_reason = "Recipient mobile is missing"
    elif not sms_allowed(recipient_user, category=category, priority=priority):
        status = "SKIPPED"
        failure_code = "SMS_PREFERENCE_DISABLED"
        failure_reason = "SMS is disabled by notification preferences"
    elif not get_bool_setting("SMS_ENABLED", True):
        status = "SKIPPED"
        failure_code = "SMS_PROVIDER_DISABLED"
        failure_reason = "SMS provider is disabled"
    else:
        try:
            normalized_mobile = normalize_mobile(mobile)
        except ValueError:
            status = "FAILED"
            failure_code = "SMS_RECIPIENT_INVALID"
            failure_reason = "Recipient mobile is invalid"
        if normalized_mobile:
            result = get_sms_provider().send_notification(
                mobile=normalized_mobile,
                template_code=template_code,
                body=body,
            )
            status = "DELIVERED" if result.accepted else "FAILED"
            failure_code = result.failure_code
            failure_reason = result.failure_reason

    provider = result.provider if result else "bambo"
    provider_status = result.provider_status if result else status.lower()
    delivery = NotificationDelivery(
        notification=notification,
        channel="SMS",
        recipient_address=mobile or "",
        provider=provider,
        template_code=template_code,
        status=status,
        provider_message_id=result.provider_message_id if result else None,
        attempt_count=1 if result else 0,
        next_retry_at=now + timedelta(minutes=5) if result and result.retryable else None,
        sent_at=now if result and result.accepted else None,
        delivered_at=now if result and result.accepted else None,
        failed_at=now if status == "FAILED" else None,
        failure_code=failure_code,
        failure_reason=failure_reason,
    )
    db.add(delivery)

    notification.status = "delivered" if status in {"DELIVERED", "SKIPPED"} else "failed"
    notification.provider_status = provider_status
    notification.attempts = delivery.attempt_count
    notification.last_error = failure_reason
    notification.sent_at = delivery.sent_at


def list_user_notifications(
    db: Session,
    *,
    user: User,
    page: int,
    page_size: int,
    status: str | None,
    category: str | None,
    priority: str | None,
    date_from,
    date_to,
) -> tuple[list[Notification], int, int]:
    query = db.query(Notification).filter(
        Notification.recipient_user_id == user.id,
        Notification.deleted_at.is_(None),
    )
    if status == "read":
        query = query.filter(Notification.is_read.is_(True))
    elif status == "unread":
        query = query.filter(Notification.is_read.is_(False))
    if category:
        query = query.filter(Notification.category == category)
    if priority:
        query = query.filter(Notification.priority == priority)
    if date_from:
        query = query.filter(Notification.created_at >= date_from)
    if date_to:
        query = query.filter(Notification.created_at <= date_to)

    total = query.count()
    items = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total, unread_notifications_count(db, user)


def unread_notifications_count(db: Session, user: User) -> int:
    return (
        db.query(func.count(Notification.id))
        .filter(
            Notification.recipient_user_id == user.id,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )


def get_user_notification(db: Session, user: User, notification_id: str) -> Notification:
    notification = (
        db.query(Notification)
        .filter(
            Notification.public_id == notification_id,
            Notification.recipient_user_id == user.id,
            Notification.deleted_at.is_(None),
        )
        .first()
    )
    if notification is None:
        raise SecurityError("NOTIFICATION_NOT_FOUND", "اعلان پیدا نشد.", 404, [])
    return notification


def mark_read(notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = utc_now()
    return notification


def mark_all_read(db: Session, user: User) -> int:
    notifications = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == user.id,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
        .all()
    )
    for notification in notifications:
        mark_read(notification)
    return len(notifications)


def soft_delete(notification: Notification) -> None:
    notification.deleted_at = utc_now()


def total_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size))


def delivery_logs(db: Session) -> list[NotificationDelivery]:
    return (
        db.query(NotificationDelivery)
        .join(Notification)
        .order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id.desc())
        .limit(200)
        .all()
    )


def masked_address(delivery: NotificationDelivery) -> str:
    if delivery.channel == "SMS" and delivery.recipient_address:
        return mask_mobile(delivery.recipient_address)
    return delivery.recipient_address
