"""Read-only contracts for the operational dashboard."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class DashboardResponse(BaseModel):
    generated_at: datetime
    filters: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    items: list[Any] = Field(default_factory=list)
    pagination: Pagination | None = None
    state: str = "SUCCESS"


class PilotDashboardItem(BaseModel):
    id: int
    pilot_code: str
    project: str
    owner_company: str | None = None
    current_stage: int
    pilot_status: str
    stage_status: str | None = None
    progress_percent: float
    current_assignee: str | None = None
    next_action: str | None = None
    due_at: datetime | None = None
    sla_status: str
    open_incidents: int
    critical_incidents: int
    current_gate: str | None = None
    commercial_status: str | None = None
    final_outcome: str | None = None
    last_updated_at: datetime


class ActionItem(BaseModel):
    id: str
    priority: str
    entity_type: str
    entity_id: int | None = None
    pilot_id: int | None = None
    title: str
    due_at: datetime | None = None
    action_url: str | None = None
    status: str = "open"
