"""Add missions, F03, per-Floor operations, and notifications.

Revision ID: 0004_missions_f03_operations
Revises: 0003_project_forms_dwg
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_missions_f03_operations"
down_revision: str | None = "0003_project_forms_dwg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("expert_user_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=False),
        sa.Column("site_contact_name", sa.String(length=120), nullable=False),
        sa.Column("site_contact_mobile", sa.String(length=20), nullable=False),
        sa.Column("limitation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("sla_due_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "scheduled_end > scheduled_start",
            name="ck_mission_schedule_interval",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'assigned', 'ready', 'in_progress', "
            "'completed', 'cancelled')",
            name="ck_mission_status",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["expert_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id", "sequence", name="uq_mission_pilot_sequence"),
    )
    op.create_index("ix_missions_code", "missions", ["code"], unique=True)
    op.create_index("ix_missions_expert_user_id", "missions", ["expert_user_id"])
    op.create_index("ix_missions_pilot_id", "missions", ["pilot_id"])
    op.create_index("ix_missions_scheduled_end", "missions", ["scheduled_end"])
    op.create_index("ix_missions_scheduled_start", "missions", ["scheduled_start"])
    op.create_index("ix_missions_sla_due_at", "missions", ["sla_due_at"])
    op.create_index("ix_missions_status", "missions", ["status"])

    op.create_table(
        "form_f03",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("assignment_accepted", sa.Boolean(), nullable=False),
        sa.Column("site_entry_confirmed", sa.Boolean(), nullable=False),
        sa.Column("permission_confirmed", sa.Boolean(), nullable=False),
        sa.Column("ppe_ready", sa.Boolean(), nullable=False),
        sa.Column("camera_ready", sa.Boolean(), nullable=False),
        sa.Column("main_app_connected", sa.Boolean(), nullable=False),
        sa.Column("battery_ready", sa.Boolean(), nullable=False),
        sa.Column("storage_ready", sa.Boolean(), nullable=False),
        sa.Column("project_floor_plan_confirmed", sa.Boolean(), nullable=False),
        sa.Column("test_image_completed", sa.Boolean(), nullable=False),
        sa.Column("stop_condition_reason", sa.Text(), nullable=True),
        sa.Column("mission_completed", sa.Boolean(), nullable=False),
        sa.Column("operations_confirmed", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="ck_form_f03_interval",
        ),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_id"),
    )

    op.create_table(
        "mission_floors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("floor_id", sa.Integer(), nullable=False),
        sa.Column("capture_state", sa.String(length=24), nullable=False),
        sa.Column("correct_floor", sa.Boolean(), nullable=False),
        sa.Column("start_point_confirmed", sa.Boolean(), nullable=False),
        sa.Column("main_capture_started", sa.Boolean(), nullable=False),
        sa.Column("continuous_route", sa.Boolean(), nullable=False),
        sa.Column("coverage_completed", sa.Boolean(), nullable=False),
        sa.Column("capture_finished", sa.Boolean(), nullable=False),
        sa.Column("saved_in_main_app", sa.Boolean(), nullable=False),
        sa.Column("capture_started_at", sa.DateTime(), nullable=True),
        sa.Column("capture_finished_at", sa.DateTime(), nullable=True),
        sa.Column("main_upload_started", sa.Boolean(), nullable=False),
        sa.Column("main_upload_completed", sa.Boolean(), nullable=False),
        sa.Column("correct_floor_link", sa.Boolean(), nullable=False),
        sa.Column("operations_notified", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "capture_state IN ('not_started', 'completed', 'incomplete', "
            "'not_done', 'needs_revision')",
            name="ck_mission_floor_capture_state",
        ),
        sa.CheckConstraint(
            "capture_finished_at IS NULL OR capture_started_at IS NULL "
            "OR capture_finished_at >= capture_started_at",
            name="ck_mission_floor_capture_interval",
        ),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_id", "floor_id", name="uq_mission_floor"),
    )
    op.create_index("ix_mission_floors_floor_id", "mission_floors", ["floor_id"])
    op.create_index("ix_mission_floors_mission_id", "mission_floors", ["mission_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=True),
        sa.Column("recipient_user_id", sa.Integer(), nullable=True),
        sa.Column("recipient_mobile", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("template", sa.String(length=80), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_status", sa.String(length=120), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'delivered', 'failed')",
            name="ck_notification_status",
        ),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_mission_id", "notifications", ["mission_id"])
    op.create_index("ix_notifications_public_id", "notifications", ["public_id"], unique=True)
    op.create_index(
        "ix_notifications_recipient_user_id",
        "notifications",
        ["recipient_user_id"],
    )
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_template", "notifications", ["template"])


def downgrade() -> None:
    op.drop_index("ix_notifications_template", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_index("ix_notifications_public_id", table_name="notifications")
    op.drop_index("ix_notifications_mission_id", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_mission_floors_mission_id", table_name="mission_floors")
    op.drop_index("ix_mission_floors_floor_id", table_name="mission_floors")
    op.drop_table("mission_floors")
    op.drop_table("form_f03")
    op.drop_index("ix_missions_status", table_name="missions")
    op.drop_index("ix_missions_sla_due_at", table_name="missions")
    op.drop_index("ix_missions_scheduled_start", table_name="missions")
    op.drop_index("ix_missions_scheduled_end", table_name="missions")
    op.drop_index("ix_missions_pilot_id", table_name="missions")
    op.drop_index("ix_missions_expert_user_id", table_name="missions")
    op.drop_index("ix_missions_code", table_name="missions")
    op.drop_table("missions")
