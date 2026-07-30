"""External status, customer success, evidence, and F05 incident models."""

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


class ExternalPlatformReference(Base):
    __tablename__ = "external_platform_references"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    project_reference = Column(String(160), nullable=True)
    platform_status = Column(String(24), nullable=False, default="unknown")
    processing_started = Column(Boolean, nullable=False, default=False)
    route_detected = Column(Boolean, nullable=False, default=False)
    plan_connected = Column(Boolean, nullable=False, default=False)
    tour_ready = Column(Boolean, nullable=False, default=False)
    captures_menu_checked = Column(Boolean, nullable=False, default=False)
    latest_capture_checked = Column(Boolean, nullable=False, default=False)
    last_visit_checked = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=True)
    checked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checked_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "platform_status IN ('available', 'degraded', 'down', 'unknown')",
            name="ck_external_platform_status",
        ),
    )

    pilot = relationship("Pilot", back_populates="external_platform_reference")
    checked_by = relationship("User", foreign_keys=[checked_by_user_id])


class FormF04(Base):
    __tablename__ = "form_f04"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner_logged_in = Column(Boolean, nullable=False, default=False)
    project_opened = Column(Boolean, nullable=False, default=False)
    main_tour_viewed = Column(Boolean, nullable=False, default=False)
    training_completed = Column(Boolean, nullable=False, default=False)
    viewing_result = Column(Text, nullable=True)
    issue_description = Column(Text, nullable=True)
    issue_category = Column(String(32), nullable=True)
    issue_route = Column(String(32), nullable=True)
    issue_owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    issue_due_at = Column(DateTime, nullable=True)
    first_follow_up_at = Column(DateTime, nullable=True)
    second_follow_up_at = Column(DateTime, nullable=True)
    useful = Column(Boolean, nullable=True)
    coverage_score = Column(Integer, nullable=True)
    quality_score = Column(Integer, nullable=True)
    most_useful_part = Column(Text, nullable=True)
    missing_part = Column(Text, nullable=True)
    other_users = Column(Text, nullable=True)
    more_training_needed = Column(Boolean, nullable=True)
    satisfaction_score = Column(Integer, nullable=True)
    continuation_interest = Column(Boolean, nullable=True)
    proposal_ready = Column(Boolean, nullable=True)
    realized_value = Column(Text, nullable=True)
    purchase_blocker = Column(Text, nullable=True)
    project_count = Column(Integer, nullable=True)
    usage_frequency = Column(String(160), nullable=True)
    user_count = Column(Integer, nullable=True)
    decision_maker = Column(String(160), nullable=True)
    next_action = Column(Text, nullable=True)
    final_result = Column(String(160), nullable=True)
    final_reason = Column(Text, nullable=True)
    customer_success_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    sales_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pilot_manager_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    login_trained = Column(Boolean, nullable=False, default=False)
    project_trained = Column(Boolean, nullable=False, default=False)
    floor_trained = Column(Boolean, nullable=False, default=False)
    plan_trained = Column(Boolean, nullable=False, default=False)
    tour_trained = Column(Boolean, nullable=False, default=False)
    navigation_trained = Column(Boolean, nullable=False, default=False)
    support_trained = Column(Boolean, nullable=False, default=False)
    independent_use_confirmed = Column(Boolean, nullable=False, default=False)
    main_platform_login_count = Column(Integer, nullable=True)
    viewed_sections = Column(JSON_TYPE, nullable=False, default=list)
    visit_reduction_result = Column(String(24), nullable=True)
    customer_need_summary = Column(Text, nullable=True)
    closing_decision = Column(String(24), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint(
            "issue_category IS NULL OR issue_category IN "
            "('access', 'platform', 'coverage_quality', 'training', "
            "'capability', 'continuation')",
            name="ck_form_f04_issue_category",
        ),
        CheckConstraint(
            "issue_route IS NULL OR issue_route IN "
            "('support', 'technical', 'operations', 'training', 'product', 'sales')",
            name="ck_form_f04_issue_route",
        ),
        CheckConstraint(
            "coverage_score IS NULL OR coverage_score BETWEEN 1 AND 10",
            name="ck_form_f04_coverage_score",
        ),
        CheckConstraint(
            "quality_score IS NULL OR quality_score BETWEEN 1 AND 10",
            name="ck_form_f04_quality_score",
        ),
        CheckConstraint(
            "satisfaction_score IS NULL OR satisfaction_score BETWEEN 1 AND 10",
            name="ck_form_f04_satisfaction_score",
        ),
        CheckConstraint(
            "project_count IS NULL OR project_count >= 0",
            name="ck_form_f04_project_count",
        ),
        CheckConstraint(
            "user_count IS NULL OR user_count >= 0",
            name="ck_form_f04_user_count",
        ),
        CheckConstraint(
            "main_platform_login_count IS NULL OR main_platform_login_count >= 0",
            name="ck_form_f04_main_platform_login_count",
        ),
        CheckConstraint(
            "visit_reduction_result IS NULL OR visit_reduction_result IN "
            "('confirmed', 'not_confirmed', 'unknown')",
            name="ck_form_f04_visit_reduction_result",
        ),
        CheckConstraint(
            "closing_decision IS NULL OR closing_decision IN "
            "('proposal', 'follow_up', 'continue_pilot', 'stop', 'undecided')",
            name="ck_form_f04_closing_decision",
        ),
    )

    pilot = relationship("Pilot", back_populates="form_f04")
    responsible = relationship("User", foreign_keys=[responsible_user_id])
    issue_owner = relationship("User", foreign_keys=[issue_owner_user_id])
    customer_success_user = relationship("User", foreign_keys=[customer_success_user_id])
    sales_user = relationship("User", foreign_keys=[sales_user_id])
    pilot_manager_user = relationship("User", foreign_keys=[pilot_manager_user_id])


class ExternalEvidenceCheck(Base):
    __tablename__ = "external_evidence_checks"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    capability = Column(String(80), nullable=False)
    status = Column(String(24), nullable=False)
    checked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checked_at = Column(DateTime, nullable=False)
    result = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint(
            "pilot_id",
            "capability",
            name="uq_external_evidence_pilot_capability",
        ),
        CheckConstraint(
            "status IN ('checked', 'mismatch', 'unavailable', 'not_checked')",
            name="ck_external_evidence_status",
        ),
    )

    pilot = relationship("Pilot", back_populates="external_evidence_checks")
    checked_by = relationship("User", foreign_keys=[checked_by_user_id])


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=True, index=True)
    sequence = Column(Integer, nullable=False)
    code = Column(String(64), nullable=False, unique=True, index=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stage_number = Column(Integer, nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)
    incident_type = Column(String(24), nullable=False, index=True)
    description = Column(Text, nullable=False)
    containment_action = Column(Text, nullable=True)
    notified_people = Column(JSON_TYPE, nullable=False, default=list)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    response_due_at = Column(DateTime, nullable=False, index=True)
    correction_due_at = Column(DateTime, nullable=True)
    result = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="open", index=True)
    closed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("pilot_id", "sequence", name="uq_incident_pilot_sequence"),
        CheckConstraint(
            "stage_number BETWEEN 1 AND 19",
            name="ck_incident_stage_number",
        ),
        CheckConstraint(
            "severity IN ('normal', 'important', 'critical')",
            name="ck_incident_severity",
        ),
        CheckConstraint(
            "incident_type IN "
            "('safety', 'equipment', 'dwg', 'main_platform', "
            "'access', 'customer', 'process')",
            name="ck_incident_type",
        ),
        CheckConstraint(
            "status IN ('open', 'contained', 'resolved', 'closed')",
            name="ck_incident_status",
        ),
    )

    pilot = relationship("Pilot", back_populates="incidents")
    mission = relationship("Mission")
    reported_by = relationship("User", foreign_keys=[reported_by_user_id])
    owner = relationship("User", foreign_keys=[owner_user_id])
    closed_by = relationship("User", foreign_keys=[closed_by_user_id])
