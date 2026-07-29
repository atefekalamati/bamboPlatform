"""Contracts for external status, F04, evidence checks, and F05 incidents."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.operations import normalize_utc_datetime
from app.schemas.security import normalize_mobile

PlatformStatus = Literal["available", "degraded", "down", "unknown"]
EvidenceStatus = Literal["checked", "mismatch", "unavailable", "not_checked"]
IncidentSeverity = Literal["normal", "important", "critical"]
IncidentType = Literal[
    "safety",
    "equipment",
    "dwg",
    "main_platform",
    "access",
    "customer",
    "process",
]
IncidentStatus = Literal["open", "contained", "resolved", "closed"]
IssueRoute = Literal[
    "support",
    "technical",
    "operations",
    "training",
    "product",
    "sales",
]
IssueCategory = Literal[
    "access",
    "platform",
    "coverage_quality",
    "training",
    "capability",
    "continuation",
]

EVIDENCE_CAPABILITIES = {
    "actual_progress",
    "delay_amount",
    "latest_visit",
    "planned_vs_actual_chart",
    "progress_stage",
    "area",
    "estimated_cost",
    "spent_cost",
    "manager_audio_report",
    "project_summary",
    "this_week_report",
    "next_week_plan",
    "owner_actions",
    "field_messages_notes",
}
CUSTOMER_SUCCESS_EVIDENCE_CAPABILITIES = {
    "project_summary",
    "this_week_report",
    "next_week_plan",
    "owner_actions",
    "field_messages_notes",
}


class ExternalPlatformUpdate(BaseModel):
    project_reference: str | None = Field(default=None, max_length=160)
    platform_status: PlatformStatus
    processing_started: bool
    route_detected: bool
    plan_connected: bool
    tour_ready: bool
    captures_menu_checked: bool
    latest_capture_checked: bool
    last_visit_checked: bool
    reason: str | None = Field(default=None, max_length=4000)
    checked_at: datetime

    model_config = ConfigDict(extra="forbid")

    _normalize_checked_at = field_validator("checked_at")(normalize_utc_datetime)

    @field_validator("project_reference")
    @classmethod
    def reject_project_url(cls, value: str | None) -> str | None:
        if value and ("http://" in value.lower() or "https://" in value.lower()):
            raise ValueError("project_reference must be an identifier, not a URL")
        return value.strip() if value else None

    @model_validator(mode="after")
    def require_status_reason(self) -> "ExternalPlatformUpdate":
        if self.platform_status != "available" and not self.reason:
            raise ValueError("reason is required when the external platform is not available")
        return self


class ExternalPlatformRead(BaseModel):
    id: int
    pilot_id: int
    project_reference: str | None
    platform_status: PlatformStatus
    processing_started: bool
    route_detected: bool
    plan_connected: bool
    tour_ready: bool
    captures_menu_checked: bool
    latest_capture_checked: bool
    last_visit_checked: bool
    reason: str | None
    checked_by_user_id: int
    checked_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormF04Patch(BaseModel):
    owner_logged_in: bool | None = None
    project_opened: bool | None = None
    main_tour_viewed: bool | None = None
    training_completed: bool | None = None
    viewing_result: str | None = Field(default=None, max_length=4000)
    issue_description: str | None = Field(default=None, max_length=4000)
    issue_category: IssueCategory | None = None
    issue_route: IssueRoute | None = None
    issue_owner_user_id: int | None = None
    issue_due_at: datetime | None = None
    first_follow_up_at: datetime | None = None
    second_follow_up_at: datetime | None = None
    useful: bool | None = None
    coverage_score: int | None = Field(default=None, ge=1, le=10)
    quality_score: int | None = Field(default=None, ge=1, le=10)
    most_useful_part: str | None = Field(default=None, max_length=4000)
    missing_part: str | None = Field(default=None, max_length=4000)
    other_users: str | None = Field(default=None, max_length=4000)
    more_training_needed: bool | None = None
    satisfaction_score: int | None = Field(default=None, ge=1, le=10)
    continuation_interest: bool | None = None
    proposal_ready: bool | None = None
    realized_value: str | None = Field(default=None, max_length=4000)
    purchase_blocker: str | None = Field(default=None, max_length=4000)
    project_count: int | None = Field(default=None, ge=0, le=100000)
    usage_frequency: str | None = Field(default=None, max_length=160)
    user_count: int | None = Field(default=None, ge=0, le=100000)
    decision_maker: str | None = Field(default=None, max_length=160)
    next_action: str | None = Field(default=None, max_length=4000)
    final_result: str | None = Field(default=None, max_length=160)
    final_reason: str | None = Field(default=None, max_length=4000)
    customer_success_user_id: int | None = None
    sales_user_id: int | None = None
    pilot_manager_user_id: int | None = None
    login_trained: bool | None = None
    project_trained: bool | None = None
    floor_trained: bool | None = None
    plan_trained: bool | None = None
    tour_trained: bool | None = None
    navigation_trained: bool | None = None
    support_trained: bool | None = None
    independent_use_confirmed: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("issue_due_at", "first_follow_up_at", "second_follow_up_at")
    @classmethod
    def normalize_optional_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @model_validator(mode="after")
    def require_changes(self) -> "FormF04Patch":
        if not self.model_fields_set:
            raise ValueError("at least one F04 field must change")
        return self


class FormF04Read(BaseModel):
    id: int
    pilot_id: int
    responsible_user_id: int
    owner_logged_in: bool
    project_opened: bool
    main_tour_viewed: bool
    training_completed: bool
    viewing_result: str | None
    issue_description: str | None
    issue_category: IssueCategory | None
    issue_route: IssueRoute | None
    issue_owner_user_id: int | None
    issue_due_at: datetime | None
    first_follow_up_at: datetime | None
    second_follow_up_at: datetime | None
    useful: bool | None
    coverage_score: int | None
    quality_score: int | None
    most_useful_part: str | None
    missing_part: str | None
    other_users: str | None
    more_training_needed: bool | None
    satisfaction_score: int | None
    continuation_interest: bool | None
    proposal_ready: bool | None
    realized_value: str | None
    purchase_blocker: str | None
    project_count: int | None
    usage_frequency: str | None
    user_count: int | None
    decision_maker: str | None
    next_action: str | None
    final_result: str | None
    final_reason: str | None
    customer_success_user_id: int | None
    sales_user_id: int | None
    pilot_manager_user_id: int | None
    login_trained: bool
    project_trained: bool
    floor_trained: bool
    plan_trained: bool
    tour_trained: bool
    navigation_trained: bool
    support_trained: bool
    independent_use_confirmed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalEvidenceUpdate(BaseModel):
    status: EvidenceStatus
    checked_at: datetime
    result: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    _normalize_checked_at = field_validator("checked_at")(normalize_utc_datetime)

    @model_validator(mode="after")
    def require_result_for_exception(self) -> "ExternalEvidenceUpdate":
        if self.status in {"mismatch", "unavailable"} and not self.result:
            raise ValueError("result is required for mismatch or unavailable evidence")
        return self


class ExternalEvidenceRead(BaseModel):
    id: int
    pilot_id: int
    capability: str
    status: EvidenceStatus
    checked_by_user_id: int
    checked_at: datetime
    result: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutputNotificationCreate(BaseModel):
    recipient_mobile: str | None = None
    alternate_contact_method: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("recipient_mobile")
    @classmethod
    def normalize_optional_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value) if value else None


class IncidentCreate(BaseModel):
    mission_id: int | None = None
    occurred_at: datetime
    stage_number: int = Field(ge=1, le=19)
    severity: IncidentSeverity
    incident_type: IncidentType
    description: str = Field(min_length=2, max_length=10000)
    containment_action: str | None = Field(default=None, max_length=10000)
    notified_people: list[str] = Field(default_factory=list, max_length=100)
    owner_user_id: int | None = None
    correction_due_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    _normalize_occurred_at = field_validator("occurred_at")(normalize_utc_datetime)

    @field_validator("correction_due_at")
    @classmethod
    def normalize_optional_due_at(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @field_validator("notified_people")
    @classmethod
    def normalize_notified_people(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 160 for value in normalized):
            raise ValueError("notified_people items must be 1 to 160 characters")
        return normalized

    @model_validator(mode="after")
    def validate_correction_due_at(self) -> "IncidentCreate":
        if self.correction_due_at and self.correction_due_at < self.occurred_at:
            raise ValueError("correction_due_at cannot be before occurred_at")
        return self


class IncidentPatch(BaseModel):
    containment_action: str | None = Field(default=None, max_length=10000)
    notified_people: list[str] | None = Field(default=None, max_length=100)
    root_cause: str | None = Field(default=None, max_length=10000)
    corrective_action: str | None = Field(default=None, max_length=10000)
    owner_user_id: int | None = None
    correction_due_at: datetime | None = None
    result: str | None = Field(default=None, max_length=10000)
    evidence: str | None = Field(default=None, max_length=10000)
    lessons_learned: str | None = Field(default=None, max_length=10000)
    status: Literal["open", "contained", "resolved"] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("correction_due_at")
    @classmethod
    def normalize_optional_due_at(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @field_validator("notified_people")
    @classmethod
    def normalize_notified_people(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 160 for value in normalized):
            raise ValueError("notified_people items must be 1 to 160 characters")
        return normalized

    @model_validator(mode="after")
    def require_changes(self) -> "IncidentPatch":
        if not self.model_fields_set:
            raise ValueError("at least one Incident field must change")
        return self


class IncidentClose(BaseModel):
    root_cause: str = Field(min_length=2, max_length=10000)
    corrective_action: str = Field(min_length=2, max_length=10000)
    result: str = Field(min_length=2, max_length=10000)
    evidence: str | None = Field(default=None, max_length=10000)
    lessons_learned: str = Field(min_length=2, max_length=10000)
    confirmed: bool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_confirmation(self) -> "IncidentClose":
        if not self.confirmed:
            raise ValueError("closing an incident requires confirmation")
        return self


class IncidentRead(BaseModel):
    id: int
    pilot_id: int
    mission_id: int | None
    sequence: int
    code: str
    occurred_at: datetime
    reported_by_user_id: int
    stage_number: int
    severity: IncidentSeverity
    incident_type: IncidentType
    description: str
    containment_action: str | None
    notified_people: list[str]
    root_cause: str | None
    corrective_action: str | None
    owner_user_id: int | None
    response_due_at: datetime
    correction_due_at: datetime | None
    result: str | None
    evidence: str | None
    lessons_learned: str | None
    status: IncidentStatus
    closed_by_user_id: int | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
