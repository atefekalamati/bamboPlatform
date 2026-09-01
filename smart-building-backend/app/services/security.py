"""OTP authentication, session, permission, and audit services."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
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
from app.providers.sms import get_sms_provider
from app.rbac import PERMISSIONS, SYSTEM_ROLES
from app.schemas.security import normalize_mobile
from app.schemas.security import UserProfilePatch

bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def mask_mobile(mobile: str) -> str:
    return f"{mobile[:4]}***{mobile[-4:]}"


def update_user_profile(
    db: Session,
    *,
    actor: User,
    target: User,
    payload: UserProfilePatch,
    session_id: int | None,
) -> User:
    changes = payload.model_dump(exclude_unset=True)
    old_data: dict[str, object] = {}
    new_data: dict[str, object] = {}
    changed_fields: list[str] = []
    if "display_name" in changes and changes["display_name"] != target.display_name:
        old_data["display_name"] = target.display_name
        new_data["display_name"] = changes["display_name"]
        target.display_name = changes["display_name"]
        changed_fields.append("display_name")
    if "mobile" in changes and changes["mobile"] != target.mobile:
        duplicate = db.query(User.id).filter(User.mobile == changes["mobile"], User.id != target.id).first()
        if duplicate:
            raise SecurityError("USER_MOBILE_ALREADY_EXISTS", "این شماره تلفن قبلاً ثبت شده است.", 409, [{"field": "mobile", "reason": "duplicate"}])
        old_mobile = target.mobile
        old_data["mobile"] = mask_mobile(old_mobile)
        new_data["mobile"] = mask_mobile(changes["mobile"])
        target.mobile = changes["mobile"]
        changed_fields.append("mobile")
        db.query(OtpRequest).filter(
            OtpRequest.mobile == old_mobile,
            OtpRequest.status == "pending",
        ).update({OtpRequest.status: "invalidated"}, synchronize_session=False)
    if not changed_fields:
        return target
    add_audit_log(
        db,
        action="users.profile_updated",
        entity_type="User",
        entity_id=target.id,
        actor_user_id=actor.id,
        old_data=old_data,
        new_data=new_data | {"changed_fields": changed_fields},
        session_id=session_id,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SecurityError("USER_MOBILE_ALREADY_EXISTS", "این شماره تلفن قبلاً ثبت شده است.", 409, [{"field": "mobile", "reason": "duplicate"}]) from exc
    db.refresh(target)
    return target


def update_own_name_edit_permission(
    db: Session,
    *,
    actor: User,
    target: User,
    allowed: bool,
    session_id: int | None,
) -> User:
    previous = target.can_edit_own_name
    if previous == allowed:
        return target
    target.can_edit_own_name = allowed
    add_audit_log(
        db,
        action="users.own_name_edit_permission_updated",
        entity_type="User",
        entity_id=target.id,
        actor_user_id=actor.id,
        old_data={"can_edit_own_name": previous},
        new_data={"can_edit_own_name": allowed},
        session_id=session_id,
    )
    db.commit()
    db.refresh(target)
    return target


def _otp_hash(public_id: str, code: str) -> str:
    payload = f"{public_id}:{code}".encode()
    return hmac.new(get_auth_secret().encode(), payload, hashlib.sha256).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_token() -> str:
    return secrets.token_urlsafe(48)


def access_token_ttl_seconds() -> int:
    return get_int_setting("AUTH_ACCESS_TTL_SECONDS", 900)


def refresh_token_ttl_seconds() -> int:
    return get_int_setting("AUTH_REFRESH_TTL_SECONDS", 60 * 60 * 24 * 30)


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
        else:
            # System roles are code-owned contracts. Keep persisted assignments in
            # sync after upgrades; custom roles remain untouched.
            role.permissions = [permissions_by_code[code] for code in permission_codes]
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
    delivery = get_sms_provider().send_otp(
        mobile=mobile,
        otp_code=code,
    )

    otp_request = OtpRequest(
        public_id=public_id,
        mobile=mobile,
        code_hash=_otp_hash(public_id, code),
        provider_status=delivery.provider_status,
        provider_message_id=delivery.provider_message_id,
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
    if not delivery.accepted:
        otp_request.status = "failed"
        db.commit()
        raise SecurityError(
            code="OTP_PROVIDER_UNAVAILABLE",
            message="سرویس ارسال کد موقتاً در دسترس نیست.",
            status_code=503,
            errors=[],
        )
    return OtpDispatch(
        request=otp_request,
        debug_code=code if get_app_env() in {"development", "test"} else None,
        retry_after=cooldown,
    )


def verify_otp(
    db: Session,
    request_id: str,
    code: str,
    ip_address: str | None,
    user_agent: str | None = None,
) -> tuple[str, str, int, int, User]:
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
    token = _new_token()
    refresh_token = _new_token()
    session_ttl = access_token_ttl_seconds()
    refresh_ttl = refresh_token_ttl_seconds()
    auth_session = AuthSession(
        user=user,
        token_hash=_token_hash(token),
        refresh_token_hash=_token_hash(refresh_token),
        created_at=session_started_at,
        expires_at=session_started_at + timedelta(seconds=session_ttl),
        refresh_expires_at=session_started_at + timedelta(seconds=refresh_ttl),
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
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
    return token, refresh_token, session_ttl, refresh_ttl, user


def refresh_session(
    db: Session,
    refresh_token: str,
    *,
    ip_address: str | None,
    user_agent: str | None = None,
) -> tuple[str, str, int, int, User]:
    now = utc_now()
    refresh_hash = _token_hash(refresh_token)
    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.refresh_token_hash == refresh_hash)
        .with_for_update()
        .first()
    )
    if auth_session is None:
        reused_session = (
            db.query(AuthSession)
            .filter(AuthSession.previous_refresh_token_hash == refresh_hash)
            .with_for_update()
            .first()
        )
        if reused_session is not None:
            db.query(AuthSession).filter(
                AuthSession.user_id == reused_session.user_id,
                AuthSession.revoked_at.is_(None),
            ).update({AuthSession.revoked_at: now}, synchronize_session=False)
            add_audit_log(
                db,
                action="auth.refresh_reuse_detected",
                entity_type="AuthSession",
                entity_id=reused_session.id,
                actor_user_id=reused_session.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=reused_session.id,
            )
            db.commit()
        raise SecurityError(
            code=(
                "REFRESH_TOKEN_REVOKED"
                if reused_session is not None
                else "REFRESH_TOKEN_INVALID"
            ),
            message="Refresh Token نامعتبر یا باطل‌شده است.",
            status_code=401,
            errors=[],
        )
    if auth_session.revoked_at is not None:
        raise SecurityError(
            code="REFRESH_TOKEN_REVOKED",
            message="Refresh Token باطل شده است.",
            status_code=401,
            errors=[],
        )
    if (
        auth_session.refresh_expires_at is None
        or auth_session.refresh_expires_at <= now
    ):
        raise SecurityError(
            code="REFRESH_TOKEN_EXPIRED",
            message="اعتبار Refresh Token به پایان رسیده است.",
            status_code=401,
            errors=[],
        )
    if not auth_session.user.is_active or auth_session.user.locked_at is not None:
        raise SecurityError(
            code="SESSION_REVOKED",
            message="نشست کاربر دیگر معتبر نیست.",
            status_code=401,
            errors=[],
        )

    access_token = _new_token()
    new_refresh_token = _new_token()
    access_ttl = access_token_ttl_seconds()
    refresh_ttl = refresh_token_ttl_seconds()
    auth_session.previous_refresh_token_hash = auth_session.refresh_token_hash
    auth_session.refresh_token_hash = _token_hash(new_refresh_token)
    auth_session.token_hash = _token_hash(access_token)
    auth_session.expires_at = now + timedelta(seconds=access_ttl)
    auth_session.refresh_expires_at = now + timedelta(seconds=refresh_ttl)
    auth_session.last_used_at = now
    auth_session.refresh_used_at = now
    auth_session.ip_address = ip_address
    auth_session.user_agent = user_agent[:500] if user_agent else None
    add_audit_log(
        db,
        action="auth.refresh",
        entity_type="AuthSession",
        entity_id=auth_session.id,
        actor_user_id=auth_session.user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=auth_session.id,
    )
    db.commit()
    db.refresh(auth_session.user)
    return access_token, new_refresh_token, access_ttl, refresh_ttl, auth_session.user


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
            code="ACCESS_TOKEN_INVALID",
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
    if auth_session is None:
        raise SecurityError(
            code="ACCESS_TOKEN_INVALID",
            message="Access Token نامعتبر است.",
            status_code=401,
            errors=[],
        )
    if auth_session.revoked_at is not None:
        raise SecurityError(
            code="SESSION_REVOKED",
            message="نشست ورود باطل شده است.",
            status_code=401,
            errors=[],
        )
    if auth_session.expires_at <= now:
        raise SecurityError(
            code="ACCESS_TOKEN_EXPIRED",
            message="اعتبار Access Token به پایان رسیده است.",
            status_code=401,
            errors=[],
        )
    if not auth_session.user.is_active or auth_session.user.locked_at is not None:
        raise SecurityError(
            code="SESSION_REVOKED",
            message="نشست کاربر دیگر معتبر نیست.",
            status_code=401,
            errors=[],
        )
    auth_session.last_used_at = now
    db.commit()
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


def revoke_session(db: Session, context: AuthContext, refresh_token: str | None = None) -> None:
    refresh_hash = _token_hash(refresh_token) if refresh_token else None
    auth_session = (
        db.query(AuthSession)
        .filter(
            AuthSession.id == context.session.id,
            *((AuthSession.refresh_token_hash == refresh_hash,) if refresh_hash else ()),
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if auth_session is None:
        raise SecurityError(
            code="REFRESH_TOKEN_INVALID",
            message="Refresh Token با نشست جاری تطابق ندارد.",
            status_code=401,
            errors=[],
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


def logout_sessions(
    db: Session,
    *,
    access_token: str | None,
    refresh_token: str | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Idempotently revoke sessions identified by either presented token.

    Unknown, already rotated, or already revoked tokens intentionally return
    success so logout cannot be used as a token/session existence oracle.
    """
    token_hashes = []
    if access_token:
        token_hashes.append(AuthSession.token_hash == _token_hash(access_token))
    if refresh_token:
        refresh_hash = _token_hash(refresh_token)
        token_hashes.extend(
            (
                AuthSession.refresh_token_hash == refresh_hash,
                AuthSession.previous_refresh_token_hash == refresh_hash,
            )
        )
    if not token_hashes:
        return

    now = utc_now()
    sessions = (
        db.query(AuthSession)
        .filter(or_(*token_hashes))
        .with_for_update()
        .all()
    )
    changed = False
    for auth_session in sessions:
        if auth_session.revoked_at is not None:
            continue
        auth_session.revoked_at = now
        add_audit_log(
            db,
            action="auth.logout",
            entity_type="AuthSession",
            entity_id=auth_session.id,
            actor_user_id=auth_session.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=auth_session.id,
        )
        changed = True
    if changed:
        db.commit()
