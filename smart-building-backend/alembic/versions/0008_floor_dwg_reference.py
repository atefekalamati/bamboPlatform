"""Add an auditable external DWG reference confirmation to floors.

Revision ID: 0008_floor_dwg_reference
Revises: 0007_commercial_final_outcome
Create Date: 2026-07-30
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008_floor_dwg_reference"
down_revision: str | None = "0007_commercial_final_outcome"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("floors") as batch_op:
        batch_op.add_column(
            sa.Column(
                "dwg_reference_confirmed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("dwg_reference_confirmed_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "dwg_reference_confirmed_by_user_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_floors_dwg_reference_user",
            "users",
            ["dwg_reference_confirmed_by_user_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("floors") as batch_op:
        batch_op.drop_constraint(
            "fk_floors_dwg_reference_user",
            type_="foreignkey",
        )
        batch_op.drop_column("dwg_reference_confirmed_by_user_id")
        batch_op.drop_column("dwg_reference_confirmed_at")
        batch_op.drop_column("dwg_reference_confirmed")
