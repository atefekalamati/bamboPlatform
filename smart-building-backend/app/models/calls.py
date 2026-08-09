"""Provider-neutral telephone call persistence."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSON_TYPE


def utc_now() -> datetime:
    return datetime.now(UTC)


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), nullable=False, unique=True, index=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    stage_id = Column(Integer, ForeignKey("pilot_stages.id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True, index=True)
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    destination_phone = Column(String(20), nullable=False)
    destination_masked = Column(String(24), nullable=False)
    purpose = Column(String(80), nullable=False)
    technical_status = Column(String(32), nullable=False, default="pending", index=True)
    business_outcome = Column(String(48), nullable=True, index=True)
    summary = Column(Text, nullable=True)
    next_action = Column(Text, nullable=True)
    callback_at = Column(DateTime, nullable=True, index=True)
    recording_consent = Column(Boolean, nullable=False, default=False)
    recording_reference = Column(String(500), nullable=True)
    controlled_metadata = Column(JSON_TYPE, nullable=False, default=dict)
    idempotency_key = Column(String(120), nullable=False, unique=True)
    override_reason = Column(Text, nullable=True)
    overridden_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    overridden_at = Column(DateTime, nullable=True)
    requested_at = Column(DateTime, nullable=False, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    pilot = relationship("Pilot")
    stage = relationship("PilotStage")
    owner = relationship("Owner")
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id])
    overridden_by = relationship("User", foreign_keys=[overridden_by_user_id])
    attempts = relationship("CallAttempt", back_populates="call", cascade="all, delete-orphan", order_by="CallAttempt.attempt_number")
    outcomes = relationship("CallOutcome", back_populates="call", cascade="all, delete-orphan", order_by="CallOutcome.created_at")


class CallAttempt(Base):
    __tablename__ = "call_attempts"

    id = Column(Integer, primary_key=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    provider = Column(String(32), nullable=False)
    provider_call_id = Column(String(160), nullable=True, unique=True, index=True)
    status = Column(String(32), nullable=False, index=True)
    failure_code = Column(String(80), nullable=True)
    failure_reason = Column(String(500), nullable=True)
    requested_at = Column(DateTime, nullable=False, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (UniqueConstraint("call_id", "attempt_number", name="uq_call_attempt_number"),)
    call = relationship("Call", back_populates="attempts")


class CallOutcome(Base):
    __tablename__ = "call_outcomes"

    id = Column(Integer, primary_key=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    outcome = Column(String(48), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    next_action = Column(Text, nullable=True)
    callback_at = Column(DateTime, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    call = relationship("Call", back_populates="outcomes")
    recorded_by = relationship("User")


class CallWebhookEvent(Base):
    __tablename__ = "call_webhook_events"

    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False)
    event_id = Column(String(160), nullable=False)
    provider_call_id = Column(String(160), nullable=True, index=True)
    event_type = Column(String(80), nullable=False)
    payload_sanitized = Column(JSON_TYPE, nullable=False, default=dict)
    processed = Column(Boolean, nullable=False, default=False)
    received_at = Column(DateTime, nullable=False, default=utc_now)
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_call_webhook_provider_event"),)
