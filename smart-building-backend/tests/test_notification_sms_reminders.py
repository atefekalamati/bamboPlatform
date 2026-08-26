"""Reminder-SMS policy for in-app notifications.

Regression guard for the defaults bug: signing in created an empty
``user_preferences`` row, and the service read a missing ``sms_enabled`` key as
``False``. Every non-CRITICAL reminder stopped once a user logged in.
"""

import pytest

from conftest import BOOTSTRAP_MOBILE, login_with_otp

from app.database import get_session
from app.models import NotificationDelivery, User, UserPreference
from app.providers.sms import SmsSendResult
from app.schemas.notifications import (
    DEFAULT_CRITICAL_SMS_ENABLED,
    DEFAULT_SMS_CATEGORIES,
    DEFAULT_SMS_ENABLED,
    NotificationPreferences,
)
import app.services.notifications as notifications
from app.services.notifications import build_in_app_action_required_sms, create_notification


class SpyProvider:
    """Records provider calls; never touches the network."""

    provider = "spy"

    def __init__(self, accepted: bool = True):
        self.accepted = accepted
        self.calls: list[dict] = []

    def send_otp(self, *, mobile, otp_code, template_id=None):
        self.calls.append({"kind": "otp", "mobile": mobile, "otp_code": otp_code})
        return SmsSendResult(True, self.provider, "accepted:spy", "spy-otp")

    def send_notification(self, *, mobile, template_code, body):
        self.calls.append(
            {"kind": "notification", "mobile": mobile, "template_code": template_code, "body": body}
        )
        if not self.accepted:
            return SmsSendResult(
                False,
                self.provider,
                "rejected:spy",
                failure_code="SMS_REJECTED",
                failure_reason="spy rejected the message",
            )
        return SmsSendResult(True, self.provider, "accepted:spy", "spy-notification")

    def get_delivery_status(self, *, provider_message_id):
        return SmsSendResult(True, self.provider, "delivered:spy", provider_message_id)


@pytest.fixture
def spy(monkeypatch):
    provider = SpyProvider()
    monkeypatch.setattr(notifications, "get_sms_provider", lambda: provider)
    return provider


def _make_user(db, mobile, *, preferences=None, has_preference_row=False, is_active=True):
    user = User(mobile=mobile, display_name=f"کاربر {mobile[-4:]}", is_active=is_active)
    db.add(user)
    db.flush()
    if has_preference_row or preferences is not None:
        db.add(UserPreference(user=user, notification_preferences=preferences or {}))
        db.flush()
    db.commit()
    return user


def _notify(db, user, *, category="STAGE", priority="HIGH", notification_type="stage.review_required"):
    notification = create_notification(
        db,
        recipient_user=user,
        notification_type=notification_type,
        category=category,
        priority=priority,
        title="عنوان اعلان",
        body="متن اعلان",
        template_code=notification_type,
    )
    db.commit()
    return notification


def _sms_delivery(db, notification):
    return (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.notification_id == notification.id,
            NotificationDelivery.channel == "SMS",
        )
        .one_or_none()
    )


# --------------------------------------------------------------- default policy


def test_schema_and_service_share_one_default_policy():
    """The two defaults that disagreed are now the same object."""
    assert notifications.DEFAULT_SMS_CATEGORIES is DEFAULT_SMS_CATEGORIES
    assert NotificationPreferences().sms_enabled is DEFAULT_SMS_ENABLED is True
    assert NotificationPreferences().critical_sms_enabled is DEFAULT_CRITICAL_SMS_ENABLED
    assert NotificationPreferences().sms_categories == DEFAULT_SMS_CATEGORIES


def test_operational_categories_remind_and_auth_system_stay_opt_in():
    assert DEFAULT_SMS_CATEGORIES == {
        "AUTH": False,
        "PILOT": True,
        "STAGE": True,
        "MISSION": True,
        "INCIDENT": True,
        "SLA": True,
        "COMMERCIAL": True,
        "SYSTEM": False,
    }


# ------------------------------------------------------------------ Tests 1 & 2


def test_user_without_preference_row_gets_reminder(client, spy):
    with get_session() as db:
        user = _make_user(db, "+989120000001")
        notification = _notify(db, user)
        assert _sms_delivery(db, notification).status == "DELIVERED"
    assert [call["kind"] for call in spy.calls] == ["notification"]


def test_empty_preference_row_after_login_still_reminds(client, spy):
    """Test 2 — the exact regression: /auth/bootstrap stores ``{}``."""
    with get_session() as db:
        user = _make_user(db, "+989120000002", has_preference_row=True)
        assert user.preferences.notification_preferences == {}
        notification = _notify(db, user)
        delivery = _sms_delivery(db, notification)
        assert delivery.status == "DELIVERED"
        assert delivery.failure_code is None
    assert len(spy.calls) == 1


def test_login_bootstrap_does_not_disable_reminders(client, spy):
    """Test 16 — end-to-end through the real login + bootstrap endpoints."""
    headers = login_with_otp(client, BOOTSTRAP_MOBILE)
    assert client.get("/auth/bootstrap", headers=headers).status_code == 200

    with get_session() as db:
        user = db.query(User).filter(User.mobile == "+989150000000").one()
        assert user.preferences is not None, "bootstrap should have created the row"
        notification = _notify(db, user)
        assert _sms_delivery(db, notification).status == "DELIVERED"


# ---------------------------------------------------------------- Tests 3 to 10


@pytest.mark.parametrize(
    "notification_type",
    ["stage.review_required", "stage.revision_required", "stage.action_required"],
)
def test_every_stage_event_reminds(client, spy, notification_type):
    with get_session() as db:
        user = _make_user(db, f"+98912000{abs(hash(notification_type)) % 10000:04d}", has_preference_row=True)
        notification = _notify(db, user, category="STAGE", notification_type=notification_type)
        assert _sms_delivery(db, notification).status == "DELIVERED"
    assert len(spy.calls) == 1


@pytest.mark.parametrize(
    ("category", "priority", "expected"),
    [
        ("MISSION", "HIGH", "DELIVERED"),
        ("INCIDENT", "HIGH", "DELIVERED"),
        ("INCIDENT", "CRITICAL", "DELIVERED"),
        ("PILOT", "NORMAL", "DELIVERED"),
        ("COMMERCIAL", "NORMAL", "DELIVERED"),
        ("SLA", "HIGH", "DELIVERED"),
        ("SYSTEM", "NORMAL", "SKIPPED"),
        ("AUTH", "NORMAL", "SKIPPED"),
    ],
)
def test_category_reminder_matrix_after_login(client, spy, category, priority, expected):
    with get_session() as db:
        user = _make_user(db, f"+9891230{abs(hash(category + priority)) % 100000:05d}", has_preference_row=True)
        notification = _notify(db, user, category=category, priority=priority)
        delivery = _sms_delivery(db, notification)
        assert delivery.status == expected, delivery.failure_code
        if expected == "SKIPPED":
            assert delivery.failure_code == "SMS_PREFERENCE_DISABLED"


# ------------------------------------------------------- Tests 11 & 12: opt-out


def test_explicit_sms_disabled_is_respected(client, spy):
    """Test 11 — fixing the default must not override a stored choice."""
    with get_session() as db:
        user = _make_user(db, "+989120000011", preferences={"sms_enabled": False})
        notification = _notify(db, user)
        delivery = _sms_delivery(db, notification)
        assert delivery.status == "SKIPPED"
        assert delivery.failure_code == "SMS_PREFERENCE_DISABLED"
    assert spy.calls == []


def test_explicitly_disabled_category_is_respected(client, spy):
    """Test 12 — and other categories keep their defaults."""
    with get_session() as db:
        user = _make_user(
            db,
            "+989120000012",
            preferences={"sms_enabled": True, "sms_categories": {"STAGE": False}},
        )
        stage_notification = _notify(db, user, category="STAGE")
        assert _sms_delivery(db, stage_notification).status == "SKIPPED"
        assert spy.calls == []

        mission_notification = _notify(db, user, category="MISSION")
        assert _sms_delivery(db, mission_notification).status == "DELIVERED"


def test_critical_still_overrides_a_disabled_switch(client, spy):
    """Documented carve-out: critical_sms_enabled is its own switch."""
    with get_session() as db:
        user = _make_user(db, "+989120000013", preferences={"sms_enabled": False})
        notification = _notify(db, user, category="INCIDENT", priority="CRITICAL")
        assert _sms_delivery(db, notification).status == "DELIVERED"

        muted = _make_user(
            db,
            "+989120000014",
            preferences={"sms_enabled": False, "critical_sms_enabled": False},
        )
        muted_notification = _notify(db, muted, category="INCIDENT", priority="CRITICAL")
        assert _sms_delivery(db, muted_notification).status == "SKIPPED"


# ------------------------------------------------- Tests 13, 14, 15: edge cases


def test_inactive_user_keeps_notification_but_gets_no_sms(client, spy):
    with get_session() as db:
        user = _make_user(db, "+989120000015", has_preference_row=True, is_active=False)
        notification = _notify(db, user)
        delivery = _sms_delivery(db, notification)
        assert delivery.status == "SKIPPED"
        assert delivery.failure_code == "USER_INACTIVE"
        assert notification.id is not None
    assert spy.calls == []


def test_provider_failure_keeps_notification_and_records_failure(client, monkeypatch):
    provider = SpyProvider(accepted=False)
    monkeypatch.setattr(notifications, "get_sms_provider", lambda: provider)
    with get_session() as db:
        user = _make_user(db, "+989120000016", has_preference_row=True)
        notification = _notify(db, user)
        delivery = _sms_delivery(db, notification)
        assert delivery.status == "FAILED"
        assert delivery.failure_code == "SMS_REJECTED"
        assert notification.status == "failed"
        # The in-app record survives a provider failure.
        assert notification.deleted_at is None


def test_duplicate_dispatch_sends_at_most_one_sms(client, spy):
    """Test 15 — deduplication_key collapses a repeated dispatch."""
    with get_session() as db:
        user = _make_user(db, "+989120000017", has_preference_row=True)
        first = create_notification(
            db,
            recipient_user=user,
            notification_type="stage.review_required",
            category="STAGE",
            priority="HIGH",
            title="t",
            body="b",
            template_code="stage.review_required",
            deduplication_key="stage.review:1:1",
        )
        db.commit()
        second = create_notification(
            db,
            recipient_user=user,
            notification_type="stage.review_required",
            category="STAGE",
            priority="HIGH",
            title="t",
            body="b",
            template_code="stage.review_required",
            deduplication_key="stage.review:1:1",
        )
        db.commit()

        assert second.id == first.id
        sms_rows = (
            db.query(NotificationDelivery)
            .filter(
                NotificationDelivery.notification_id == first.id,
                NotificationDelivery.channel == "SMS",
            )
            .count()
        )
        assert sms_rows == 1
    assert len(spy.calls) == 1


# ------------------------------------------------------------ safety of content


def test_reminder_body_is_generic_and_leaks_no_pilot_detail(client, spy):
    with get_session() as db:
        user = _make_user(db, "+989120000018", has_preference_row=True)
        create_notification(
            db,
            recipient_user=user,
            notification_type="stage.review_required",
            category="STAGE",
            priority="HIGH",
            title="تأیید مرحله ۳ پرونده PIL-1405-001",
            body="پرونده PIL-1405-001 مالک شرکت نمونه نیازمند تصمیم است.",
            template_code="stage.review_required",
        )
        db.commit()

    body = spy.calls[0]["body"]
    assert body == build_in_app_action_required_sms()
    for secret in ("PIL-1405-001", "شرکت نمونه", "مالک"):
        assert secret not in body


def test_reminder_goes_only_to_the_recipient(client, spy):
    with get_session() as db:
        actor = _make_user(db, "+989120000019", has_preference_row=True)
        recipient = _make_user(db, "+989120000020", has_preference_row=True)
        create_notification(
            db,
            recipient_user=recipient,
            actor_user_id=actor.id,
            notification_type="stage.review_required",
            category="STAGE",
            priority="HIGH",
            title="t",
            body="b",
            template_code="stage.review_required",
        )
        db.commit()

    assert len(spy.calls) == 1
    assert spy.calls[0]["mobile"] == "+989120000020"


# --------------------------------------------------------------- OTP regression


def test_otp_flow_is_untouched_by_the_reminder_change(client):
    """Test 14 — OTP has its own provider call path and its own template."""
    request = client.post("/auth/otp/request", json={"mobile": "09121230001"})
    assert request.status_code == 200
    body = request.json()
    assert body["debug_code"]
    assert body["destination_mask"].count("*") == 3

    verify = client.post(
        "/auth/otp/verify",
        json={"request_id": body["request_id"], "code": body["debug_code"]},
    )
    assert verify.status_code == 200
    assert verify.json()["access_token"]
