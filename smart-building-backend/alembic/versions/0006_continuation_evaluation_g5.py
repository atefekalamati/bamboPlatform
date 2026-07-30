"""Add continuation reviews, pilot evaluation, and G5 closing fields.

Revision ID: 0006_continuation_evaluation_g5
Revises: 0005_customer_experience_incidents
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_continuation_evaluation_g5"
down_revision: str | None = "0005_customer_experience_incidents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("form_f04") as batch_op:
        batch_op.add_column(
            sa.Column("main_platform_login_count", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "viewed_sections",
                json_type,
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(
            sa.Column("visit_reduction_result", sa.String(length=24), nullable=True)
        )
        batch_op.add_column(
            sa.Column("customer_need_summary", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("closing_decision", sa.String(length=24), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_form_f04_main_platform_login_count",
            "main_platform_login_count IS NULL OR main_platform_login_count >= 0",
        )
        batch_op.create_check_constraint(
            "ck_form_f04_visit_reduction_result",
            "visit_reduction_result IS NULL OR visit_reduction_result IN "
            "('confirmed', 'not_confirmed', 'unknown')",
        )
        batch_op.create_check_constraint(
            "ck_form_f04_closing_decision",
            "closing_decision IS NULL OR closing_decision IN "
            "('proposal', 'follow_up', 'continue_pilot', 'stop', 'undecided')",
        )
        batch_op.alter_column("viewed_sections", server_default=None)

    op.create_table(
        "continuation_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("stage_5_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_6_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_7_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_8_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_9_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_10_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_11_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_12_confirmed", sa.Boolean(), nullable=False),
        sa.Column("stage_13_confirmed", sa.Boolean(), nullable=False),
        sa.Column("independent_result", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_id"),
    )

    op.create_table(
        "pilot_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("operations_status", sa.String(length=24), nullable=False),
        sa.Column("operations_result", sa.Text(), nullable=False),
        sa.Column("quality_status", sa.String(length=24), nullable=False),
        sa.Column("quality_result", sa.Text(), nullable=False),
        sa.Column("technical_status", sa.String(length=24), nullable=False),
        sa.Column("technical_result", sa.Text(), nullable=False),
        sa.Column("customer_status", sa.String(length=24), nullable=False),
        sa.Column("customer_result", sa.Text(), nullable=False),
        sa.Column("commercial_status", sa.String(length=24), nullable=False),
        sa.Column("commercial_result", sa.Text(), nullable=False),
        sa.Column("one_page_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "operations_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_operations_status",
        ),
        sa.CheckConstraint(
            "quality_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_quality_status",
        ),
        sa.CheckConstraint(
            "technical_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_technical_status",
        ),
        sa.CheckConstraint(
            "customer_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_customer_status",
        ),
        sa.CheckConstraint(
            "commercial_status IN ('approved', 'needs_action', 'not_applicable')",
            name="ck_pilot_evaluation_commercial_status",
        ),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )


def downgrade() -> None:
    op.drop_table("pilot_evaluations")
    op.drop_table("continuation_reviews")

    with op.batch_alter_table("form_f04") as batch_op:
        batch_op.drop_constraint(
            "ck_form_f04_closing_decision",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_form_f04_visit_reduction_result",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_form_f04_main_platform_login_count",
            type_="check",
        )
        batch_op.drop_column("closing_decision")
        batch_op.drop_column("customer_need_summary")
        batch_op.drop_column("visit_reduction_result")
        batch_op.drop_column("viewed_sections")
        batch_op.drop_column("main_platform_login_count")
