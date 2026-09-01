"""Notification API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.datetimes import UtcDatetime

NotificationCategory = Literal[
    "AUTH",
    "PILOT",
    "STAGE",
    "MISSION",
    "INCIDENT",
    "SLA",
    "COMMERCIAL",
    "SYSTEM",
]
NotificationPriority = Literal["LOW", "NORMAL", "HIGH", "CRITICAL"]
DeliveryStatus = Literal[
    "PENDING",
    "QUEUED",
    "SENDING",
    "SENT",
    "DELIVERED",
    "FAILED",
    "CANCELLED",
    "SKIPPED",
]


class NotificationItem(BaseModel):
    id: str
    type: str
    category: NotificationCategory
    priority: NotificationPriority
    title: str
    body: str
    short_body: str | None
    entity_type: str | None
    entity_id: str | None
    pilot_id: int | None
    action_url: str | None
    payload: dict
    is_read: bool
    created_at: UtcDatetime


class NotificationList(BaseModel):
    items: list[NotificationItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    unread_count: int


class UnreadCount(BaseModel):
    unread_count: int


# Single source of truth for notification-preference defaults. The service layer
# reads the same constants when a stored preference omits a key, so an empty
# ``notification_preferences`` blob means "user has not chosen yet" rather than
# "everything is off".
DEFAULT_IN_APP_ENABLED = True
DEFAULT_SMS_ENABLED = True
DEFAULT_CRITICAL_SMS_ENABLED = True

# Operational pilot categories remind by SMS; AUTH belongs to the OTP flow and
# SYSTEM is broadcast noise, so both stay opt-in.
DEFAULT_SMS_CATEGORIES: dict[str, bool] = {
    "AUTH": False,
    "PILOT": True,
    "STAGE": True,
    "MISSION": True,
    "INCIDENT": True,
    "SLA": True,
    "COMMERCIAL": True,
    "SYSTEM": False,
}


class NotificationPreferences(BaseModel):
    in_app_enabled: bool = DEFAULT_IN_APP_ENABLED
    sms_enabled: bool = DEFAULT_SMS_ENABLED
    sms_categories: dict[str, bool] = Field(default_factory=lambda: dict(DEFAULT_SMS_CATEGORIES))
    critical_sms_enabled: bool = DEFAULT_CRITICAL_SMS_ENABLED
    quiet_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")

    @field_validator("sms_categories")
    @classmethod
    def validate_sms_categories(cls, value: dict[str, bool]) -> dict[str, bool]:
        allowed = {"AUTH", "PILOT", "STAGE", "MISSION", "INCIDENT", "SLA", "COMMERCIAL", "SYSTEM"}
        invalid = set(value) - allowed
        if invalid:
            raise ValueError("sms_categories contains unsupported categories")
        return value


class NotificationDeliveryRead(BaseModel):
    id: int
    notification_id: int
    notification_public_id: str
    channel: Literal["IN_APP", "SMS"]
    recipient_address: str
    provider: str
    template_code: str
    status: DeliveryStatus
    provider_message_id: str | None
    attempt_count: int
    sent_at: UtcDatetime | None
    delivered_at: UtcDatetime | None
    failed_at: UtcDatetime | None
    failure_code: str | None
    failure_reason: str | None
    created_at: UtcDatetime
