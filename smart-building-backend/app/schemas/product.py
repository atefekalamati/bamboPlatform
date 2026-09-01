"""Contracts for project data, F01/F02, floors, and DWG versions."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.security import normalize_mobile


class OwnerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    decision_maker_name: str = Field(min_length=2, max_length=120)
    decision_maker_position: str = Field(min_length=2, max_length=120)
    primary_mobile: str

    _normalize_mobile = field_validator("primary_mobile")(normalize_mobile)


class OwnerRead(OwnerCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    total_floors: int = Field(ge=1, le=500)
    address: str = Field(min_length=5, max_length=500)
    progress_stage: str = Field(min_length=2, max_length=160)
    customer_need: str = Field(min_length=2, max_length=4000)
    expected_value: str = Field(min_length=2, max_length=4000)


class ProjectRead(ProjectCreate):
    id: int
    system_name: str
    display_name: str
    owner: OwnerRead

    model_config = ConfigDict(from_attributes=True)


class FormF01Update(BaseModel):
    project_active: bool
    imaging_value: bool
    remote_viewing_need: bool
    access_possible: bool
    dwg_available: bool
    continued_capacity: bool
    not_demo_only: bool
    introduction_completed: bool
    imaging_accepted: bool
    dwg_accepted: bool
    feedback_accepted: bool
    coordinator_name: str | None = Field(default=None, max_length=120)
    coordinator_mobile: str | None = None
    limitation: str | None = Field(default=None, max_length=4000)
    result: Literal["approved", "complete_information", "rejected", "referred"]
    referral_deadline: date | None = None
    sales_user_id: int | None = None
    pilot_manager_user_id: int | None = None
    referred_at: datetime | None = None

    @field_validator("coordinator_mobile")
    @classmethod
    def normalize_optional_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value) if value else None


class FormF01Read(FormF01Update):
    id: int
    pilot_id: int
    case_owner_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormF02Update(BaseModel):
    information_package: str | None = Field(default=None, max_length=4000)
    contacts_summary: str | None = Field(default=None, max_length=4000)
    progress_status: str | None = Field(default=None, max_length=160)
    limitation: str | None = Field(default=None, max_length=4000)
    main_project_registered: bool = False
    floor_order_confirmed: bool = False
    typical_floors_identified: bool = False
    plan_connections_registered: bool = False
    start_point_registered: bool = False
    expert_access_tested: bool = False
    main_app_display_tested: bool = False
    ready_for_capture: bool = False
    ambiguity: str | None = Field(default=None, max_length=4000)
    referred_at: datetime | None = None
    configured_by_user_id: int | None = None
    controlled_by_user_id: int | None = None
    configured_at: datetime | None = None


class FormF02Read(FormF02Update):
    id: int
    pilot_id: int
    responsible_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FloorCreate(BaseModel):
    code: str = Field(pattern=r"^F\d{2,3}$")
    name: str = Field(min_length=1, max_length=120)
    level_order: int = Field(ge=-20, le=500)
    floor_type: Literal["typical", "non_typical"] = "non_typical"

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class FloorDwgReferenceUpdate(BaseModel):
    confirmed: bool


class FloorRead(FloorCreate):
    id: int
    project_id: int
    has_dwg: bool = False
    has_valid_dwg: bool = False
    latest_dwg_version: int | None = None
    dwg_reference_confirmed: bool = False
    dwg_reference_confirmed_at: datetime | None = None
    dwg_reference_confirmed_by_user_id: int | None = None


class DwgVersionRead(BaseModel):
    id: int
    version: int
    original_filename: str
    standardized_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    dwg_signature: str
    is_readable: bool
    uploaded_by_user_id: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------- bulk stage 3
#
# Stage 3 registers every floor of a building and its drawing. Doing that one
# floor at a time meant a request per floor, the same file stored repeatedly,
# and a run that could stop halfway. These contracts describe the grouped
# operations; the single-floor endpoints they complement are unchanged.


class FloorBulkCreate(BaseModel):
    floors: list[FloorCreate] = Field(min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_duplicates_within_the_request(self) -> "FloorBulkCreate":
        codes = [floor.code for floor in self.floors]
        orders = [floor.level_order for floor in self.floors]
        if len(set(codes)) != len(codes):
            raise ValueError("floor codes must be unique within the request")
        if len(set(orders)) != len(orders):
            raise ValueError("level_order values must be unique within the request")
        return self


class FloorBulkCreateResult(BaseModel):
    pilot_id: int
    total: int
    created: int
    floors: list[FloorRead]


class FloorDwgReferenceBulkUpdate(BaseModel):
    floor_ids: list[int] = Field(min_length=1, max_length=200)
    confirmed: bool

    model_config = ConfigDict(extra="forbid")

    @field_validator("floor_ids")
    @classmethod
    def reject_repeated_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("floor_ids must not repeat")
        return value


class FloorDwgReferenceBulkItem(BaseModel):
    id: int
    dwg_reference_confirmed: bool
    has_valid_dwg: bool


class FloorDwgReferenceBulkResult(BaseModel):
    pilot_id: int
    total: int
    updated: int
    floors: list[FloorDwgReferenceBulkItem]


class SharedDwgFileSummary(BaseModel):
    """The one stored file, described once rather than per floor."""

    original_filename: str
    standardized_filename: str
    storage_key: str
    mime_type: str
    size_bytes: int
    sha256: str


class SharedDwgVersionItem(BaseModel):
    floor_id: int
    floor_code: str
    version_id: int
    version: int
    has_valid_dwg: bool


class SharedDwgUploadResult(BaseModel):
    pilot_id: int
    file: SharedDwgFileSummary
    total: int
    uploaded: int
    versions: list[SharedDwgVersionItem]
