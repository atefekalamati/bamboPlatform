"""Users, RBAC, OTP, sessions, and audit persistence models."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import JSON_TYPE


def utc_now() -> datetime:
    return datetime.now(UTC)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("assigned_at", DateTime, nullable=False, default=utc_now),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
    Column("assigned_at", DateTime, nullable=False, default=utc_now),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    mobile = Column(String(20), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    locked_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship(
        "UserPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=False)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    code = Column(String(120), nullable=False, unique=True, index=True)
    group_name = Column(String(80), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    is_sensitive = Column(Boolean, nullable=False, default=False)

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class OtpRequest(Base):
    __tablename__ = "otp_requests"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(36), nullable=False, unique=True, index=True)
    mobile = Column(String(20), nullable=False, index=True)
    purpose = Column(String(32), nullable=False, default="auth")
    code_hash = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    provider_status = Column(String(80), nullable=False)
    request_ip = Column(String(64), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    verified_at = Column(DateTime, nullable=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    language = Column(String(16), nullable=False, default="fa")
    theme = Column(String(16), nullable=False, default="light")
    timezone = Column(String(64), nullable=False, default="Asia/Tehran")
    calendar = Column(String(16), nullable=False, default="jalali")
    page_size = Column(Integer, nullable=False, default=20)
    default_page = Column(String(120), nullable=True)
    last_page = Column(String(120), nullable=True)
    visible_columns = Column(JSON_TYPE, nullable=False, default=dict)
    column_order = Column(JSON_TYPE, nullable=False, default=dict)
    saved_filters = Column(JSON_TYPE, nullable=False, default=dict)
    notification_preferences = Column(JSON_TYPE, nullable=False, default=dict)
    dashboard_preferences = Column(JSON_TYPE, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="preferences")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(120), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(String(80), nullable=True)
    pilot_id = Column(Integer, ForeignKey("pilots.id"), nullable=True, index=True)
    old_data = Column(JSON_TYPE, nullable=True)
    new_data = Column(JSON_TYPE, nullable=True)
    reason = Column(Text, nullable=True)
    request_id = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(Integer, ForeignKey("auth_sessions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)
