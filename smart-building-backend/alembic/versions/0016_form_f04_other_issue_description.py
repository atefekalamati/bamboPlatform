"""Add optional other issue description to F04.

Revision ID: 0016_form_f04_other_issue_description
Revises: 0015_incident_lifecycle_hardening
Create Date: 2026-08-03
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0016_form_f04_other_issue_description"
down_revision: str | None = "0015_incident_lifecycle_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("form_f04") as batch_op:
        batch_op.add_column(sa.Column("other_issue_description", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("form_f04") as batch_op:
        batch_op.drop_column("other_issue_description")
