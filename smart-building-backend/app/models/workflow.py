"""Pilot workflow persistence models."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, event
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSON_TYPE


def utc_now() -> datetime:
    return datetime.now(UTC)


class Pilot(Base):
    __tablename__ = "pilots"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    pilot_year = Column(Integer, nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    project_number = Column(Integer, nullable=False, unique=True)
    project_system_name = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    status = Column(String(40), nullable=False, default="candidate")
    current_stage = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (UniqueConstraint("pilot_year", "sequence", name="uq_pilot_year_sequence"),)

    stages = relationship(
        "PilotStage",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="PilotStage.number",
    )
    gates = relationship(
        "PilotGate",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="PilotGate.after_stage",
    )
    project = relationship(
        "Project",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    form_f01 = relationship(
        "FormF01",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    form_f02 = relationship(
        "FormF02",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    missions = relationship(
        "Mission",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="Mission.sequence",
    )
    external_platform_reference = relationship(
        "ExternalPlatformReference",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    form_f04 = relationship(
        "FormF04",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    external_evidence_checks = relationship(
        "ExternalEvidenceCheck",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="ExternalEvidenceCheck.capability",
    )
    incidents = relationship(
        "Incident",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="Incident.sequence",
    )
    notifications = relationship(
        "Notification",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="Notification.created_at",
    )
    evaluation = relationship(
        "PilotEvaluation",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    commercial_proposal = relationship(
        "CommercialProposal",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )
    customer_follow_ups = relationship(
        "CustomerFollowUp",
        back_populates="pilot",
        cascade="all, delete-orphan",
        order_by="CustomerFollowUp.id",
    )
    final_outcome = relationship(
        "FinalOutcome",
        back_populates="pilot",
        cascade="all, delete-orphan",
        uselist=False,
    )


class PilotStage(Base):
    __tablename__ = "pilot_stages"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    title = Column(String(160), nullable=False)
    status = Column(String(32), nullable=False, default="locked")
    latest_version = Column(Integer, nullable=False, default=0)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (UniqueConstraint("pilot_id", "number", name="uq_pilot_stage_number"),)

    pilot = relationship("Pilot", back_populates="stages")
    submissions = relationship(
        "StageSubmission",
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="StageSubmission.version",
    )


class StageSubmission(Base):
    __tablename__ = "stage_submissions"

    id = Column(Integer, primary_key=True)
    stage_id = Column(Integer, ForeignKey("pilot_stages.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="submitted")
    form_data = Column(JSON_TYPE, nullable=False, default=dict)
    checklist = Column(JSON_TYPE, nullable=False, default=dict)
    submitted_by = Column(String(120), nullable=False)
    submitted_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (UniqueConstraint("stage_id", "version", name="uq_stage_submission_version"),)

    stage = relationship("PilotStage", back_populates="submissions")
    review = relationship(
        "StageApproval",
        back_populates="submission",
        cascade="all, delete-orphan",
        uselist=False,
    )


class StageApproval(Base):
    __tablename__ = "stage_approvals"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("stage_submissions.id"), nullable=False, unique=True)
    decision = Column(String(16), nullable=False)
    reviewer = Column(String(120), nullable=False)
    reason = Column(String(1000), nullable=True)
    correction_items = Column(JSON_TYPE, nullable=False, default=list)
    reviewed_at = Column(DateTime, nullable=False, default=utc_now)

    submission = relationship("StageSubmission", back_populates="review")
    snapshot = relationship(
        "ImmutableSnapshot",
        back_populates="approval",
        cascade="all, delete-orphan",
        uselist=False,
    )


class PilotGate(Base):
    __tablename__ = "pilot_gates"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    code = Column(String(8), nullable=False)
    title = Column(String(80), nullable=False)
    after_stage = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="locked")
    passed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("pilot_id", "code", name="uq_pilot_gate_code"),)

    pilot = relationship("Pilot", back_populates="gates")


class ImmutableSnapshot(Base):
    __tablename__ = "immutable_snapshots"

    id = Column(Integer, primary_key=True)
    approval_id = Column(Integer, ForeignKey("stage_approvals.id"), nullable=False, unique=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    content = Column(JSON_TYPE, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("pilot_id", "stage_number", "version", name="uq_snapshot_stage_version"),
    )

    approval = relationship("StageApproval", back_populates="snapshot")


@event.listens_for(ImmutableSnapshot, "before_update")
@event.listens_for(ImmutableSnapshot, "before_delete")
def prevent_snapshot_mutation(*_args) -> None:
    raise ValueError("Approved snapshots are immutable")
