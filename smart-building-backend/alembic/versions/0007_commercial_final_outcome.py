"""Add commercial proposal, follow-up calendar, and final outcome.

Revision ID: 0007_commercial_final_outcome
Revises: 0006_continuation_evaluation_g5
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_commercial_final_outcome"
down_revision: str | None = "0006_continuation_evaluation_g5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "commercial_proposals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("project_count", sa.Integer(), nullable=False),
        sa.Column("floor_count", sa.Integer(), nullable=False),
        sa.Column("area_sqm", sa.Float(), nullable=False),
        sa.Column("frequency", sa.String(length=160), nullable=False),
        sa.Column("period", sa.String(length=160), nullable=False),
        sa.Column("user_count", sa.Integer(), nullable=False),
        sa.Column("support_scope", sa.Text(), nullable=False),
        sa.Column("features", json_type, nullable=False),
        sa.Column("proposal_file_name", sa.String(length=255), nullable=False),
        sa.Column("proposal_file_size", sa.Integer(), nullable=False),
        sa.Column("proposal_file_sha256", sa.String(length=64), nullable=False),
        sa.Column("decision_maker", sa.String(length=160), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "project_count > 0",
            name="ck_commercial_proposal_project_count",
        ),
        sa.CheckConstraint(
            "floor_count > 0",
            name="ck_commercial_proposal_floor_count",
        ),
        sa.CheckConstraint(
            "area_sqm > 0",
            name="ck_commercial_proposal_area",
        ),
        sa.CheckConstraint(
            "user_count > 0",
            name="ck_commercial_proposal_user_count",
        ),
        sa.CheckConstraint(
            "proposal_file_size > 0",
            name="ck_commercial_proposal_file_size",
        ),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )

    op.create_table(
        "customer_follow_ups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("schedule_slot", sa.String(length=16), nullable=False),
        sa.Column("obstacle", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "schedule_slot IN ('day_0', 'day_2', 'day_5', 'day_7_10')",
            name="ck_customer_follow_up_schedule_slot",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pilot_id",
            "schedule_slot",
            name="uq_customer_follow_up_pilot_slot",
        ),
    )
    op.create_index(
        op.f("ix_customer_follow_ups_pilot_id"),
        "customer_follow_ups",
        ["pilot_id"],
        unique=False,
    )

    op.create_table(
        "final_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("ready_at", sa.DateTime(), nullable=True),
        sa.Column("success_owner_user_id", sa.Integer(), nullable=True),
        sa.Column("periodic_capture", sa.Boolean(), nullable=True),
        sa.Column("contracted_user_count", sa.Integer(), nullable=True),
        sa.Column("first_capture_at", sa.DateTime(), nullable=True),
        sa.Column(
            "pilot_manager_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "outcome IN "
            "('contract', 'ready_on_date', 'negotiation', 'rejected', 'closed')",
            name="ck_final_outcome_value",
        ),
        sa.CheckConstraint(
            "contracted_user_count IS NULL OR contracted_user_count > 0",
            name="ck_final_outcome_contracted_user_count",
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["success_owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )
    with op.batch_alter_table("final_outcomes") as batch_op:
        batch_op.alter_column("pilot_manager_approved", server_default=None)


def downgrade() -> None:
    op.drop_table("final_outcomes")
    op.drop_index(
        op.f("ix_customer_follow_ups_pilot_id"),
        table_name="customer_follow_ups",
    )
    op.drop_table("customer_follow_ups")
    op.drop_table("commercial_proposals")
