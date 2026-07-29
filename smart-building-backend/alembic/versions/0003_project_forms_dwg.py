"""Add project, F01/F02, floor, and DWG versioning.

Revision ID: 0003_project_forms_dwg
Revises: 0002_auth_rbac_audit
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_project_forms_dwg"
down_revision: str | None = "0002_auth_rbac_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("decision_maker_name", sa.String(length=120), nullable=False),
        sa.Column("decision_maker_position", sa.String(length=120), nullable=False),
        sa.Column("primary_mobile", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_owners_name", "owners", ["name"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("system_name", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("total_floors", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("progress_stage", sa.String(length=160), nullable=False),
        sa.Column("customer_need", sa.Text(), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_system_name", "projects", ["system_name"], unique=True)

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("mobile", sa.String(length=20), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("is_site_coordinator", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contacts_owner_id", "contacts", ["owner_id"])

    op.create_table(
        "floors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("level_order", sa.Integer(), nullable=False),
        sa.Column("floor_type", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "code", name="uq_floor_project_code"),
        sa.UniqueConstraint("project_id", "level_order", name="uq_floor_project_order"),
    )
    op.create_index("ix_floors_project_id", "floors", ["project_id"])

    op.create_table(
        "dwg_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("floor_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("floor_id"),
    )

    op.create_table(
        "form_f01",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("case_owner_user_id", sa.Integer(), nullable=False),
        sa.Column("project_active", sa.Boolean(), nullable=False),
        sa.Column("imaging_value", sa.Boolean(), nullable=False),
        sa.Column("remote_viewing_need", sa.Boolean(), nullable=False),
        sa.Column("access_possible", sa.Boolean(), nullable=False),
        sa.Column("dwg_available", sa.Boolean(), nullable=False),
        sa.Column("continued_capacity", sa.Boolean(), nullable=False),
        sa.Column("not_demo_only", sa.Boolean(), nullable=False),
        sa.Column("introduction_completed", sa.Boolean(), nullable=False),
        sa.Column("imaging_accepted", sa.Boolean(), nullable=False),
        sa.Column("dwg_accepted", sa.Boolean(), nullable=False),
        sa.Column("feedback_accepted", sa.Boolean(), nullable=False),
        sa.Column("coordinator_name", sa.String(length=120), nullable=True),
        sa.Column("coordinator_mobile", sa.String(length=20), nullable=True),
        sa.Column("limitation", sa.Text(), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("referral_deadline", sa.Date(), nullable=True),
        sa.Column("sales_user_id", sa.Integer(), nullable=True),
        sa.Column("pilot_manager_user_id", sa.Integer(), nullable=True),
        sa.Column("referred_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["pilot_manager_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sales_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )

    op.create_table(
        "form_f02",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("information_package", sa.Text(), nullable=True),
        sa.Column("contacts_summary", sa.Text(), nullable=True),
        sa.Column("progress_status", sa.String(length=160), nullable=True),
        sa.Column("limitation", sa.Text(), nullable=True),
        sa.Column("main_project_registered", sa.Boolean(), nullable=False),
        sa.Column("floor_order_confirmed", sa.Boolean(), nullable=False),
        sa.Column("typical_floors_identified", sa.Boolean(), nullable=False),
        sa.Column("plan_connections_registered", sa.Boolean(), nullable=False),
        sa.Column("start_point_registered", sa.Boolean(), nullable=False),
        sa.Column("expert_access_tested", sa.Boolean(), nullable=False),
        sa.Column("main_app_display_tested", sa.Boolean(), nullable=False),
        sa.Column("ready_for_capture", sa.Boolean(), nullable=False),
        sa.Column("ambiguity", sa.Text(), nullable=True),
        sa.Column("referred_at", sa.DateTime(), nullable=True),
        sa.Column("configured_by_user_id", sa.Integer(), nullable=True),
        sa.Column("controlled_by_user_id", sa.Integer(), nullable=True),
        sa.Column("configured_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["configured_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["controlled_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )

    op.create_table(
        "dwg_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dwg_file_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("standardized_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("dwg_signature", sa.String(length=12), nullable=False),
        sa.Column("is_readable", sa.Boolean(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dwg_file_id"], ["dwg_files.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dwg_file_id", "sha256", name="uq_dwg_file_hash"),
        sa.UniqueConstraint("dwg_file_id", "version", name="uq_dwg_file_version"),
        sa.UniqueConstraint("standardized_filename"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_dwg_versions_dwg_file_id", "dwg_versions", ["dwg_file_id"])
    op.create_index("ix_dwg_versions_sha256", "dwg_versions", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_dwg_versions_sha256", table_name="dwg_versions")
    op.drop_index("ix_dwg_versions_dwg_file_id", table_name="dwg_versions")
    op.drop_table("dwg_versions")
    op.drop_table("form_f02")
    op.drop_table("form_f01")
    op.drop_table("dwg_files")
    op.drop_index("ix_floors_project_id", table_name="floors")
    op.drop_table("floors")
    op.drop_index("ix_contacts_owner_id", table_name="contacts")
    op.drop_table("contacts")
    op.drop_index("ix_projects_system_name", table_name="projects")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_owners_name", table_name="owners")
    op.drop_table("owners")
