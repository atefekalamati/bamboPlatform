"""Add in-app notification metadata and delivery logs.

Revision ID: 0014_in_app_notifications_delivery
Revises: 0013_user_preferences_audit_metadata
Create Date: 2026-08-02
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0014_in_app_notifications_delivery"
down_revision: str | None = "0013_user_preferences_audit_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "notification_type",
                sa.String(length=80),
                nullable=False,
                server_default="system.notification",
            )
        )
        batch_op.add_column(
            sa.Column("category", sa.String(length=32), nullable=False, server_default="SYSTEM")
        )
        batch_op.add_column(
            sa.Column("priority", sa.String(length=16), nullable=False, server_default="NORMAL")
        )
        batch_op.add_column(sa.Column("title", sa.String(length=160), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("body", sa.Text(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("short_body", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("entity_type", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("entity_id", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("action_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("read_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("deduplication_key", sa.String(length=160), nullable=True))
        batch_op.create_foreign_key(
            "fk_notifications_actor_user_id_users",
            "users",
            ["actor_user_id"],
            ["id"],
        )
        batch_op.create_index("ix_notifications_actor_user_id", ["actor_user_id"])
        batch_op.create_index("ix_notifications_notification_type", ["notification_type"])
        batch_op.create_index("ix_notifications_category", ["category"])
        batch_op.create_index("ix_notifications_priority", ["priority"])
        batch_op.create_index("ix_notifications_entity_type", ["entity_type"])
        batch_op.create_index("ix_notifications_entity_id", ["entity_id"])
        batch_op.create_index("ix_notifications_is_read", ["is_read"])
        batch_op.create_index("ix_notifications_expires_at", ["expires_at"])
        batch_op.create_index("ix_notifications_deleted_at", ["deleted_at"])
        batch_op.create_index("ix_notifications_deduplication_key", ["deduplication_key"])
        batch_op.create_check_constraint(
            "ck_notification_priority",
            "priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')",
        )
        batch_op.create_check_constraint(
            "ck_notification_category",
            "category IN ('AUTH', 'PILOT', 'STAGE', 'MISSION', "
            "'INCIDENT', 'SLA', 'COMMERCIAL', 'SYSTEM')",
        )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("recipient_address", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("template_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_message_id", sa.String(length=120), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("channel IN ('IN_APP', 'SMS')", name="ck_notification_delivery_channel"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'QUEUED', 'SENDING', 'SENT', 'DELIVERED', "
            "'FAILED', 'CANCELLED', 'SKIPPED')",
            name="ck_notification_delivery_status",
        ),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])
    op.create_index("ix_notification_deliveries_channel", "notification_deliveries", ["channel"])
    op.create_index("ix_notification_deliveries_template_code", "notification_deliveries", ["template_code"])
    op.create_index("ix_notification_deliveries_status", "notification_deliveries", ["status"])
    op.create_index("ix_notification_deliveries_next_retry_at", "notification_deliveries", ["next_retry_at"])
    op.create_index("ix_notification_deliveries_created_at", "notification_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_created_at", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_next_retry_at", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_status", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_template_code", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_channel", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_notification_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("ck_notification_category", type_="check")
        batch_op.drop_constraint("ck_notification_priority", type_="check")
        batch_op.drop_index("ix_notifications_deduplication_key")
        batch_op.drop_index("ix_notifications_deleted_at")
        batch_op.drop_index("ix_notifications_expires_at")
        batch_op.drop_index("ix_notifications_is_read")
        batch_op.drop_index("ix_notifications_entity_id")
        batch_op.drop_index("ix_notifications_entity_type")
        batch_op.drop_index("ix_notifications_priority")
        batch_op.drop_index("ix_notifications_category")
        batch_op.drop_index("ix_notifications_notification_type")
        batch_op.drop_index("ix_notifications_actor_user_id")
        batch_op.drop_constraint("fk_notifications_actor_user_id_users", type_="foreignkey")
        batch_op.drop_column("deduplication_key")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("read_at")
        batch_op.drop_column("is_read")
        batch_op.drop_column("action_url")
        batch_op.drop_column("entity_id")
        batch_op.drop_column("entity_type")
        batch_op.drop_column("short_body")
        batch_op.drop_column("body")
        batch_op.drop_column("title")
        batch_op.drop_column("priority")
        batch_op.drop_column("category")
        batch_op.drop_column("notification_type")
        batch_op.drop_column("actor_user_id")
