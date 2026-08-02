"""Add user preferences and audit metadata.

Revision ID: 0013_user_preferences_audit_metadata
Revises: 0012_stage_13_19_g5_alignment
Create Date: 2026-08-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013_user_preferences_audit_metadata"
down_revision: str | None = "0012_stage_13_19_g5_alignment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("theme", sa.String(length=16), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("calendar", sa.String(length=16), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("default_page", sa.String(length=120), nullable=True),
        sa.Column("last_page", sa.String(length=120), nullable=True),
        sa.Column("visible_columns", json_type, nullable=False),
        sa.Column("column_order", json_type, nullable=False),
        sa.Column("saved_filters", json_type, nullable=False),
        sa.Column("notification_preferences", json_type, nullable=False),
        sa.Column("dashboard_preferences", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("pilot_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("user_agent", sa.String(length=500), nullable=True))
        batch_op.create_foreign_key("fk_audit_logs_pilot_id_pilots", "pilots", ["pilot_id"], ["id"])
        batch_op.create_index("ix_audit_logs_pilot_id", ["pilot_id"])
        batch_op.create_index("ix_audit_logs_request_id", ["request_id"])


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_index("ix_audit_logs_request_id")
        batch_op.drop_index("ix_audit_logs_pilot_id")
        batch_op.drop_constraint("fk_audit_logs_pilot_id_pilots", type_="foreignkey")
        batch_op.drop_column("user_agent")
        batch_op.drop_column("request_id")
        batch_op.drop_column("pilot_id")

    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
