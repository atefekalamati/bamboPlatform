"""Add per-user own-name edit permission.

Revision ID: 0019_user_own_name_edit_permission
Revises: 0018_call_integration
Create Date: 2026-08-08
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0019_user_own_name_edit_permission"
down_revision: str | None = "0018_call_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "can_edit_own_name",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "can_edit_own_name")
