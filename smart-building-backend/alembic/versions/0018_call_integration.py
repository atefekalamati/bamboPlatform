"""Add provider-neutral call lifecycle tables.

Revision ID: 0018_call_integration
Revises: 0017_pilot_scope_and_sms_delivery
Create Date: 2026-08-08
"""

from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "0018_call_integration"
down_revision: str | None = "0017_pilot_scope_and_sms_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("pilot_id", sa.Integer(), sa.ForeignKey("pilots.id"), nullable=False),
        sa.Column("stage_id", sa.Integer(), sa.ForeignKey("pilot_stages.id"), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("owners.id"), nullable=True),
        sa.Column("initiated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("destination_phone", sa.String(20), nullable=False),
        sa.Column("destination_masked", sa.String(24), nullable=False),
        sa.Column("purpose", sa.String(80), nullable=False),
        sa.Column("technical_status", sa.String(32), nullable=False),
        sa.Column("business_outcome", sa.String(48), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("callback_at", sa.DateTime(), nullable=True),
        sa.Column("recording_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recording_reference", sa.String(500), nullable=True),
        sa.Column("controlled_metadata", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("overridden_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("overridden_at", sa.DateTime(), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_calls_idempotency_key"),
    )
    for name, columns in (
        ("ix_calls_pilot_id", ["pilot_id"]),
        ("ix_calls_stage_id", ["stage_id"]), ("ix_calls_stage_number", ["stage_number"]),
        ("ix_calls_owner_id", ["owner_id"]), ("ix_calls_initiated_by_user_id", ["initiated_by_user_id"]),
        ("ix_calls_technical_status", ["technical_status"]), ("ix_calls_business_outcome", ["business_outcome"]),
        ("ix_calls_callback_at", ["callback_at"]),
    ):
        op.create_index(name, "calls", columns)
    op.create_index("ix_calls_public_id", "calls", ["public_id"], unique=True)
    op.create_table(
        "call_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("call_id", sa.Integer(), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_call_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("call_id", "attempt_number", name="uq_call_attempt_number"),
    )
    op.create_index("ix_call_attempts_call_id", "call_attempts", ["call_id"])
    op.create_index("ix_call_attempts_provider_call_id", "call_attempts", ["provider_call_id"], unique=True)
    op.create_index("ix_call_attempts_status", "call_attempts", ["status"])
    op.create_table(
        "call_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("call_id", sa.Integer(), sa.ForeignKey("calls.id"), nullable=False),
        sa.Column("outcome", sa.String(48), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("callback_at", sa.DateTime(), nullable=True),
        sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_call_outcomes_call_id", "call_outcomes", ["call_id"])
    op.create_index("ix_call_outcomes_outcome", "call_outcomes", ["outcome"])
    op.create_table(
        "call_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("provider_call_id", sa.String(160), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload_sanitized", sa.JSON(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("provider", "event_id", name="uq_call_webhook_provider_event"),
    )
    op.create_index("ix_call_webhook_events_provider_call_id", "call_webhook_events", ["provider_call_id"])


def downgrade() -> None:
    op.drop_table("call_webhook_events")
    op.drop_table("call_outcomes")
    op.drop_table("call_attempts")
    op.drop_table("calls")
