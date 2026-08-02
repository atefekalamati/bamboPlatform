"""Harden incident lifecycle fields and indexes.

Revision ID: 0015_incident_lifecycle_hardening
Revises: 0014_in_app_notifications_delivery
Create Date: 2026-08-02
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0015_incident_lifecycle_hardening"
down_revision: str | None = "0014_in_app_notifications_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(sa.Column("reported_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("location", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("informed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("preventive_action", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("responded_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("contained_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("closure_note", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("closure_approved_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_incidents_closure_approved_by_user_id_users",
            "users",
            ["closure_approved_by_user_id"],
            ["id"],
        )
        batch_op.create_index("ix_incidents_reported_at", ["reported_at"])
        batch_op.create_index("ix_incidents_reported_by_user_id", ["reported_by_user_id"])
        batch_op.create_index("ix_incidents_owner_user_id", ["owner_user_id"])
        batch_op.create_index("ix_incidents_correction_due_at", ["correction_due_at"])
        batch_op.create_index("ix_incidents_responded_at", ["responded_at"])

    op.execute("UPDATE incidents SET reported_at = created_at WHERE reported_at IS NULL")
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.alter_column("reported_at", existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.drop_index("ix_incidents_responded_at")
        batch_op.drop_index("ix_incidents_correction_due_at")
        batch_op.drop_index("ix_incidents_owner_user_id")
        batch_op.drop_index("ix_incidents_reported_by_user_id")
        batch_op.drop_index("ix_incidents_reported_at")
        batch_op.drop_constraint(
            "fk_incidents_closure_approved_by_user_id_users",
            type_="foreignkey",
        )
        batch_op.drop_column("closure_approved_by_user_id")
        batch_op.drop_column("closure_note")
        batch_op.drop_column("contained_at")
        batch_op.drop_column("responded_at")
        batch_op.drop_column("preventive_action")
        batch_op.drop_column("informed_at")
        batch_op.drop_column("location")
        batch_op.drop_column("reported_at")
