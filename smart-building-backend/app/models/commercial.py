"""Commercial proposal, sales follow-up, and final outcome models."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
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


class CommercialProposal(Base):
    __tablename__ = "commercial_proposals"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_count = Column(Integer, nullable=False)
    floor_count = Column(Integer, nullable=False)
    area_sqm = Column(Float, nullable=False)
    frequency = Column(String(160), nullable=False)
    period = Column(String(160), nullable=False)
    user_count = Column(Integer, nullable=False)
    support_scope = Column(Text, nullable=False)
    features = Column(JSON_TYPE, nullable=False, default=list)
    proposal_file_name = Column(String(255), nullable=False)
    proposal_file_size = Column(Integer, nullable=False)
    proposal_file_sha256 = Column(String(64), nullable=False)
    decision_maker = Column(String(160), nullable=False)
    follow_up_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("project_count > 0", name="ck_commercial_proposal_project_count"),
        CheckConstraint("floor_count > 0", name="ck_commercial_proposal_floor_count"),
        CheckConstraint("area_sqm > 0", name="ck_commercial_proposal_area"),
        CheckConstraint("user_count > 0", name="ck_commercial_proposal_user_count"),
        CheckConstraint(
            "proposal_file_size > 0",
            name="ck_commercial_proposal_file_size",
        ),
    )

    pilot = relationship("Pilot", back_populates="commercial_proposal")
    responsible = relationship("User", foreign_keys=[responsible_user_id])


class CustomerFollowUp(Base):
    __tablename__ = "customer_follow_ups"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    schedule_slot = Column(String(16), nullable=False)
    obstacle = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    due_at = Column(DateTime, nullable=False)
    result = Column(Text, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint(
            "pilot_id",
            "schedule_slot",
            name="uq_customer_follow_up_pilot_slot",
        ),
        CheckConstraint(
            "schedule_slot IN ('day_0', 'day_2', 'day_5', 'day_7_10')",
            name="ck_customer_follow_up_schedule_slot",
        ),
    )

    pilot = relationship("Pilot", back_populates="customer_follow_ups")
    owner = relationship("User", foreign_keys=[owner_user_id])


class FinalOutcome(Base):
    __tablename__ = "final_outcomes"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(String(24), nullable=False)
    reason = Column(Text, nullable=True)
    ready_at = Column(DateTime, nullable=True)
    success_owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    periodic_capture = Column(Boolean, nullable=True)
    contracted_user_count = Column(Integer, nullable=True)
    first_capture_at = Column(DateTime, nullable=True)
    pilot_manager_approved = Column(Boolean, nullable=False, default=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "outcome IN "
            "('contract', 'ready_on_date', 'negotiation', 'rejected', 'closed')",
            name="ck_final_outcome_value",
        ),
        CheckConstraint(
            "contracted_user_count IS NULL OR contracted_user_count > 0",
            name="ck_final_outcome_contracted_user_count",
        ),
    )

    pilot = relationship("Pilot", back_populates="final_outcome")
    responsible = relationship("User", foreign_keys=[responsible_user_id])
    success_owner = relationship("User", foreign_keys=[success_owner_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
