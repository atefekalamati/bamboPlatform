"""OTP authentication, session, permission, and audit services."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import (
    get_app_env,
    get_auth_secret,
    get_bootstrap_super_admin_mobile,
    get_int_setting,
)
from app.database import get_db
from app.exceptions import SecurityError
from app.models import AuditLog, AuthSession, OtpRequest, Permission, Role, User
from app.rbac import PERMISSIONS, SYSTEM_ROLES
from app.schemas.security import normalize_mobile

bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def mask_mobile(mobile: str) -> str:
    return f"{mobile[:4]}***{mobile[-4:]}"


def _otp_hash(public_id: str, code: str) -> str:
    payload = f"{public_id}:{code}".encode()
    return hmac.new(get_auth_secret().encode(), payload, hashlib.sha256).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _transaction_lock(db: Session, scope: str) -> None:
    """Serialize a small authentication scope across PostgreSQL workers."""
    if db.get_bind().dialect.name != "postgresql":
        return
    lock_key = int.from_bytes(
        hashlib.sha256(scope.encode()).digest()[:8],
        byteorder="big",
        signed=True,
    )
    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )


def effective_permissions(user: User) -> set[str]:
    return {
        permission.code
        for role in user.roles
        if role.is_active
        for permission in role.permissions
    }


def add_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int | None,
    actor_user_id: int | None = None,
    pilot_id: int | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    reason: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    session_id: int | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        pilot_id=pilot_id,
        old_data=old_data,
        new_data=new_data,
        reason=reason,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
    )
    db.add(log)
    return log


def seed_security_data(db: Session) -> None:
    permissions_by_code = {item.code: item for item in db.query(Permission).all()}
    new_permission_codes: set[str] = set()
    for code, group, description, sensitive in PERMISSIONS:
        if code not in permissions_by_code:
            permission = Permission(
                code=code,
                group_name=group,
                description=description,
                is_sensitive=sensitive,
            )
            db.add(permission)
            permissions_by_code[code] = permission
            new_permission_codes.add(code)
    db.flush()

    roles_by_name = {item.name: item for item in db.query(Role).all()}
    for name, (display_name, permission_codes) in SYSTEM_ROLES.items():
        role = roles_by_name.get(name)
        if role is None:
            role = Role(
                name=name,
                display_name=display_name,
                is_system=True,
                permissions=[permissions_by_code[code] for code in permission_codes],
            )
            db.add(role)
            roles_by_name[name] = role
        elif name == "super_admin":
            existing = {permission.code for permission in role.permissions}
            role.permissions.extend(
                permissions_by_code[code] for code in permission_codes - existing
            )
        elif new_permission_codes:
            existing = {permission.code for permission in role.permissions}
            role.permissions.extend(
                permissions_by_code[code]
                for code in (permission_codes & new_permission_codes) - existing
            )
    db.commit()


@dataclass
class OtpDispatch:
    request: OtpRequest
    debug_code: str | None
    retry_after: int


def request_otp(db: Session, mobile: str, ip_address: str | None) -> OtpDispatch:
    now = utc_now()
    window_seconds = get_int_setting("OTP_RATE_WINDOW_SECONDS", 600)
    max_requests = get_int_setting("OTP_MAX_REQUESTS_PER_WINDOW", 3)
    cooldown = get_int_setting("OTP_RESEND_COOLDOWN_SECONDS", 60)
    _transaction_lock(db, f"otp-request-mobile:{mobile}")
    if ip_address:
        _transaction_lock(db, f"otp-request-ip:{ip_address}")
    recent = (
        db.query(OtpRequest)
        .filter(
            OtpRequest.mobile == mobile,
            OtpRequest.created_at >= now - timedelta(seconds=window_seconds),
        )
        .order_by(OtpRequest.created_at.desc())
        .all()
    )
    if len(recent) >= max_requests:
        retry_after = max(
            1,
            int((recent[-1].created_at + timedelta(seconds=window_seconds) - now).total_seconds()),
        )
        raise SecurityError(
            code="OTP_RATE_LIMITED",
            message="درخواست بیش از حد مجاز است. بعداً دوباره تلاش کنید.",
            status_code=429,
            errors=[],
            retry_after=retry_after,
        )
    if ip_address:
        max_ip_requests = get_int_setting("OTP_MAX_IP_REQUESTS_PER_WINDOW", 20)
        ip_request_count = (
            db.query(OtpRequest)
            .filter(
                OtpRequest.request_ip == ip_address,
                OtpRequest.created_at >= now - timedelta(seconds=window_seconds),
            )
            .count()
        )
        if ip_request_count >= max_ip_requests:
            raise SecurityError(
                code="OTP_RATE_LIMITED",
                message="درخواست بیش از حد مجاز است. بعداً دوباره تلاش کنید.",
                status_code=429,
                errors=[],
                retry_after=window_seconds,
            )
    if recent:
        elapsed = int((now - recent[0].created_at).total_seconds())
        if elapsed < cooldown:
            raise SecurityError(
                code="OTP_COOLDOWN",
                message="برای ارسال مجدد کمی صبر کنید.",
                status_code=429,
                errors=[],
                retry_after=cooldown - elapsed,
            )

    public_id = str(uuid4())
    code = f"{secrets.randbelow(1_000_000):06d}"
    ttl = get_int_setting("OTP_TTL_SECONDS", 300)
    if get_app_env() == "production":
        raise SecurityError(
            code="OTP_PROVIDER_UNAVAILABLE",
            message="سرویس ارسال کد موقتاً در دسترس نیست.",
            status_code=503,
            errors=[],
        )

    otp_request = OtpRequest(
        public_id=public_id,
        mobile=mobile,
        code_hash=_otp_hash(public_id, code),
        provider_status="accepted:console" if get_app_env() != "production" else "accepted",
        request_ip=ip_address,
        expires_at=now + timedelta(seconds=ttl),
        max_attempts=get_int_setting("OTP_MAX_ATTEMPTS", 5),
    )
    db.add(otp_request)
    add_audit_log(
        db,
        action="auth.otp_requested",
        entity_type="OtpRequest",
        entity_id=public_id,
        ip_address=ip_address,
        new_data={"mobile": mask_mobile(mobile), "provider_status": otp_request.provider_status},
    )
    db.commit()
    db.refresh(otp_request)
    return OtpDispatch(
        request=otp_request,
        debug_code=code if get_app_env() in {"development", "test"} else None,
        retry_after=cooldown,
    )


def verify_otp(
    db: Session, request_id: str, code: str, ip_address: str | None
) -> tuple[str, int, User]:
    now = utc_now()
    otp_request = (
        db.query(OtpRequest)
        .filter(OtpRequest.public_id == request_id)
        .with_for_update()
        .first()
    )
    generic_error = SecurityError(
        code="OTP_INVALID",
        message="کد نامعتبر یا منقضی است.",
        status_code=400,
        errors=[],
    )
    if not otp_request or otp_request.status != "pending":
        raise generic_error
    if otp_request.expires_at <= now:
        otp_request.status = "expired"
        db.commit()
        raise generic_error

    otp_request.attempts += 1
    if not hmac.compare_digest(otp_request.code_hash, _otp_hash(request_id, code)):
        if otp_request.attempts >= otp_request.max_attempts:
            otp_request.status = "locked"
        db.commit()
        raise generic_error

    otp_request.status = "verified"
    otp_request.verified_at = now
    _transaction_lock(db, f"otp-verify-mobile:{otp_request.mobile}")
    user = db.query(User).filter(User.mobile == otp_request.mobile).first()
    if user is None:
        user = User(
            mobile=otp_request.mobile,
            display_name=f"کاربر {otp_request.mobile[-4:]}",
        )
        bootstrap_mobile = get_bootstrap_super_admin_mobile()
        if bootstrap_mobile and normalize_mobile(bootstrap_mobile) == otp_request.mobile:
            super_admin = db.query(Role).filter(Role.name == "super_admin").one()
            user.roles.append(super_admin)
        db.add(user)
        db.flush()
    if not user.is_active or user.locked_at is not None:
        db.commit()
        raise SecurityError(
            code="ACCOUNT_UNAVAILABLE",
            message="امکان ورود به حساب وجود ندارد.",
            status_code=403,
            errors=[],
        )

    session_started_at = utc_now()
    token = secrets.token_urlsafe(32)
    session_ttl = get_int_setting("AUTH_SESSION_TTL_SECONDS", 28800)
    auth_session = AuthSession(
        user=user,
        token_hash=_token_hash(token),
        created_at=session_started_at,
        expires_at=session_started_at + timedelta(seconds=session_ttl),
    )
    user.last_login_at = session_started_at
    db.add(auth_session)
    db.flush()
    add_audit_log(
        db,
        action="auth.login",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
        session_id=auth_session.id,
    )
    db.commit()
    db.refresh(user)
    return token, session_ttl, user


@dataclass
class AuthContext:
    user: User
    session: AuthSession


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise SecurityError(
            code="AUTH_REQUIRED",
            message="ورود به سامانه الزامی است.",
            status_code=401,
            errors=[],
        )
    now = utc_now()
    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == _token_hash(credentials.credentials))
        .first()
    )
    if (
        not auth_session
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
        or not auth_session.user.is_active
        or auth_session.user.locked_at is not None
    ):
        raise SecurityError(
            code="AUTH_INVALID",
            message="نشست ورود نامعتبر یا منقضی است.",
            status_code=401,
            errors=[],
        )
    return AuthContext(user=auth_session.user, session=auth_session)


def require_permission(permission_code: str):
    def dependency(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if permission_code not in effective_permissions(context.user):
            raise SecurityError(
                code="PERMISSION_DENIED",
                message="دسترسی لازم برای این عملیات وجود ندارد.",
                status_code=403,
                errors=[{"permission": permission_code}],
            )
        return context

    return dependency


def revoke_session(db: Session, context: AuthContext) -> None:
    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.id == context.session.id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    if auth_session.revoked_at is not None:
        return
    auth_session.revoked_at = utc_now()
    add_audit_log(
        db,
        action="auth.logout",
        entity_type="AuthSession",
        entity_id=auth_session.id,
        actor_user_id=context.user.id,
        session_id=auth_session.id,
    )
    db.commit()
