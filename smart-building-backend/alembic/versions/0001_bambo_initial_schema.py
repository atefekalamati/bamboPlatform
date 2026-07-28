"""Create the initial BAMBO pilot schema.

Revision ID: 0001_bambo_initial
Revises:
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_bambo_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_floors", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buildings_id", "buildings", ["id"])
    op.create_index("ix_buildings_name", "buildings", ["name"])

    op.create_table(
        "pilots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("pilot_year", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("project_number", sa.Integer(), nullable=False),
        sa.Column("project_system_name", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_stage", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_year", "sequence", name="uq_pilot_year_sequence"),
        sa.UniqueConstraint("project_number"),
        sa.UniqueConstraint("project_system_name"),
    )
    op.create_index("ix_pilots_code", "pilots", ["code"], unique=True)
    op.create_index("ix_pilots_pilot_year", "pilots", ["pilot_year"])

    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("equipment_type", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equipment_building_id", "equipment", ["building_id"])
    op.create_index("ix_equipment_id", "equipment", ["id"])
    op.create_index("ix_equipment_name", "equipment", ["name"])

    op.create_table(
        "pilot_gates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("after_stage", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("passed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id", "code", name="uq_pilot_gate_code"),
    )
    op.create_index("ix_pilot_gates_pilot_id", "pilot_gates", ["pilot_id"])

    op.create_table(
        "pilot_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latest_version", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id", "number", name="uq_pilot_stage_number"),
    )
    op.create_index("ix_pilot_stages_pilot_id", "pilot_stages", ["pilot_id"])

    op.create_table(
        "sensors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sensor_type", sa.String(length=50), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("equipment_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sensors_equipment_id", "sensors", ["equipment_id"])
    op.create_index("ix_sensors_id", "sensors", ["id"])
    op.create_index("ix_sensors_name", "sensors", ["name"])

    op.create_table(
        "stage_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("form_data", json_type, nullable=False),
        sa.Column("checklist", json_type, nullable=False),
        sa.Column("submitted_by", sa.String(length=120), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["stage_id"], ["pilot_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stage_id", "version", name="uq_stage_submission_version"),
    )
    op.create_index("ix_stage_submissions_stage_id", "stage_submissions", ["stage_id"])

    op.create_table(
        "stage_approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reviewer", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("correction_items", json_type, nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["stage_submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id"),
    )

    op.create_table(
        "immutable_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("approval_id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content", json_type, nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["stage_approvals.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint(
            "pilot_id", "stage_number", "version", name="uq_snapshot_stage_version"
        ),
    )
    op.create_index("ix_immutable_snapshots_pilot_id", "immutable_snapshots", ["pilot_id"])


def downgrade() -> None:
    op.drop_index("ix_immutable_snapshots_pilot_id", table_name="immutable_snapshots")
    op.drop_table("immutable_snapshots")
    op.drop_table("stage_approvals")
    op.drop_index("ix_stage_submissions_stage_id", table_name="stage_submissions")
    op.drop_table("stage_submissions")
    op.drop_index("ix_sensors_name", table_name="sensors")
    op.drop_index("ix_sensors_id", table_name="sensors")
    op.drop_index("ix_sensors_equipment_id", table_name="sensors")
    op.drop_table("sensors")
    op.drop_index("ix_pilot_stages_pilot_id", table_name="pilot_stages")
    op.drop_table("pilot_stages")
    op.drop_index("ix_pilot_gates_pilot_id", table_name="pilot_gates")
    op.drop_table("pilot_gates")
    op.drop_index("ix_equipment_name", table_name="equipment")
    op.drop_index("ix_equipment_id", table_name="equipment")
    op.drop_index("ix_equipment_building_id", table_name="equipment")
    op.drop_table("equipment")
    op.drop_index("ix_pilots_pilot_year", table_name="pilots")
    op.drop_index("ix_pilots_code", table_name="pilots")
    op.drop_table("pilots")
    op.drop_index("ix_buildings_name", table_name="buildings")
    op.drop_index("ix_buildings_id", table_name="buildings")
    op.drop_table("buildings")
