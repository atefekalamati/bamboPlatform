"""Make Stage 17 proposal PDF metadata optional.

Revision ID: 0011_optional_stage17_proposal_pdf
Revises: 0010_stage_1_12_alignment
Create Date: 2026-08-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011_optional_stage17_proposal_pdf"
down_revision: str | None = "0010_stage_1_12_alignment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OPTIONAL_FILE_CONSTRAINT = (
    "(proposal_file_name IS NULL AND proposal_file_size IS NULL "
    "AND proposal_file_sha256 IS NULL) OR "
    "(proposal_file_name IS NOT NULL AND proposal_file_size IS NOT NULL "
    "AND proposal_file_size > 0 AND proposal_file_sha256 IS NOT NULL "
    "AND length(proposal_file_sha256) = 64)"
)


def upgrade() -> None:
    with op.batch_alter_table("commercial_proposals") as batch_op:
        batch_op.drop_constraint(
            "ck_commercial_proposal_file_size",
            type_="check",
        )
        batch_op.alter_column(
            "proposal_file_name",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.alter_column(
            "proposal_file_size",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.alter_column(
            "proposal_file_sha256",
            existing_type=sa.String(length=64),
            nullable=True,
        )
        batch_op.create_check_constraint(
            "ck_commercial_proposal_file_metadata",
            OPTIONAL_FILE_CONSTRAINT,
        )


def downgrade() -> None:
    missing_file_count = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM commercial_proposals "
            "WHERE proposal_file_name IS NULL "
            "OR proposal_file_size IS NULL "
            "OR proposal_file_sha256 IS NULL"
        )
    ).scalar_one()
    if missing_file_count:
        raise RuntimeError(
            "Cannot restore mandatory Stage 17 PDF columns while proposals "
            "without file metadata exist; register files before downgrading."
        )

    with op.batch_alter_table("commercial_proposals") as batch_op:
        batch_op.drop_constraint(
            "ck_commercial_proposal_file_metadata",
            type_="check",
        )
        batch_op.alter_column(
            "proposal_file_name",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "proposal_file_size",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.alter_column(
            "proposal_file_sha256",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_commercial_proposal_file_size",
            "proposal_file_size > 0",
        )
