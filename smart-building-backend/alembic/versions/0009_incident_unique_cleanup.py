"""Remove the redundant incident-code unique constraint.

Revision ID: 0009_incident_unique_cleanup
Revises: 0008_floor_dwg_reference
Create Date: 2026-07-30
"""

from typing import Sequence

from alembic import op

revision: str = "0009_incident_unique_cleanup"
down_revision: str | None = "0008_floor_dwg_reference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL reflects both the unnamed constraint created by migration 0005
    # and the canonical unique index declared by the SQLAlchemy model. Keep the
    # index and remove only the redundant constraint without rewriting history.
    if op.get_bind().dialect.name == "postgresql":
        op.drop_constraint(
            "incidents_code_key",
            "incidents",
            type_="unique",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.create_unique_constraint(
            "incidents_code_key",
            "incidents",
            ["code"],
        )
