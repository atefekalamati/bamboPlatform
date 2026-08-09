"""Track pilot ownership and SMS provider delivery identifiers.

Revision ID: 0017_pilot_scope_and_sms_delivery
Revises: 0016_form_f04_other_issue_description
Create Date: 2026-08-07
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0017_pilot_scope_and_sms_delivery"
down_revision: str | None = "0016_form_f04_other_issue_description"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pilots") as batch_op:
        batch_op.add_column(sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_pilots_created_by_user_id_users",
            "users",
            ["created_by_user_id"],
            ["id"],
        )
        batch_op.create_index("ix_pilots_created_by_user_id", ["created_by_user_id"])
    with op.batch_alter_table("otp_requests") as batch_op:
        batch_op.add_column(sa.Column("provider_message_id", sa.String(length=160), nullable=True))
        batch_op.create_index("ix_otp_requests_provider_message_id", ["provider_message_id"])


def downgrade() -> None:
    with op.batch_alter_table("otp_requests") as batch_op:
        batch_op.drop_index("ix_otp_requests_provider_message_id")
        batch_op.drop_column("provider_message_id")
    with op.batch_alter_table("pilots") as batch_op:
        batch_op.drop_index("ix_pilots_created_by_user_id")
        batch_op.drop_constraint("fk_pilots_created_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("created_by_user_id")
