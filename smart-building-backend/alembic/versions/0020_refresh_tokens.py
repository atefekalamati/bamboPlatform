"""Add refresh token session fields.

Revision ID: 0020_refresh_tokens
Revises: 0019_user_own_name_edit_permission
Create Date: 2026-08-08
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0020_refresh_tokens"
down_revision: str | None = "0019_user_own_name_edit_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("auth_sessions", sa.Column("refresh_token_hash", sa.String(length=64), nullable=True))
    op.add_column("auth_sessions", sa.Column("previous_refresh_token_hash", sa.String(length=64), nullable=True))
    op.add_column("auth_sessions", sa.Column("refresh_expires_at", sa.DateTime(), nullable=True))
    op.add_column("auth_sessions", sa.Column("refresh_used_at", sa.DateTime(), nullable=True))
    op.add_column("auth_sessions", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("auth_sessions", sa.Column("user_agent", sa.String(length=500), nullable=True))
    op.create_index("ix_auth_sessions_refresh_token_hash", "auth_sessions", ["refresh_token_hash"], unique=True)
    op.create_index("ix_auth_sessions_previous_refresh_token_hash", "auth_sessions", ["previous_refresh_token_hash"])
    op.create_index("ix_auth_sessions_refresh_expires_at", "auth_sessions", ["refresh_expires_at"])
    op.create_index("ix_auth_sessions_ip_address", "auth_sessions", ["ip_address"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_ip_address", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_refresh_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_previous_refresh_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_refresh_token_hash", table_name="auth_sessions")
    op.drop_column("auth_sessions", "user_agent")
    op.drop_column("auth_sessions", "ip_address")
    op.drop_column("auth_sessions", "refresh_used_at")
    op.drop_column("auth_sessions", "refresh_expires_at")
    op.drop_column("auth_sessions", "previous_refresh_token_hash")
    op.drop_column("auth_sessions", "refresh_token_hash")
