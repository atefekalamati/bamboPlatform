"""OTP authentication and RBAC administration API."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.models import AuditLog, Permission, Role, User, UserPreference
from app.rbac import ALL_PERMISSION_CODES
from app.schemas.security import (
    AuditLogRead,
    AuthToken,
    OtpRequestInput,
    OtpRequestResult,
    OtpVerifyInput,
    PermissionRead,
    RoleCreate,
    RolePermissionsUpdate,
    RoleRead,
    RoleSummary,
    UserCreate,
    UserPreferencePatch,
    UserPreferenceRead,
    UserRead,
    UserRolesUpdate,
    UserStatusUpdate,
)
from app.services.security import (
    AuthContext,
    add_audit_log,
    effective_permissions,
    get_auth_context,
    mask_mobile,
    request_otp,
    require_permission,
    revoke_session,
    utc_now,
    verify_otp,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        mobile=mask_mobile(user.mobile),
        display_name=user.display_name,
        is_active=user.is_active,
        locked_at=user.locked_at,
        roles=[
            RoleSummary(id=role.id, name=role.name, display_name=role.display_name)
            for role in sorted(user.roles, key=lambda item: item.id)
        ],
        permissions=sorted(effective_permissions(user)),
    )


def _preference_read(preference: UserPreference) -> UserPreferenceRead:
    return UserPreferenceRead(
        language=preference.language,
        theme=preference.theme,
        timezone=preference.timezone,
        calendar=preference.calendar,
        page_size=preference.page_size,
        default_page=preference.default_page,
        last_page=preference.last_page,
        visible_columns=preference.visible_columns,
        column_order=preference.column_order,
        saved_filters=preference.saved_filters,
        notification_preferences=preference.notification_preferences,
        dashboard_preferences=preference.dashboard_preferences,
        updated_at=preference.updated_at,
    )


def _get_or_create_preferences(db: Session, user: User) -> UserPreference:
    preference = user.preferences
    if preference is None:
        preference = UserPreference(user=user)
        db.add(preference)
        db.flush()
    return preference


def role_read(role: Role) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        is_system=role.is_system,
        is_active=role.is_active,
        permissions=[
            PermissionRead(
                id=permission.id,
                code=permission.code,
                group_name=permission.group_name,
                description=permission.description,
                is_sensitive=permission.is_sensitive,
            )
            for permission in sorted(role.permissions, key=lambda item: item.code)
        ],
    )


@auth_router.post("/otp/request", response_model=OtpRequestResult)
def otp_request_endpoint(
    payload: OtpRequestInput,
    request: Request,
    db: Session = Depends(get_db),
) -> OtpRequestResult:
    dispatch = request_otp(db, payload.mobile, client_ip(request))
    return OtpRequestResult(
        request_id=dispatch.request.public_id,
        destination_mask=mask_mobile(dispatch.request.mobile),
        expires_in=int((dispatch.request.expires_at - dispatch.request.created_at).total_seconds()),
        retry_after=dispatch.retry_after,
        debug_code=dispatch.debug_code,
    )


@auth_router.post("/otp/verify", response_model=AuthToken)
def otp_verify_endpoint(
    payload: OtpVerifyInput,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthToken:
    token, expires_in, user = verify_otp(db, payload.request_id, payload.code, client_ip(request))
    return AuthToken(access_token=token, expires_in=expires_in, user=user_read(user))


@auth_router.get("/me", response_model=UserRead)
def me(context: AuthContext = Depends(get_auth_context)) -> UserRead:
    return user_read(context.user)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> None:
    revoke_session(db, context)


@auth_router.get("/preferences", response_model=UserPreferenceRead)
def get_preferences(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> UserPreferenceRead:
    preference = _get_or_create_preferences(db, context.user)
    db.commit()
    db.refresh(preference)
    return _preference_read(preference)


@auth_router.patch("/preferences", response_model=UserPreferenceRead)
def patch_preferences(
    payload: UserPreferencePatch,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> UserPreferenceRead:
    preference = _get_or_create_preferences(db, context.user)
    changes = payload.model_dump(exclude_unset=True)
    old_data = {field: getattr(preference, field) for field in changes}
    for field, value in changes.items():
        setattr(preference, field, value)
    add_audit_log(
        db,
        action="users.preferences_updated",
        entity_type="UserPreference",
        entity_id=preference.id,
        actor_user_id=context.user.id,
        old_data=old_data,
        new_data=changes,
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(preference)
    return _preference_read(preference)


@users_router.get("", response_model=list[UserRead])
def list_users(
    _: AuthContext = Depends(require_permission("users.read")),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    return [user_read(user) for user in db.query(User).order_by(User.id).all()]


@users_router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    context: AuthContext = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> UserRead:
    if db.query(User).filter(User.mobile == payload.mobile).first():
        raise SecurityError(
            code="USER_ALREADY_EXISTS",
            message="کاربر با این شماره از قبل وجود دارد.",
            status_code=409,
            errors=[],
        )
    roles = db.query(Role).filter(Role.id.in_(payload.role_ids), Role.is_active.is_(True)).all()
    if len(roles) != len(set(payload.role_ids)):
        raise SecurityError(
            code="ROLE_NOT_FOUND",
            message="یک یا چند نقش معتبر نیست.",
            status_code=422,
            errors=[],
        )
    _ensure_role_assignment_allowed(context.user, roles)
    user = User(
        mobile=payload.mobile,
        display_name=payload.display_name,
        is_active=payload.is_active,
        roles=roles,
    )
    db.add(user)
    db.flush()
    add_audit_log(
        db,
        action="users.created",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=context.user.id,
        new_data={"mobile": mask_mobile(user.mobile), "role_ids": payload.role_ids},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(user)
    return user_read(user)


def _ensure_not_removing_last_super_admin(db: Session, user: User, keeps_super_admin: bool) -> None:
    has_super_admin = any(role.name == "super_admin" for role in user.roles)
    if not has_super_admin or keeps_super_admin:
        return
    active_count = (
        db.query(User)
        .join(User.roles)
        .filter(
            Role.name == "super_admin",
            User.is_active.is_(True),
            User.locked_at.is_(None),
        )
        .count()
    )
    if active_count <= 1:
        raise SecurityError(
            code="LAST_SUPER_ADMIN",
            message="آخرین مدیر کل فعال را نمی‌توان غیرفعال یا بدون نقش کرد.",
            status_code=409,
            errors=[],
        )


def _is_super_admin(user: User) -> bool:
    return any(role.name == "super_admin" and role.is_active for role in user.roles)


def _ensure_role_assignment_allowed(actor: User, roles: list[Role]) -> None:
    if _is_super_admin(actor):
        return
    actor_permissions = effective_permissions(actor)
    delegated_permissions = {
        permission.code for role in roles for permission in role.permissions if role.is_active
    }
    if any(role.name == "super_admin" for role in roles) or not delegated_permissions.issubset(
        actor_permissions
    ):
        raise SecurityError(
            code="PRIVILEGE_ESCALATION_DENIED",
            message="واگذاری دسترسی فراتر از سطح کاربر مجاز نیست.",
            status_code=403,
            errors=[],
        )


@users_router.put("/{user_id}/roles", response_model=UserRead)
def update_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    context: AuthContext = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise SecurityError("USER_NOT_FOUND", "کاربر پیدا نشد.", 404, [])
    if _is_super_admin(user) and not _is_super_admin(context.user):
        raise SecurityError(
            "PRIVILEGE_ESCALATION_DENIED",
            "مدیریت نقش مدیر کل فقط توسط مدیر کل مجاز است.",
            403,
            [],
        )
    roles = db.query(Role).filter(Role.id.in_(payload.role_ids), Role.is_active.is_(True)).all()
    if len(roles) != len(set(payload.role_ids)):
        raise SecurityError("ROLE_NOT_FOUND", "یک یا چند نقش معتبر نیست.", 422, [])
    _ensure_role_assignment_allowed(context.user, roles)
    _ensure_not_removing_last_super_admin(
        db,
        user,
        keeps_super_admin=any(role.name == "super_admin" for role in roles),
    )
    old_role_ids = [role.id for role in user.roles]
    user.roles = roles
    add_audit_log(
        db,
        action="users.roles_updated",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=context.user.id,
        old_data={"role_ids": old_role_ids},
        new_data={"role_ids": payload.role_ids},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(user)
    return user_read(user)


@users_router.patch("/{user_id}/status", response_model=UserRead)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    context: AuthContext = Depends(require_permission("users.manage")),
    db: Session = Depends(get_db),
) -> UserRead:
    user = db.get(User, user_id)
    if not user:
        raise SecurityError("USER_NOT_FOUND", "کاربر پیدا نشد.", 404, [])
    if _is_super_admin(user) and not _is_super_admin(context.user):
        raise SecurityError(
            "PRIVILEGE_ESCALATION_DENIED",
            "مدیریت حساب مدیر کل فقط توسط مدیر کل مجاز است.",
            403,
            [],
        )
    if not payload.is_active:
        _ensure_not_removing_last_super_admin(db, user, keeps_super_admin=False)
    old_active = user.is_active
    user.is_active = payload.is_active
    user.locked_at = None if payload.is_active else utc_now()
    add_audit_log(
        db,
        action="users.status_updated",
        entity_type="User",
        entity_id=user.id,
        actor_user_id=context.user.id,
        old_data={"is_active": old_active},
        new_data={"is_active": user.is_active},
        reason=payload.reason,
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(user)
    return user_read(user)


@roles_router.get("", response_model=list[RoleRead])
def list_roles(
    _: AuthContext = Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
) -> list[RoleRead]:
    return [role_read(role) for role in db.query(Role).order_by(Role.id).all()]


@roles_router.get("/permissions", response_model=list[PermissionRead])
def list_permissions(
    _: AuthContext = Depends(require_permission("roles.read")),
    db: Session = Depends(get_db),
) -> list[Permission]:
    return db.query(Permission).order_by(Permission.group_name, Permission.code).all()


@roles_router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    context: AuthContext = Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
) -> RoleRead:
    if db.query(Role).filter(Role.name == payload.name).first():
        raise SecurityError("ROLE_ALREADY_EXISTS", "این نقش از قبل وجود دارد.", 409, [])
    role = Role(name=payload.name, display_name=payload.display_name)
    db.add(role)
    db.flush()
    add_audit_log(
        db,
        action="roles.created",
        entity_type="Role",
        entity_id=role.id,
        actor_user_id=context.user.id,
        new_data={"name": role.name},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(role)
    return role_read(role)


@roles_router.put("/{role_id}/permissions", response_model=RoleRead)
def update_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    context: AuthContext = Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
) -> RoleRead:
    role = db.get(Role, role_id)
    if not role:
        raise SecurityError("ROLE_NOT_FOUND", "نقش پیدا نشد.", 404, [])
    requested = set(payload.permission_codes)
    if not requested.issubset(ALL_PERMISSION_CODES):
        raise SecurityError(
            "PERMISSION_NOT_FOUND",
            "یک یا چند Permission معتبر نیست.",
            422,
            [{"permission": code} for code in sorted(requested - ALL_PERMISSION_CODES)],
        )
    if role.name == "super_admin" and requested != ALL_PERMISSION_CODES:
        raise SecurityError(
            "SUPER_ADMIN_PERMISSIONS_REQUIRED",
            "نقش مدیر کل باید همه دسترسی‌ها را حفظ کند.",
            409,
            [],
        )
    if not _is_super_admin(context.user) and not requested.issubset(
        effective_permissions(context.user)
    ):
        raise SecurityError(
            "PRIVILEGE_ESCALATION_DENIED",
            "واگذاری Permission فراتر از سطح کاربر مجاز نیست.",
            403,
            [],
        )
    old_codes = {permission.code for permission in role.permissions}
    changed_codes = old_codes ^ requested
    sensitive_changed = (
        db.query(Permission)
        .filter(Permission.code.in_(changed_codes), Permission.is_sensitive.is_(True))
        .count()
        > 0
    )
    if sensitive_changed and not payload.confirmed:
        raise SecurityError(
            "CONFIRMATION_REQUIRED",
            "تغییر Permission حساس نیازمند تأیید است.",
            422,
            [],
        )
    role.permissions = db.query(Permission).filter(Permission.code.in_(requested)).all()
    add_audit_log(
        db,
        action="roles.permissions_updated",
        entity_type="Role",
        entity_id=role.id,
        actor_user_id=context.user.id,
        old_data={"permission_codes": sorted(old_codes)},
        new_data={"permission_codes": sorted(requested)},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(role)
    return role_read(role)


@roles_router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    context: AuthContext = Depends(require_permission("roles.manage")),
    db: Session = Depends(get_db),
) -> None:
    role = db.get(Role, role_id)
    if not role:
        raise SecurityError("ROLE_NOT_FOUND", "نقش پیدا نشد.", 404, [])
    if role.is_system:
        raise SecurityError(
            "SYSTEM_ROLE_DELETE_DENIED",
            "نقش سیستمی قابل حذف نیست.",
            409,
            [],
        )
    if role.users:
        raise SecurityError(
            "ROLE_IN_USE",
            "این نقش به کاربر اختصاص داده شده و تا زمان حذف انتساب‌ها قابل حذف نیست.",
            409,
            [{"user_id": user.id} for user in role.users],
        )

    role_data = {
        "name": role.name,
        "display_name": role.display_name,
        "permission_codes": sorted(permission.code for permission in role.permissions),
    }
    add_audit_log(
        db,
        action="roles.deleted",
        entity_type="Role",
        entity_id=role.id,
        actor_user_id=context.user.id,
        old_data=role_data,
        session_id=context.session.id,
    )
    role.permissions.clear()
    db.delete(role)
    db.commit()


@audit_router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=200, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, min_length=1, max_length=120),
    entity_type: str | None = Query(default=None, min_length=1, max_length=80),
    entity_id: str | None = Query(default=None, min_length=1, max_length=80),
    actor_user_id: int | None = Query(default=None, ge=1),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    _: AuthContext = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    def normalize_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise SecurityError(
                "AUDIT_TIMEZONE_REQUIRED",
                "زمان فیلتر Audit باید شامل منطقه زمانی باشد.",
                422,
                [],
            )
        return value.astimezone(UTC).replace(tzinfo=None)

    normalized_from = normalize_utc(created_from)
    normalized_to = normalize_utc(created_to)
    if normalized_from and normalized_to and normalized_from > normalized_to:
        raise SecurityError(
            "AUDIT_DATE_RANGE_INVALID",
            "ابتدای بازه Audit نباید بعد از انتهای آن باشد.",
            422,
            [],
        )

    query = db.query(AuditLog)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
        query = query.filter(AuditLog.actor_user_id == actor_user_id)
    if normalized_from is not None:
        query = query.filter(AuditLog.created_at >= normalized_from)
    if normalized_to is not None:
        query = query.filter(AuditLog.created_at <= normalized_to)

    return query.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
