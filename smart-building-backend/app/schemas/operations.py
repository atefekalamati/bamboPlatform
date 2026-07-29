"""Mission, F03, per-Floor capture, and notification API contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.security import normalize_mobile

CaptureState = Literal[
    "not_started",
    "completed",
    "incomplete",
    "not_done",
    "needs_revision",
]


def normalize_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include a timezone offset")
    return value.astimezone(UTC).replace(tzinfo=None)


class MissionCreate(BaseModel):
    expert_user_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    floor_ids: list[int] = Field(min_length=1)
    location: str = Field(min_length=2, max_length=500)
    site_contact_name: str = Field(min_length=2, max_length=120)
    site_contact_mobile: str
    limitation: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(extra="forbid")

    _normalize_mobile = field_validator("site_contact_mobile")(normalize_mobile)
    _normalize_start = field_validator("scheduled_start")(normalize_utc_datetime)
    _normalize_end = field_validator("scheduled_end")(normalize_utc_datetime)

    @model_validator(mode="after")
    def validate_schedule_and_floors(self) -> "MissionCreate":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        if len(set(self.floor_ids)) != len(self.floor_ids):
            raise ValueError("floor_ids must be unique")
        return self


class MissionReschedule(BaseModel):
    expert_user_id: int | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    location: str | None = Field(default=None, min_length=2, max_length=500)
    site_contact_name: str | None = Field(default=None, min_length=2, max_length=120)
    site_contact_mobile: str | None = None
    limitation: str | None = Field(default=None, max_length=4000)
    reason: str = Field(min_length=2, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("site_contact_mobile")
    @classmethod
    def normalize_optional_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value) if value else None

    @field_validator("scheduled_start", "scheduled_end")
    @classmethod
    def normalize_optional_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @model_validator(mode="after")
    def validate_update(self) -> "MissionReschedule":
        changed_fields = self.model_fields_set - {"reason"}
        if not changed_fields:
            raise ValueError("at least one mission field must change")
        non_nullable = {
            "expert_user_id",
            "scheduled_start",
            "scheduled_end",
            "location",
            "site_contact_name",
            "site_contact_mobile",
        }
        if any(getattr(self, field) is None for field in changed_fields & non_nullable):
            raise ValueError("required mission fields cannot be null")
        schedule_fields = changed_fields & {"scheduled_start", "scheduled_end"}
        if schedule_fields and schedule_fields != {"scheduled_start", "scheduled_end"}:
            raise ValueError("scheduled_start and scheduled_end must be changed together")
        if (
            self.scheduled_start is not None
            and self.scheduled_end is not None
            and self.scheduled_end <= self.scheduled_start
        ):
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class FormF03Update(BaseModel):
    assignment_accepted: bool
    site_entry_confirmed: bool
    permission_confirmed: bool
    ppe_ready: bool
    camera_ready: bool
    main_app_connected: bool
    battery_ready: bool
    storage_ready: bool
    project_floor_plan_confirmed: bool
    test_image_completed: bool
    stop_condition_reason: str | None = Field(default=None, max_length=4000)
    mission_completed: bool
    operations_confirmed: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("started_at", "finished_at")
    @classmethod
    def normalize_optional_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @model_validator(mode="after")
    def validate_interval(self) -> "FormF03Update":
        if self.finished_at and not self.started_at:
            raise ValueError("started_at is required when finished_at is set")
        if self.started_at and self.finished_at and self.finished_at < self.started_at:
            raise ValueError("finished_at must not be before started_at")
        if self.mission_completed and not self.finished_at:
            raise ValueError("finished_at is required for a completed mission")
        if self.operations_confirmed and not self.mission_completed:
            raise ValueError("operations cannot be confirmed before mission completion")
        return self


class MissionFloorUpdate(BaseModel):
    capture_state: CaptureState
    correct_floor: bool
    start_point_confirmed: bool
    main_capture_started: bool
    continuous_route: bool
    coverage_completed: bool
    capture_finished: bool
    saved_in_main_app: bool
    capture_started_at: datetime | None = None
    capture_finished_at: datetime | None = None
    main_upload_started: bool
    main_upload_completed: bool
    correct_floor_link: bool
    operations_notified: bool
    failure_reason: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("capture_started_at", "capture_finished_at")
    @classmethod
    def normalize_optional_datetime(cls, value: datetime | None) -> datetime | None:
        return normalize_utc_datetime(value) if value else None

    @model_validator(mode="after")
    def validate_capture_state(self) -> "MissionFloorUpdate":
        capture_checks = (
            self.correct_floor,
            self.start_point_confirmed,
            self.main_capture_started,
            self.continuous_route,
            self.coverage_completed,
            self.capture_finished,
            self.saved_in_main_app,
        )
        if self.capture_state == "completed":
            if not all(capture_checks):
                raise ValueError("all capture checklist items are required when completed")
            if not self.capture_started_at or not self.capture_finished_at:
                raise ValueError("capture start and finish times are required when completed")
        elif self.capture_state != "not_started" and not self.failure_reason:
            raise ValueError("failure_reason is required for an unresolved capture")
        if (
            self.capture_started_at
            and self.capture_finished_at
            and self.capture_finished_at < self.capture_started_at
        ):
            raise ValueError("capture_finished_at must not be before capture_started_at")
        if self.main_upload_completed and not self.main_upload_started:
            raise ValueError("main upload cannot complete before it starts")
        if self.correct_floor_link and not self.main_upload_completed:
            raise ValueError("floor link cannot be confirmed before upload completion")
        if self.operations_notified and not (
            self.main_upload_completed and self.correct_floor_link
        ):
            raise ValueError("operations notification requires a completed linked upload")
        return self


class NotificationRead(BaseModel):
    id: int
    public_id: str
    pilot_id: int | None = None
    template: str
    status: str
    provider_status: str
    attempts: int
    last_error: str | None
    alternate_contact_method: str | None = None
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissionFloorRead(BaseModel):
    id: int
    floor_id: int
    capture_state: CaptureState
    correct_floor: bool
    start_point_confirmed: bool
    main_capture_started: bool
    continuous_route: bool
    coverage_completed: bool
    capture_finished: bool
    saved_in_main_app: bool
    capture_started_at: datetime | None
    capture_finished_at: datetime | None
    main_upload_started: bool
    main_upload_completed: bool
    correct_floor_link: bool
    operations_notified: bool
    failure_reason: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FormF03Read(BaseModel):
    id: int
    mission_id: int
    responsible_user_id: int
    assignment_accepted: bool
    site_entry_confirmed: bool
    permission_confirmed: bool
    ppe_ready: bool
    camera_ready: bool
    main_app_connected: bool
    battery_ready: bool
    storage_ready: bool
    project_floor_plan_confirmed: bool
    test_image_completed: bool
    stop_condition_reason: str | None
    mission_completed: bool
    operations_confirmed: bool
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissionRead(BaseModel):
    id: int
    pilot_id: int
    sequence: int
    code: str
    expert_user_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    location: str
    site_contact_name: str
    site_contact_mobile: str
    limitation: str | None
    status: str
    sla_due_at: datetime
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    floor_states: list[MissionFloorRead]
    form_f03: FormF03Read
    notifications: list[NotificationRead]

    model_config = ConfigDict(from_attributes=True)
