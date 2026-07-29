"""Project, F01/F02, floor, and DWG domain models."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False, index=True)
    decision_maker_name = Column(String(120), nullable=False)
    decision_maker_position = Column(String(120), nullable=False)
    primary_mobile = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    projects = relationship("Project", back_populates="owner")
    contacts = relationship("Contact", back_populates="owner", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    position = Column(String(120), nullable=True)
    mobile = Column(String(20), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    is_site_coordinator = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    owner = relationship("Owner", back_populates="contacts")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False, index=True)
    system_name = Column(String(64), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    name = Column(String(160), nullable=False)
    total_floors = Column(Integer, nullable=False)
    address = Column(String(500), nullable=False)
    progress_stage = Column(String(160), nullable=False)
    customer_need = Column(Text, nullable=False)
    expected_value = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    pilot = relationship("Pilot", back_populates="project")
    owner = relationship("Owner", back_populates="projects")
    floors = relationship(
        "Floor",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Floor.level_order",
    )


class Floor(Base):
    __tablename__ = "floors"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(120), nullable=False)
    level_order = Column(Integer, nullable=False)
    floor_type = Column(String(24), nullable=False, default="non_typical")
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("project_id", "code", name="uq_floor_project_code"),
        UniqueConstraint("project_id", "level_order", name="uq_floor_project_order"),
    )

    project = relationship("Project", back_populates="floors")
    dwg_file = relationship(
        "DwgFile",
        back_populates="floor",
        cascade="all, delete-orphan",
        uselist=False,
    )


class DwgFile(Base):
    __tablename__ = "dwg_files"

    id = Column(Integer, primary_key=True)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    floor = relationship("Floor", back_populates="dwg_file")
    versions = relationship(
        "DwgVersion",
        back_populates="dwg_file",
        cascade="all, delete-orphan",
        order_by="DwgVersion.version",
    )


class DwgVersion(Base):
    __tablename__ = "dwg_versions"

    id = Column(Integer, primary_key=True)
    dwg_file_id = Column(Integer, ForeignKey("dwg_files.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    original_filename = Column(String(255), nullable=False)
    standardized_filename = Column(String(255), nullable=False, unique=True)
    storage_key = Column(String(500), nullable=False, unique=True)
    mime_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    dwg_signature = Column(String(12), nullable=False)
    is_readable = Column(Boolean, nullable=False, default=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("dwg_file_id", "version", name="uq_dwg_file_version"),
        UniqueConstraint("dwg_file_id", "sha256", name="uq_dwg_file_hash"),
    )

    dwg_file = relationship("DwgFile", back_populates="versions")
    uploaded_by = relationship("User")


class FormF01(Base):
    __tablename__ = "form_f01"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    case_owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_active = Column(Boolean, nullable=False)
    imaging_value = Column(Boolean, nullable=False)
    remote_viewing_need = Column(Boolean, nullable=False)
    access_possible = Column(Boolean, nullable=False)
    dwg_available = Column(Boolean, nullable=False)
    continued_capacity = Column(Boolean, nullable=False)
    not_demo_only = Column(Boolean, nullable=False)
    introduction_completed = Column(Boolean, nullable=False)
    imaging_accepted = Column(Boolean, nullable=False)
    dwg_accepted = Column(Boolean, nullable=False)
    feedback_accepted = Column(Boolean, nullable=False)
    coordinator_name = Column(String(120), nullable=True)
    coordinator_mobile = Column(String(20), nullable=True)
    limitation = Column(Text, nullable=True)
    result = Column(String(32), nullable=False)
    referral_deadline = Column(Date, nullable=True)
    sales_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pilot_manager_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referred_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    pilot = relationship("Pilot", back_populates="form_f01")


class FormF02(Base):
    __tablename__ = "form_f02"

    id = Column(Integer, primary_key=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=False, unique=True)
    responsible_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    information_package = Column(Text, nullable=True)
    contacts_summary = Column(Text, nullable=True)
    progress_status = Column(String(160), nullable=True)
    limitation = Column(Text, nullable=True)
    main_project_registered = Column(Boolean, nullable=False, default=False)
    floor_order_confirmed = Column(Boolean, nullable=False, default=False)
    typical_floors_identified = Column(Boolean, nullable=False, default=False)
    plan_connections_registered = Column(Boolean, nullable=False, default=False)
    start_point_registered = Column(Boolean, nullable=False, default=False)
    expert_access_tested = Column(Boolean, nullable=False, default=False)
    main_app_display_tested = Column(Boolean, nullable=False, default=False)
    ready_for_capture = Column(Boolean, nullable=False, default=False)
    ambiguity = Column(Text, nullable=True)
    referred_at = Column(DateTime, nullable=True)
    configured_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    controlled_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    configured_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    pilot = relationship("Pilot", back_populates="form_f02")
