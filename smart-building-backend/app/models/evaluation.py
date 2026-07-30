"""Continuation-capture and cross-functional pilot evaluation models."""

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
)
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ContinuationReview(Base):
    __tablename__ = "continuation_reviews"

    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stage_5_confirmed = Column(Boolean, nullable=False, default=False)
    stage_6_confirmed = Column(Boolean, nullable=False, default=False)
    stage_7_confirmed = Column(Boolean, nullable=False, default=False)
    stage_8_confirmed = Column(Boolean, nullable=False, default=False)
    stage_9_confirmed = Column(Boolean, nullable=False, default=False)
    stage_10_confirmed = Column(Boolean, nullable=False, default=False)
    stage_11_confirmed = Column(Boolean, nullable=False, default=False)
    stage_12_confirmed = Column(Boolean, nullable=False, default=False)
    stage_13_confirmed = Column(Boolean, nullable=False, default=False)
    independent_result = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    mission = relationship("Mission", back_populates="continuation_review")
    responsible = relationship("User", foreign_keys=[responsible_user_id])


class PilotEvaluation(Base):
    __tablename__ = "pilot_evaluations"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operations_status = Column(String(24), nullable=False)
    operations_result = Column(Text, nullable=False)
    quality_status = Column(String(24), nullable=False)
    quality_result = Column(Text, nullable=False)
    technical_status = Column(String(24), nullable=False)
    technical_result = Column(Text, nullable=False)
    customer_status = Column(String(24), nullable=False)
    customer_result = Column(Text, nullable=False)
    commercial_status = Column(String(24), nullable=False)
    commercial_result = Column(Text, nullable=False)
    one_page_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "operations_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_operations_status",
        ),
        CheckConstraint(
            "quality_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_quality_status",
        ),
        CheckConstraint(
            "technical_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_technical_status",
        ),
        CheckConstraint(
            "customer_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_customer_status",
        ),
        CheckConstraint(
            "commercial_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_commercial_status",
        ),
    )

    pilot = relationship("Pilot", back_populates="evaluation")
    responsible = relationship("User", foreign_keys=[responsible_user_id])
