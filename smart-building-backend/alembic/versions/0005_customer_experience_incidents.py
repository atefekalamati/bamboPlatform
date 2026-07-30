"""Add external status, F04, evidence checks, and F05 incidents.

Revision ID: 0005_customer_experience_incidents
Revises: 0004_missions_f03_operations
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_customer_experience_incidents"
down_revision: str | None = "0004_missions_f03_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=False,
        )

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("pilot_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("alternate_contact_method", sa.String(length=500), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_notifications_pilot_id_pilots",
            "pilots",
            ["pilot_id"],
            ["id"],
        )
        batch_op.create_index("ix_notifications_pilot_id", ["pilot_id"])

    op.create_table(
        "external_platform_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("project_reference", sa.String(length=160), nullable=True),
        sa.Column("platform_status", sa.String(length=24), nullable=False),
        sa.Column("processing_started", sa.Boolean(), nullable=False),
        sa.Column("route_detected", sa.Boolean(), nullable=False),
        sa.Column("plan_connected", sa.Boolean(), nullable=False),
        sa.Column("tour_ready", sa.Boolean(), nullable=False),
        sa.Column("captures_menu_checked", sa.Boolean(), nullable=False),
        sa.Column("latest_capture_checked", sa.Boolean(), nullable=False),
        sa.Column("last_visit_checked", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("checked_by_user_id", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "platform_status IN ('available', 'degraded', 'down', 'unknown')",
            name="ck_external_platform_status",
        ),
        sa.ForeignKeyConstraint(["checked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )

    op.create_table(
        "form_f04",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Integer(), nullable=False),
        sa.Column("owner_logged_in", sa.Boolean(), nullable=False),
        sa.Column("project_opened", sa.Boolean(), nullable=False),
        sa.Column("main_tour_viewed", sa.Boolean(), nullable=False),
        sa.Column("training_completed", sa.Boolean(), nullable=False),
        sa.Column("viewing_result", sa.Text(), nullable=True),
        sa.Column("issue_description", sa.Text(), nullable=True),
        sa.Column("issue_category", sa.String(length=32), nullable=True),
        sa.Column("issue_route", sa.String(length=32), nullable=True),
        sa.Column("issue_owner_user_id", sa.Integer(), nullable=True),
        sa.Column("issue_due_at", sa.DateTime(), nullable=True),
        sa.Column("first_follow_up_at", sa.DateTime(), nullable=True),
        sa.Column("second_follow_up_at", sa.DateTime(), nullable=True),
        sa.Column("useful", sa.Boolean(), nullable=True),
        sa.Column("coverage_score", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("most_useful_part", sa.Text(), nullable=True),
        sa.Column("missing_part", sa.Text(), nullable=True),
        sa.Column("other_users", sa.Text(), nullable=True),
        sa.Column("more_training_needed", sa.Boolean(), nullable=True),
        sa.Column("satisfaction_score", sa.Integer(), nullable=True),
        sa.Column("continuation_interest", sa.Boolean(), nullable=True),
        sa.Column("proposal_ready", sa.Boolean(), nullable=True),
        sa.Column("realized_value", sa.Text(), nullable=True),
        sa.Column("purchase_blocker", sa.Text(), nullable=True),
        sa.Column("project_count", sa.Integer(), nullable=True),
        sa.Column("usage_frequency", sa.String(length=160), nullable=True),
        sa.Column("user_count", sa.Integer(), nullable=True),
        sa.Column("decision_maker", sa.String(length=160), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("final_result", sa.String(length=160), nullable=True),
        sa.Column("final_reason", sa.Text(), nullable=True),
        sa.Column("customer_success_user_id", sa.Integer(), nullable=True),
        sa.Column("sales_user_id", sa.Integer(), nullable=True),
        sa.Column("pilot_manager_user_id", sa.Integer(), nullable=True),
        sa.Column("login_trained", sa.Boolean(), nullable=False),
        sa.Column("project_trained", sa.Boolean(), nullable=False),
        sa.Column("floor_trained", sa.Boolean(), nullable=False),
        sa.Column("plan_trained", sa.Boolean(), nullable=False),
        sa.Column("tour_trained", sa.Boolean(), nullable=False),
        sa.Column("navigation_trained", sa.Boolean(), nullable=False),
        sa.Column("support_trained", sa.Boolean(), nullable=False),
        sa.Column("independent_use_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "issue_category IS NULL OR issue_category IN "
            "('access', 'platform', 'coverage_quality', 'training', "
            "'capability', 'continuation')",
            name="ck_form_f04_issue_category",
        ),
        sa.CheckConstraint(
            "issue_route IS NULL OR issue_route IN "
            "('support', 'technical', 'operations', 'training', 'product', 'sales')",
            name="ck_form_f04_issue_route",
        ),
        sa.CheckConstraint(
            "coverage_score IS NULL OR coverage_score BETWEEN 1 AND 10",
            name="ck_form_f04_coverage_score",
        ),
        sa.CheckConstraint(
            "quality_score IS NULL OR quality_score BETWEEN 1 AND 10",
            name="ck_form_f04_quality_score",
        ),
        sa.CheckConstraint(
            "satisfaction_score IS NULL OR satisfaction_score BETWEEN 1 AND 10",
            name="ck_form_f04_satisfaction_score",
        ),
        sa.CheckConstraint(
            "project_count IS NULL OR project_count >= 0",
            name="ck_form_f04_project_count",
        ),
        sa.CheckConstraint(
            "user_count IS NULL OR user_count >= 0",
            name="ck_form_f04_user_count",
        ),
        sa.ForeignKeyConstraint(["customer_success_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["issue_owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["pilot_manager_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sales_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pilot_id"),
    )

    op.create_table(
        "external_evidence_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("checked_by_user_id", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("result", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('checked', 'mismatch', 'unavailable', 'not_checked')",
            name="ck_external_evidence_status",
        ),
        sa.ForeignKeyConstraint(["checked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pilot_id",
            "capability",
            name="uq_external_evidence_pilot_capability",
        ),
    )
    op.create_index(
        "ix_external_evidence_checks_pilot_id",
        "external_evidence_checks",
        ["pilot_id"],
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pilot_id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("reported_by_user_id", sa.Integer(), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("incident_type", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("containment_action", sa.Text(), nullable=True),
        sa.Column("notified_people", json_type, nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("response_due_at", sa.DateTime(), nullable=False),
        sa.Column("correction_due_at", sa.DateTime(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("closed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "stage_number BETWEEN 1 AND 19",
            name="ck_incident_stage_number",
        ),
        sa.CheckConstraint(
            "severity IN ('normal', 'important', 'critical')",
            name="ck_incident_severity",
        ),
        sa.CheckConstraint(
            "incident_type IN "
            "('safety', 'equipment', 'dwg', 'main_platform', "
            "'access', 'customer', 'process')",
            name="ck_incident_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'contained', 'resolved', 'closed')",
            name="ck_incident_status",
        ),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_id"], ["pilots.id"]),
        sa.ForeignKeyConstraint(["reported_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("pilot_id", "sequence", name="uq_incident_pilot_sequence"),
    )
    for column_name in (
        "code",
        "incident_type",
        "mission_id",
        "occurred_at",
        "pilot_id",
        "response_due_at",
        "severity",
        "stage_number",
        "status",
    ):
        op.create_index(
            f"ix_incidents_{column_name}",
            "incidents",
            [column_name],
            unique=column_name == "code",
        )


def downgrade() -> None:
    for column_name in (
        "status",
        "stage_number",
        "severity",
        "response_due_at",
        "pilot_id",
        "occurred_at",
        "mission_id",
        "incident_type",
        "code",
    ):
        op.drop_index(f"ix_incidents_{column_name}", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index(
        "ix_external_evidence_checks_pilot_id",
        table_name="external_evidence_checks",
    )
    op.drop_table("external_evidence_checks")
    op.drop_table("form_f04")
    op.drop_table("external_platform_references")

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notifications_pilot_id")
        batch_op.drop_constraint(
            "fk_notifications_pilot_id_pilots",
            type_="foreignkey",
        )
        batch_op.drop_column("alternate_contact_method")
        batch_op.drop_column("pilot_id")
