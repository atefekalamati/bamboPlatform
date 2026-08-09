"""Call API contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CALL_OUTCOMES = {
    "customer_confirmed", "revision_requested", "callback_requested", "no_response",
    "customer_rejected", "invalid_contact", "escalated_to_manager",
    "contract_follow_up", "follow_up_completed",
}


class CallCreate(BaseModel):
    purpose: str | None = Field(default=None, max_length=80)
    recording_consent: bool = False
    idempotency_key: str = Field(min_length=8, max_length=120)
    model_config = ConfigDict(extra="forbid")


class CallOutcomeUpdate(BaseModel):
    outcome: str
    summary: str = Field(min_length=3, max_length=4000)
    next_action: str | None = Field(default=None, max_length=2000)
    callback_at: datetime | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.outcome not in CALL_OUTCOMES:
            raise ValueError("unsupported call outcome")
        if self.outcome in {"callback_requested", "contract_follow_up", "revision_requested"} and not (self.next_action and self.next_action.strip()):
            raise ValueError("next_action is required for this outcome")
        if self.outcome == "callback_requested" and self.callback_at is None:
            raise ValueError("callback_at is required for callback_requested")
        self.summary = self.summary.strip()
        self.next_action = self.next_action.strip() if self.next_action else None
        return self


class CallOverride(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)
    model_config = ConfigDict(extra="forbid")


class CallAttemptRead(BaseModel):
    attempt_number: int
    provider: str
    status: str
    failure_code: str | None
    requested_at: datetime
    started_at: datetime | None
    answered_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    model_config = ConfigDict(from_attributes=True)


class CallRead(BaseModel):
    public_id: str
    pilot_id: int
    stage_number: int
    initiated_by_user_id: int
    provider: str
    destination_masked: str
    purpose: str
    technical_status: str
    business_outcome: str | None
    summary: str | None
    next_action: str | None
    callback_at: datetime | None
    recording_consent: bool
    overridden_at: datetime | None
    requested_at: datetime
    started_at: datetime | None
    answered_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    attempts: list[CallAttemptRead]
    model_config = ConfigDict(from_attributes=True)


class RecordingReferenceRead(BaseModel):
    reference: str


class MockWebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=160)
    provider_call_id: str = Field(min_length=1, max_length=160)
    event_type: str = Field(min_length=1, max_length=80)
    status: Literal["initiating", "ringing", "answered", "completed", "no_answer", "busy", "failed", "cancelled"]
    occurred_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    recording_reference: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid")
