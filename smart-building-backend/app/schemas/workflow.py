"""Pydantic contracts for the BAMBO pilot workflow."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PilotCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=255)
    pilot_year: int | None = Field(default=None, ge=1300, le=2000)


class GateRead(BaseModel):
    code: str
    title: str
    after_stage: int
    status: str
    passed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class StageRead(BaseModel):
    number: int
    title: str
    status: str
    latest_version: int
    submitted_at: datetime | None
    approved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class PilotRead(BaseModel):
    id: int
    code: str
    pilot_year: int
    project_number: int
    project_system_name: str
    display_name: str
    status: str
    current_stage: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PilotDetail(PilotRead):
    stages: list[StageRead]
    gates: list[GateRead]


class StageSubmit(BaseModel):
    form_data: dict[str, Any] = Field(default_factory=dict)
    checklist: dict[str, bool] = Field(default_factory=dict)


class StageDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)


class StageReject(StageDecision):
    reason: str | None = Field(default=None, max_length=1000)
    correction_items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_rejection_details(self):
        if not (self.reason and self.reason.strip()) and not self.correction_items:
            raise ValueError("A rejection requires a reason or at least one correction item")
        return self


class SubmissionRead(BaseModel):
    id: int
    version: int
    status: str
    form_data: dict[str, Any]
    checklist: dict[str, bool]
    submitted_by: str
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SnapshotRead(BaseModel):
    id: int
    stage_number: int
    version: int
    name: str
    content: dict[str, Any]
    content_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StageActionResult(BaseModel):
    stage: StageRead
    submission: SubmissionRead
    snapshot: SnapshotRead | None = None
