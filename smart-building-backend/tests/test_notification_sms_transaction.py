"""A notification SMS must not leave before the caller's transaction commits.

``create_notification`` used to call the provider inline. A caller that rolled
back afterwards had already texted the recipient about a notification that never
reached the database. Sends are now queued on the session and dispatched from
``after_commit``.
"""

import pytest

from app.database import get_session
from app.models import Notification, NotificationDelivery, User
from app.providers.sms import SmsSendResult
import app.services.notifications as notifications
from app.services.notifications import create_notification


class SpyProvider:
    provider = "spy"

    def __init__(self, accepted: bool = True, raises: bool = False):
        self.accepted = accepted
        self.raises = raises
        self.sends: list[dict] = []

    def send_otp(self, *, mobile, otp_code, template_id=None):
        return SmsSendResult(True, self.provider, "accepted:spy", "spy-otp")

    def send_notification(self, *, mobile, template_code, body):
        self.sends.append({"mobile": mobile, "template_code": template_code})
        if self.raises:
            raise RuntimeError("provider exploded")
        if not self.accepted:
            return SmsSendResult(
                False, self.provider, "rejected:spy",
                failure_code="SMS_REJECTED", failure_reason="rejected by spy",
            )
        return SmsSendResult(True, self.provider, "accepted:spy", "spy-msg")

    def get_delivery_status(self, *, provider_message_id):
        return SmsSendResult(True, self.provider, "delivered:spy", provider_message_id)


@pytest.fixture
def spy(monkeypatch):
    provider = SpyProvider()
    monkeypatch.setattr(notifications, "get_sms_provider", lambda: provider)
    return provider


def _recipient(db):
    user = User(mobile="+989127770099", display_name="گیرنده")
    db.add(user)
    db.flush()
    return user


def _notify(db, user, notification_type="tx.probe"):
    return create_notification(
        db,
        recipient_user=user,
        notification_type=notification_type,
        category="STAGE",
        priority="HIGH",
        title="عنوان",
        body="متن",
        template_code=notification_type,
    )


def _sms_row(db, notification_id):
    return (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.notification_id == notification_id,
            NotificationDelivery.channel == "SMS",
        )
        .one()
    )


# ------------------------------------------------------------------ scenario A


def test_commit_success_sends_the_sms(client, spy):
    with get_session() as db:
        user = _recipient(db)
        notification = _notify(db, user)
        assert spy.sends == [], "nothing may be sent before the commit"
        db.commit()

        assert len(spy.sends) == 1
        delivery = _sms_row(db, notification.id)
        assert delivery.status == "DELIVERED"
        assert delivery.sent_at is not None
        assert delivery.provider_message_id == "spy-msg"


# ------------------------------------------------------------------ scenario B


def test_rollback_sends_nothing(client, spy):
    """The defect this guards: an SMS for a notification that does not exist."""
    with get_session() as db:
        user = _recipient(db)
        db.commit()

        _notify(db, user)
        assert spy.sends == []
        db.rollback()

        assert spy.sends == [], "a rolled-back notification must not text anyone"
        assert db.query(Notification).count() == 0


def test_rollback_clears_the_queue_so_a_later_commit_does_not_send_it(client, spy):
    with get_session() as db:
        user = _recipient(db)
        db.commit()

        _notify(db, user)
        db.rollback()

        # An unrelated commit on the same session must not flush the dropped job.
        db.add(User(mobile="+989127770098", display_name="دیگری"))
        db.commit()
        assert spy.sends == []


# ------------------------------------------------------------------ scenario C


def test_provider_failure_after_commit_keeps_the_business_data(client, monkeypatch):
    provider = SpyProvider(accepted=False)
    monkeypatch.setattr(notifications, "get_sms_provider", lambda: provider)
    with get_session() as db:
        user = _recipient(db)
        notification = _notify(db, user)
        db.commit()

        assert db.get(Notification, notification.id) is not None
        delivery = _sms_row(db, notification.id)
        assert delivery.status == "FAILED"
        assert delivery.failure_code == "SMS_REJECTED"
        assert delivery.failed_at is not None


def test_a_raising_provider_does_not_break_the_committed_action(client, monkeypatch):
    provider = SpyProvider(raises=True)
    monkeypatch.setattr(notifications, "get_sms_provider", lambda: provider)
    with get_session() as db:
        user = _recipient(db)
        notification = _notify(db, user)
        db.commit()  # must not raise

        assert db.get(Notification, notification.id) is not None
        delivery = _sms_row(db, notification.id)
        assert delivery.status == "FAILED"
        assert delivery.failure_code == "SMS_DISPATCH_ERROR"


# -------------------------------------------------------------- no duplicates


def test_one_commit_sends_one_sms(client, spy):
    with get_session() as db:
        user = _recipient(db)
        notification = _notify(db, user)
        db.commit()
        db.commit()  # a second commit must not re-dispatch
        assert len(spy.sends) == 1

        rows = (
            db.query(NotificationDelivery)
            .filter(
                NotificationDelivery.notification_id == notification.id,
                NotificationDelivery.channel == "SMS",
            )
            .count()
        )
        assert rows == 1


def test_deduplicated_notification_sends_once(client, spy):
    with get_session() as db:
        user = _recipient(db)
        first = create_notification(
            db, recipient_user=user, notification_type="tx.dedup", category="STAGE",
            priority="HIGH", title="ع", body="م", template_code="tx.dedup",
            deduplication_key="tx.dedup:1",
        )
        db.commit()
        second = create_notification(
            db, recipient_user=user, notification_type="tx.dedup", category="STAGE",
            priority="HIGH", title="ع", body="م", template_code="tx.dedup",
            deduplication_key="tx.dedup:1",
        )
        db.commit()

        assert second.id == first.id
        assert len(spy.sends) == 1


# ---------------------------------------------------------------- skip paths


def test_a_skipped_send_never_reaches_the_dispatcher(client, spy):
    """Preference and policy skips stay terminal, decided inside the transaction."""
    with get_session() as db:
        user = _recipient(db)
        notification = create_notification(
            db, recipient_user=user, notification_type="tx.skip", category="SYSTEM",
            priority="NORMAL", title="ع", body="م", template_code="tx.skip",
        )
        db.commit()

        delivery = _sms_row(db, notification.id)
        assert delivery.status == "SKIPPED"
        assert delivery.failure_code == "SMS_PREFERENCE_DISABLED"
        assert spy.sends == []


def test_otp_is_untouched_by_the_post_commit_path(client):
    """OTP has its own provider call and must stay synchronous."""
    response = client.post("/auth/otp/request", json={"mobile": "09127770097"})
    assert response.status_code == 200
    assert response.json()["debug_code"]
