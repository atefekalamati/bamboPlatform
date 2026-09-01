"""API contracts for OTP authentication, users, roles, and permissions."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


def normalize_mobile(value: str) -> str:
    cleaned = re.sub(r"[\s()-]", "", value)
    if cleaned.startswith("0098"):
        cleaned = f"+98{cleaned[4:]}"
    elif cleaned.startswith("09"):
        cleaned = f"+98{cleaned[1:]}"
    elif cleaned.startswith("98") and not cleaned.startswith("+"):
        cleaned = f"+{cleaned}"
    if not re.fullmatch(r"\+[1-9]\d{9,14}", cleaned):
        raise ValueError("mobile must be a valid international number")
    return cleaned


class OtpRequestInput(BaseModel):
    mobile: str

    _normalize_mobile = field_validator("mobile")(normalize_mobile)


class OtpRequestResult(BaseModel):
    request_id: str
    destination_mask: str
    expires_in: int
    retry_after: int
    debug_code: str | None = None


class OtpVerifyInput(BaseModel):
    request_id: str = Field(min_length=36, max_length=36)
    code: str = Field(pattern=r"^\d{6}$")


class PermissionRead(BaseModel):
    id: int
    code: str
    group_name: str
    description: str
    is_sensitive: bool


class RoleSummary(BaseModel):
    id: int
    name: str
    display_name: str


class UserRead(BaseModel):
    id: int
    mobile: str
    display_name: str
    can_edit_own_name: bool
    is_active: bool
    locked_at: datetime | None
    roles: list[RoleSummary]
    permissions: list[str]


class AuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: UserRead


class RefreshTokenInput(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)

    model_config = {"extra": "forbid"}


class UserPreferenceRead(BaseModel):
    language: str
    theme: str
    timezone: str
    calendar: str
    page_size: int
    default_page: str | None
    last_page: str | None
    visible_columns: dict
    column_order: dict
    saved_filters: dict
    notification_preferences: dict
    dashboard_preferences: dict
    updated_at: datetime


class UserPreferencePatch(BaseModel):
    language: str | None = Field(default=None, min_length=2, max_length=16)
    theme: str | None = Field(default=None, pattern="^(light|dark)$")
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    calendar: str | None = Field(default=None, pattern="^(jalali|gregorian)$")
    page_size: int | None = Field(default=None, ge=5, le=200)
    default_page: str | None = Field(default=None, max_length=120)
    last_page: str | None = Field(default=None, max_length=120)
    visible_columns: dict | None = None
    column_order: dict | None = None
    saved_filters: dict | None = None
    notification_preferences: dict | None = None
    dashboard_preferences: dict | None = None


class UserCreate(BaseModel):
    mobile: str
    display_name: str = Field(min_length=2, max_length=120)
    role_ids: list[int] = Field(default_factory=list)
    is_active: bool = True

    _normalize_mobile = field_validator("mobile")(normalize_mobile)


class UserProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    mobile: str | None = None

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("display_name must contain at least 2 characters")
        return normalized

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value) if value is not None else None

    @model_validator(mode="after")
    def require_editable_field(self):
        if not self.model_fields_set.intersection({"display_name", "mobile"}):
            raise ValueError("at least one editable field is required")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("editable fields cannot be null")
        return self

    model_config = {"extra": "forbid"}


class UserOwnNameEditPermissionPatch(BaseModel):
    can_edit_own_name: bool

    model_config = {"extra": "forbid"}


class UserRolesUpdate(BaseModel):
    role_ids: list[int]
    confirmed: bool = False

    @model_validator(mode="after")
    def require_confirmation(self):
        if not self.confirmed:
            raise ValueError("role assignment requires confirmation")
        return self


class UserStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=2, max_length=500)
    confirmed: bool = False

    @model_validator(mode="after")
    def require_confirmation(self):
        if not self.confirmed:
            raise ValueError("account status change requires confirmation")
        return self


class RoleCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    display_name: str = Field(min_length=2, max_length=120)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{2,79}$")
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


class RoleClone(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    display_name: str = Field(min_length=2, max_length=120)


class RoleRead(BaseModel):
    id: int
    name: str
    display_name: str
    is_system: bool
    is_active: bool
    permissions: list[PermissionRead]


class RolePermissionsUpdate(BaseModel):
    permission_codes: list[str]
    confirmed: bool = False


class PermissionGroupRead(BaseModel):
    group_name: str
    permissions: list[PermissionRead]


class EffectivePermissionsRead(BaseModel):
    permissions: list[str]


class AccessPreviewRead(BaseModel):
    roles: list[dict]
    permissions: list[str]
    scopes: list[str]
    menu_access: list[str]
    stage_access: dict[str, list[int]]
    gate_access: dict[str, list[str]]
    operations: list[str]


class AuthBootstrapRead(AccessPreviewRead):
    user: UserRead
    preferences: UserPreferenceRead


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    pilot_id: int | None
    old_data: dict | None
    new_data: dict | None
    reason: str | None
    request_id: str | None
    ip_address: str | None
    user_agent: str | None
    session_id: int | None
    created_at: datetime
