"""Contracts for continuation capture and Stage 15 evaluation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvaluationStatus = Literal["approved", "needs_action", "not_applicable"]


class ContinuationReviewUpdate(BaseModel):
    stage_5_confirmed: bool
    stage_6_confirmed: bool
    stage_7_confirmed: bool
    stage_8_confirmed: bool
    stage_9_confirmed: bool
    stage_10_confirmed: bool
    stage_11_confirmed: bool
    stage_12_confirmed: bool
    stage_13_confirmed: bool
    independent_result: str = Field(min_length=2, max_length=10000)

    model_config = ConfigDict(extra="forbid")


class ContinuationReviewRead(ContinuationReviewUpdate):
    id: int
    mission_id: int
    responsible_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PilotEvaluationUpdate(BaseModel):
    operations_status: EvaluationStatus
    operations_result: str = Field(min_length=2, max_length=10000)
    quality_status: EvaluationStatus
    quality_result: str = Field(min_length=2, max_length=10000)
    technical_status: EvaluationStatus
    technical_result: str = Field(min_length=2, max_length=10000)
    customer_status: EvaluationStatus
    customer_result: str = Field(min_length=2, max_length=10000)
    commercial_status: EvaluationStatus
    commercial_result: str = Field(min_length=2, max_length=10000)
    one_page_summary: str = Field(min_length=2, max_length=20000)

    model_config = ConfigDict(extra="forbid")


class PilotEvaluationRead(PilotEvaluationUpdate):
    id: int
    pilot_id: int
    responsible_user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
