"""Contracts for commercial proposal, follow-up, and final outcome."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.operations import normalize_utc_datetime

FollowUpSlot = Literal["day_0", "day_2", "day_5", "day_7_10"]
FinalOutcomeValue = Literal[
    "contract",
    "ready_on_date",
    "negotiation",
    "rejected",
    "closed",
]


class CommercialProposalUpdate(BaseModel):
    project_count: int = Field(gt=0)
    floor_count: int = Field(gt=0)
    area_sqm: float = Field(gt=0)
    frequency: str = Field(min_length=1, max_length=160)
    period: str = Field(min_length=1, max_length=160)
    user_count: int = Field(gt=0)
    support_scope: str = Field(min_length=2, max_length=10000)
    features: list[str] = Field(min_length=1, max_length=100)
    proposal_file_name: str | None = Field(default=None, max_length=255)
    proposal_file_size: int | None = Field(
        default=None,
        gt=0,
        le=100 * 1024 * 1024,
    )
    proposal_file_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    decision_maker: str = Field(min_length=2, max_length=160)
    follow_up_at: datetime

    model_config = ConfigDict(extra="forbid")

    _normalize_follow_up_at = field_validator("follow_up_at")(normalize_utc_datetime)

    @field_validator("support_scope")
    @classmethod
    def normalize_proposal_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("support_scope must contain a valid proposal text")
        return normalized

    @field_validator("proposal_file_name", mode="before")
    @classmethod
    def normalize_optional_file_name(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value or None

    @field_validator("proposal_file_name")
    @classmethod
    def validate_file_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (
            "/" in value
            or "\\" in value
            or value in {".", ".."}
            or "://" in value
        ):
            raise ValueError("proposal_file_name must be a safe file name, not a path or URL")
        if not value.lower().endswith(".pdf"):
            raise ValueError("proposal_file_name must use the .pdf extension")
        return value

    @field_validator("proposal_file_size", mode="before")
    @classmethod
    def normalize_optional_file_size(cls, value):
        return None if value is None or value == "" or value == 0 else value

    @field_validator("proposal_file_sha256", mode="before")
    @classmethod
    def normalize_sha256(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
        return value or None

    @field_validator("features")
    @classmethod
    def normalize_features(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 160 for value in normalized):
            raise ValueError("features must contain non-empty short names")
        if len(set(normalized)) != len(normalized):
            raise ValueError("features must be unique")
        return normalized

    @model_validator(mode="after")
    def require_complete_file_metadata(self) -> "CommercialProposalUpdate":
        file_metadata = (
            self.proposal_file_name,
            self.proposal_file_size,
            self.proposal_file_sha256,
        )
        if any(value is not None for value in file_metadata) and not all(
            value is not None for value in file_metadata
        ):
            raise ValueError(
                "proposal file name, size, and sha256 must be provided together"
            )
        return self


class CommercialProposalRead(BaseModel):
    id: int
    pilot_id: int
    responsible_user_id: int
    project_count: int
    floor_count: int
    area_sqm: float
    frequency: str
    period: str
    user_count: int
    support_scope: str
    features: list[str]
    proposal_file_name: str | None
    proposal_file_size: int | None
    proposal_file_sha256: str | None
    decision_maker: str
    follow_up_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerFollowUpUpdate(BaseModel):
    obstacle: str = Field(min_length=2, max_length=10000)
    action: str = Field(min_length=2, max_length=10000)
    owner_user_id: int
    due_at: datetime
    result: str = Field(min_length=2, max_length=10000)
    completed_at: datetime

    model_config = ConfigDict(extra="forbid")

    _normalize_due_at = field_validator("due_at")(normalize_utc_datetime)
    _normalize_completed_at = field_validator("completed_at")(normalize_utc_datetime)


class CustomerFollowUpRead(BaseModel):
    id: int
    pilot_id: int
    schedule_slot: FollowUpSlot
    obstacle: str
    action: str
    owner_user_id: int
    due_at: datetime
    result: str
    completed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinalOutcomeUpdate(BaseModel):
    outcome: FinalOutcomeValue
    reason: str | None = Field(default=None, max_length=10000)
    ready_at: datetime | None = None
    success_owner_user_id: int | None = None
    periodic_capture: bool | None = None
    contracted_user_count: int | None = Field(default=None, gt=0)
    first_capture_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("ready_at", "first_capture_at")
    @classmethod
    def normalize_optional_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @model_validator(mode="after")
    def validate_outcome_details(self) -> "FinalOutcomeUpdate":
        if self.outcome == "contract" and not (
            self.success_owner_user_id
            and self.periodic_capture is not None
            and self.contracted_user_count
            and self.first_capture_at
        ):
            raise ValueError(
                "contract requires success owner, periodic capture, users, and first capture"
            )
        if self.outcome == "ready_on_date" and not self.ready_at:
            raise ValueError("ready_at is required for ready_on_date")
        if self.outcome in {"rejected", "closed"} and not (
            self.reason and self.reason.strip()
        ):
            raise ValueError("reason is required for rejected or closed outcomes")
        return self


class FinalOutcomeApprove(BaseModel):
    confirmed: bool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_confirmation(self) -> "FinalOutcomeApprove":
        if not self.confirmed:
            raise ValueError("final outcome approval requires confirmation")
        return self


class FinalOutcomeRead(BaseModel):
    id: int
    pilot_id: int
    responsible_user_id: int
    outcome: FinalOutcomeValue
    reason: str | None
    ready_at: datetime | None
    success_owner_user_id: int | None
    periodic_capture: bool | None
    contracted_user_count: int | None
    first_capture_at: datetime | None
    pilot_manager_approved: bool
    approved_by_user_id: int | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
