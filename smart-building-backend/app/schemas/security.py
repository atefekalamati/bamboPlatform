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
    is_active: bool
    locked_at: datetime | None
    roles: list[RoleSummary]
    permissions: list[str]


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class UserCreate(BaseModel):
    mobile: str
    display_name: str = Field(min_length=2, max_length=120)
    role_ids: list[int] = Field(default_factory=list)
    is_active: bool = True

    _normalize_mobile = field_validator("mobile")(normalize_mobile)


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


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    old_data: dict | None
    new_data: dict | None
    reason: str | None
    ip_address: str | None
    session_id: int | None
    created_at: datetime
