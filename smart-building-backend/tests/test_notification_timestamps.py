"""Notification timestamps must reach the client as absolute instants.

Regression guard: the columns are ``timestamp without time zone`` and
``utc_now()`` strips tzinfo, so a bare ``datetime`` response field serialized as
``2026-08-31T16:26:07``. ``new Date()`` reads an offset-less string as local
time, so in Tehran a notification created seconds ago rendered as 3.5 hours old.
"""

import json
import re
from datetime import UTC, datetime, timedelta

import pytest

from conftest import BOOTSTRAP_MOBILE, login_with_otp

from app.database import get_session
from app.models import Notification, NotificationDelivery, User
from app.schemas.datetimes import ensure_utc
from app.services.notifications import create_notification

# Matches a trailing "Z" or a numeric offset such as "+00:00".
OFFSET = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def is_aware(value: str) -> bool:
    return bool(OFFSET.search(value))


@pytest.fixture
def actor(client):
    headers = login_with_otp(client, BOOTSTRAP_MOBILE)
    with get_session() as db:
        user_id = db.query(User).filter(User.mobile == "+989150000000").one().id
    return headers, user_id


def make_notification(user_id, *, notification_type="test.event", category="STAGE", created_at=None):
    with get_session() as db:
        user = db.get(User, user_id)
        notification = create_notification(
            db,
            recipient_user=user,
            notification_type=notification_type,
            category=category,
            priority="HIGH",
            title="عنوان",
            body="متن",
            template_code=notification_type,
            send_sms=False,
        )
        db.flush()
        if created_at is not None:
            notification.created_at = created_at
        db.commit()
        return notification.public_id, notification.id


# ------------------------------------------------------------------ the helper


def test_ensure_utc_stamps_naive_without_moving_the_clock():
    naive = datetime(2026, 8, 31, 16, 26, 7)
    stamped = ensure_utc(naive)
    assert stamped.tzinfo is not None
    assert stamped.utcoffset() == timedelta(0)
    # Same wall clock, now labelled.
    assert stamped.replace(tzinfo=None) == naive


def test_ensure_utc_converts_an_aware_value():
    tehran = datetime(2026, 8, 31, 20, 0, tzinfo=timezone_of(3, 30))
    converted = ensure_utc(tehran)
    assert converted.utcoffset() == timedelta(0)
    assert converted == tehran  # same instant, different representation


def timezone_of(hours, minutes):
    from datetime import timezone

    return timezone(timedelta(hours=hours, minutes=minutes))


def test_ensure_utc_passes_none_through():
    assert ensure_utc(None) is None


# ------------------------------------------------------------------- endpoints


def test_list_returns_aware_created_at(client, actor):
    headers, user_id = actor
    make_notification(user_id)

    response = client.get("/notifications", headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    for item in items:
        assert is_aware(item["created_at"]), item["created_at"]


def test_detail_returns_aware_created_at(client, actor):
    headers, user_id = actor
    public_id, _ = make_notification(user_id)

    response = client.get(f"/notifications/{public_id}", headers=headers)
    assert response.status_code == 200
    assert is_aware(response.json()["created_at"])


def test_mark_as_read_returns_aware_created_at(client, actor):
    headers, user_id = actor
    public_id, _ = make_notification(user_id)

    response = client.patch(f"/notifications/{public_id}/read", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_read"] is True
    assert is_aware(body["created_at"])


def test_read_all_leaves_later_reads_aware(client, actor):
    headers, user_id = actor
    make_notification(user_id)

    assert client.post("/notifications/read-all", headers=headers).status_code == 204
    items = client.get("/notifications", headers=headers).json()["items"]
    assert all(is_aware(item["created_at"]) for item in items)


def test_delivery_logs_return_aware_timestamps(client, actor):
    headers, user_id = actor
    _, notification_id = make_notification(user_id)

    # create_notification writes one delivery per channel; stamp them all so the
    # assertion does not depend on which row the endpoint returns first.
    now = datetime.now(UTC).replace(tzinfo=None)
    with get_session() as db:
        deliveries = (
            db.query(NotificationDelivery)
            .filter(NotificationDelivery.notification_id == notification_id)
            .all()
        )
        assert deliveries
        for delivery in deliveries:
            delivery.sent_at = now
            delivery.delivered_at = now
            delivery.failed_at = now
        db.commit()

    response = client.get("/notifications/delivery-logs", headers=headers)
    assert response.status_code == 200
    rows = [r for r in response.json() if r["notification_id"] == notification_id]
    assert rows
    for row in rows:
        for field in ("created_at", "sent_at", "delivered_at", "failed_at"):
            assert row[field] is not None, f"{row['channel']}.{field} is null"
            assert is_aware(row[field]), f"{row['channel']}.{field} = {row[field]}"


# -------------------------------------------------------------- no clock shift


def test_a_fresh_notification_is_not_hours_old(client, actor):
    """The bug's symptom: a notification created now reading 3.5 hours old."""
    headers, user_id = actor
    before = datetime.now(UTC)
    public_id, _ = make_notification(user_id)

    body = client.get(f"/notifications/{public_id}", headers=headers).json()
    reported = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    drift = abs((datetime.now(UTC) - reported).total_seconds())

    assert reported >= before - timedelta(seconds=5)
    assert drift < 60, f"created_at is {drift:.0f}s away from now"


def test_legacy_naive_row_keeps_its_clock_reading(client, actor):
    """An old row must be labelled UTC, never converted to Tehran time."""
    headers, user_id = actor
    stored = datetime(2026, 8, 31, 9, 15, 0)
    public_id, _ = make_notification(user_id, created_at=stored)

    body = client.get(f"/notifications/{public_id}", headers=headers).json()
    reported = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))

    assert reported.utcoffset() == timedelta(0)
    assert reported.replace(tzinfo=None) == stored, "the instant was shifted"


def test_raw_json_carries_an_offset_on_every_notification_timestamp(client, actor):
    headers, user_id = actor
    make_notification(user_id)

    raw = client.get("/notifications", headers=headers).text
    payload = json.loads(raw)
    for item in payload["items"]:
        value = item["created_at"]
        assert value.endswith("Z") or "+00:00" in value, value


# ------------------------------------------------------------- filters intact


def test_date_filters_still_select_the_right_rows(client, actor):
    headers, user_id = actor
    old_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=10)
    make_notification(user_id, notification_type="test.old", created_at=old_at)
    make_notification(user_id, notification_type="test.new")

    cutoff = (datetime.now(UTC) - timedelta(days=1)).replace(tzinfo=None).isoformat()

    recent = client.get(f"/notifications?date_from={cutoff}", headers=headers).json()
    types = {item["type"] for item in recent["items"]}
    assert "test.new" in types
    assert "test.old" not in types

    older = client.get(f"/notifications?date_to={cutoff}", headers=headers).json()
    types = {item["type"] for item in older["items"]}
    assert "test.old" in types
    assert "test.new" not in types


def test_contract_shape_is_unchanged(client, actor):
    """Field names, pagination and list envelope must not move."""
    headers, user_id = actor
    make_notification(user_id)

    body = client.get("/notifications", headers=headers).json()
    assert set(body) == {"items", "total", "page", "page_size", "total_pages", "unread_count"}
    assert set(body["items"][0]) == {
        "id", "type", "category", "priority", "title", "body", "short_body",
        "entity_type", "entity_id", "pilot_id", "action_url", "payload",
        "is_read", "created_at",
    }
