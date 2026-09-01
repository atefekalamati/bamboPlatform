"""Let several floors reference one stored DWG file.

A building's floors often share one drawing. Uploading it per floor stored the
same bytes several times, and the two global unique constraints on
``dwg_versions`` made sharing impossible: ``storage_key`` and
``standardized_filename`` each encoded "one row per physical file".

That assumption is what the shared upload changes. The guarantees worth keeping
are per floor, and they already exist as their own constraints:
``uq_dwg_file_version`` (no duplicate version number) and ``uq_dwg_file_hash``
(the same drawing cannot be uploaded twice to one floor). Those stay untouched,
so nothing about duplicate detection weakens — only the global one-row-per-file
rule is lifted.

Both columns keep an index, so lookups by storage key stay fast and the code
that resolves or deletes a file is unaffected.

Revision ID: 0024_shared_dwg_storage
Revises: 0023_merge_customer_success_into_support
Create Date: 2026-09-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0024_shared_dwg_storage"
down_revision: Union[str, None] = "0023_merge_customer_success_into_support"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STORAGE_KEY_UNIQUE = "dwg_versions_storage_key_key"
FILENAME_UNIQUE = "dwg_versions_standardized_filename_key"
STORAGE_KEY_INDEX = "ix_dwg_versions_storage_key"
FILENAME_INDEX = "ix_dwg_versions_standardized_filename"


def _dwg_versions_without_global_uniques() -> sa.Table:
    """The table as it should look afterwards.

    SQLite cannot drop a constraint in place, so batch_alter_table rebuilds the
    table from this definition. It carries the per-floor constraints and leaves
    out the two global ones.
    """
    return sa.Table(
        "dwg_versions",
        sa.MetaData(),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dwg_file_id", sa.Integer(), sa.ForeignKey("dwg_files.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("standardized_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("dwg_signature", sa.String(length=12), nullable=False),
        sa.Column("is_readable", sa.Boolean(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("dwg_file_id", "version", name="uq_dwg_file_version"),
        sa.UniqueConstraint("dwg_file_id", "sha256", name="uq_dwg_file_hash"),
    )


def upgrade() -> None:
    # PostgreSQL names these constraints when the table is created; SQLite
    # writes them inline with no name, so it has to be told the target shape.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(
            "dwg_versions",
            copy_from=_dwg_versions_without_global_uniques(),
            recreate="always",
        ):
            pass
        # Rebuilding the table drops its indexes; the two the model declares
        # have to come back or the schema no longer matches the metadata.
        op.create_index("ix_dwg_versions_dwg_file_id", "dwg_versions", ["dwg_file_id"])
        op.create_index("ix_dwg_versions_sha256", "dwg_versions", ["sha256"])
    else:
        op.drop_constraint(STORAGE_KEY_UNIQUE, "dwg_versions", type_="unique")
        op.drop_constraint(FILENAME_UNIQUE, "dwg_versions", type_="unique")
    op.create_index(STORAGE_KEY_INDEX, "dwg_versions", ["storage_key"])
    op.create_index(FILENAME_INDEX, "dwg_versions", ["standardized_filename"])


def downgrade() -> None:
    """Restore the global uniqueness.

    This fails if shared uploads have already created rows that point at one
    file, which is correct: the old schema cannot represent them, and silently
    dropping rows to fit would lose drawings. Detach the shared versions first
    if a downgrade is genuinely needed.
    """
    op.drop_index(FILENAME_INDEX, table_name="dwg_versions")
    op.drop_index(STORAGE_KEY_INDEX, table_name="dwg_versions")
    if op.get_bind().dialect.name == "sqlite":
        restored = _dwg_versions_without_global_uniques()
        restored.append_constraint(
            sa.UniqueConstraint("standardized_filename", name=FILENAME_UNIQUE)
        )
        restored.append_constraint(
            sa.UniqueConstraint("storage_key", name=STORAGE_KEY_UNIQUE)
        )
        with op.batch_alter_table(
            "dwg_versions", copy_from=restored, recreate="always"
        ):
            pass
        # The rebuild drops every index, including the two the model declares.
        op.create_index("ix_dwg_versions_dwg_file_id", "dwg_versions", ["dwg_file_id"])
        op.create_index("ix_dwg_versions_sha256", "dwg_versions", ["sha256"])
    else:
        op.create_unique_constraint(FILENAME_UNIQUE, "dwg_versions", ["standardized_filename"])
        op.create_unique_constraint(STORAGE_KEY_UNIQUE, "dwg_versions", ["storage_key"])
