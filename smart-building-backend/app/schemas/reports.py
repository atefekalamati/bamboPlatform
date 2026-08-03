"""Typed, read-only contracts shared by management report endpoints."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ReportState = Literal["SUCCESS", "PARTIAL_DATA", "NO_DATA", "NO_ACCESS"]


class ReportFilters(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    pilot_id: int | None = Field(default=None, ge=1)
    project_id: int | None = Field(default=None, ge=1)
    pilot_status: str | None = Field(default=None, max_length=40)
    stage: int | None = Field(default=None, ge=1, le=19)
    stage_status: str | None = Field(default=None, max_length=32)
    gate: str | None = Field(default=None, pattern="^G[1-5]$")
    sla: str | None = Field(default=None, pattern="^(on_track|at_risk|overdue|not_applicable)$")
    assignee_id: int | None = Field(default=None, ge=1)
    has_open_incident: bool | None = None
    has_critical_incident: bool | None = None
    final_outcome: str | None = Field(default=None, max_length=24)
    q: str | None = Field(default=None, max_length=160)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: str = Field(default="updated", max_length=40)

    @model_validator(mode="after")
    def validate_dates(self) -> "ReportFilters":
        for field in ("date_from", "date_to"):
            value = getattr(self, field)
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError(f"{field} must include a timezone offset")
            if value is not None:
                setattr(self, field, value.astimezone(UTC))
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class ReportPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ReportResponse(BaseModel):
    generated_at: datetime
    filters: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
    items: list[dict] = Field(default_factory=list)
    pagination: ReportPagination | None = None
    state: ReportState = "SUCCESS"
