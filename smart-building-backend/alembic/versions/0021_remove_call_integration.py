"""Remove backend call provider integration.

Revision ID: 0021_remove_call_integration
Revises: 0020_refresh_tokens
Create Date: 2026-08-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0021_remove_call_integration"
down_revision: Union[str, None] = "0020_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("call_webhook_events")
    op.drop_table("call_outcomes")
    op.drop_table("call_attempts")
    op.drop_table("calls")


def downgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("pilot_id", sa.Integer(), sa.ForeignKey("pilots.id"), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("destination_phone", sa.String(length=32), nullable=False),
        sa.Column("masked_destination", sa.String(length=32), nullable=False),
        sa.Column("business_status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("technical_status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("required_for_stage", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requirement_overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("override_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("override_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recording_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recording_reference", sa.String(length=500), nullable=True),
        sa.Column("initiated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("stage_number BETWEEN 1 AND 19", name="ck_calls_stage_number"),
        sa.UniqueConstraint("public_id", name="uq_calls_public_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_calls_idempotency_key"),
    )
    op.create_index("ix_calls_pilot_stage", "calls", ["pilot_id", "stage_number"])
    op.create_index("ix_calls_business_status", "calls", ["business_status"])
    op.create_index("ix_calls_technical_status", "calls", ["technical_status"])

    op.create_table(
        "call_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("call_id", sa.Integer(), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_call_id", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="initiating"),
        sa.Column("failure_code", sa.String(length=120), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("call_id", "attempt_number", name="uq_call_attempt_number"),
    )
    op.create_index("ix_call_attempts_call_id", "call_attempts", ["call_id"])
    op.create_index("ix_call_attempts_provider_call_id", "call_attempts", ["provider_call_id"], unique=True)
    op.create_index("ix_call_attempts_status", "call_attempts", ["status"])

    op.create_table(
        "call_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("call_id", sa.Integer(), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_call_outcomes_call_id", "call_outcomes", ["call_id"])
    op.create_index("ix_call_outcomes_outcome", "call_outcomes", ["outcome"])

    op.create_table(
        "call_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.String(length=160), nullable=False),
        sa.Column("provider_call_id", sa.String(length=160), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "event_id", name="uq_call_webhook_provider_event"),
    )
    op.create_index("ix_call_webhook_events_provider_call_id", "call_webhook_events", ["provider_call_id"])
