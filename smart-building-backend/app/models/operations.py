"""Mission, F03, per-Floor capture state, and notification persistence."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSON_TYPE


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    code = Column(String(64), nullable=False, unique=True, index=True)
    expert_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False, index=True)
    location = Column(String(500), nullable=False)
    site_contact_name = Column(String(120), nullable=False)
    site_contact_mobile = Column(String(20), nullable=False)
    limitation = Column(Text, nullable=True)
    status = Column(String(24), nullable=False, default="scheduled", index=True)
    sla_due_at = Column(DateTime, nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("pilot_id", "sequence", name="uq_mission_pilot_sequence"),
        CheckConstraint(
            "scheduled_end > scheduled_start",
            name="ck_mission_schedule_interval",
        ),
        CheckConstraint(
            "status IN ('scheduled', 'assigned', 'ready', 'in_progress', "
            "'completed', 'cancelled')",
            name="ck_mission_status",
        ),
    )

    pilot = relationship("Pilot", back_populates="missions")
    expert = relationship("User", foreign_keys=[expert_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    floor_states = relationship(
        "MissionFloor",
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="MissionFloor.id",
    )
    form_f03 = relationship(
        "FormF03",
        back_populates="mission",
        cascade="all, delete-orphan",
        uselist=False,
    )
    notifications = relationship(
        "Notification",
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="Notification.created_at",
    )
    continuation_review = relationship(
        "ContinuationReview",
        back_populates="mission",
        cascade="all, delete-orphan",
        uselist=False,
    )

    @property
    def display_name(self) -> str:
        """Stable human-readable label without changing the formal mission code."""
        return f"مأموریت {self.sequence:02d} — {self.pilot.code}"


class MissionFloor(Base):
    __tablename__ = "mission_floors"

    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, index=True)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=False, index=True)
    capture_state = Column(String(24), nullable=False, default="not_started")
    correct_floor = Column(Boolean, nullable=False, default=False)
    start_point_confirmed = Column(Boolean, nullable=False, default=False)
    main_capture_started = Column(Boolean, nullable=False, default=False)
    continuous_route = Column(Boolean, nullable=False, default=False)
    coverage_completed = Column(Boolean, nullable=False, default=False)
    capture_finished = Column(Boolean, nullable=False, default=False)
    saved_in_main_app = Column(Boolean, nullable=False, default=False)
    capture_started_at = Column(DateTime, nullable=True)
    capture_finished_at = Column(DateTime, nullable=True)
    main_upload_started = Column(Boolean, nullable=False, default=False)
    main_upload_completed = Column(Boolean, nullable=False, default=False)
    correct_floor_link = Column(Boolean, nullable=False, default=False)
    operations_notified = Column(Boolean, nullable=False, default=False)
    failure_reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("mission_id", "floor_id", name="uq_mission_floor"),
        CheckConstraint(
            "capture_state IN ('not_started', 'completed', 'incomplete', "
            "'not_done', 'needs_revision')",
            name="ck_mission_floor_capture_state",
        ),
        CheckConstraint(
            "capture_finished_at IS NULL OR capture_started_at IS NULL "
            "OR capture_finished_at >= capture_started_at",
            name="ck_mission_floor_capture_interval",
        ),
    )

    mission = relationship("Mission", back_populates="floor_states")
    floor = relationship("Floor", back_populates="mission_states")


class FormF03(Base):
    __tablename__ = "form_f03"

    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignment_accepted = Column(Boolean, nullable=False, default=False)
    site_entry_confirmed = Column(Boolean, nullable=False, default=False)
    permission_confirmed = Column(Boolean, nullable=False, default=False)
    ppe_ready = Column(Boolean, nullable=False, default=False)
    camera_ready = Column(Boolean, nullable=False, default=False)
    main_app_connected = Column(Boolean, nullable=False, default=False)
    battery_ready = Column(Boolean, nullable=False, default=False)
    storage_ready = Column(Boolean, nullable=False, default=False)
    project_floor_plan_confirmed = Column(Boolean, nullable=False, default=False)
    test_image_completed = Column(Boolean, nullable=False, default=False)
    stop_condition_reason = Column(Text, nullable=True)
    mission_completed = Column(Boolean, nullable=False, default=False)
    operations_confirmed = Column(Boolean, nullable=False, default=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="ck_form_f03_interval",
        ),
    )

    mission = relationship("Mission", back_populates="form_f03")
    responsible = relationship("User", foreign_keys=[responsible_user_id])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), nullable=False, unique=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=True, index=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    recipient_mobile = Column(String(20), nullable=False)
    channel = Column(String(16), nullable=False, default="SMS")
    notification_type = Column(String(80), nullable=False, default="system.notification", index=True)
    category = Column(String(32), nullable=False, default="SYSTEM", index=True)
    priority = Column(String(16), nullable=False, default="NORMAL", index=True)
    title = Column(String(160), nullable=False, default="")
    body = Column(Text, nullable=False, default="")
    short_body = Column(String(255), nullable=True)
    entity_type = Column(String(80), nullable=True, index=True)
    entity_id = Column(String(80), nullable=True, index=True)
    action_url = Column(String(500), nullable=True)
    template = Column(String(80), nullable=False, index=True)
    payload = Column(JSON_TYPE, nullable=False, default=dict)
    status = Column(String(24), nullable=False, index=True)
    provider_status = Column(String(120), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String(500), nullable=True)
    alternate_contact_method = Column(String(500), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deduplication_key = Column(String(160), nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'delivered', 'failed')",
            name="ck_notification_status",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')",
            name="ck_notification_priority",
        ),
        CheckConstraint(
            "category IN ('AUTH', 'PILOT', 'STAGE', 'MISSION', 'INCIDENT', "
            "'SLA', 'COMMERCIAL', 'SYSTEM')",
            name="ck_notification_category",
        ),
    )

    mission = relationship("Mission", back_populates="notifications")
    pilot = relationship("Pilot", back_populates="notifications")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    actor_user = relationship("User", foreign_keys=[actor_user_id])
    deliveries = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
        order_by="NotificationDelivery.id",
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    channel = Column(String(16), nullable=False, index=True)
    recipient_address = Column(String(160), nullable=False)
    provider = Column(String(80), nullable=False)
    template_code = Column(String(80), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    provider_message_id = Column(String(120), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_code = Column(String(80), nullable=True)
    failure_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "channel IN ('IN_APP', 'SMS')",
            name="ck_notification_delivery_channel",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'QUEUED', 'SENDING', 'SENT', 'DELIVERED', "
            "'FAILED', 'CANCELLED', 'SKIPPED')",
            name="ck_notification_delivery_status",
        ),
    )

    notification = relationship("Notification", back_populates="deliveries")
