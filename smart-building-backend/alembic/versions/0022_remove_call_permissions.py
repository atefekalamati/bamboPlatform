"""Remove the orphaned call permissions.

0021 dropped the call tables and the routers were deleted with them, but the six
``calls.*`` rows stayed behind in ``permissions``. ``seed_security_data`` only
ever inserts, so nothing removes them, and they keep showing up in the role
admin screens as grantable permissions that map to no endpoint.

Revision ID: 0022_remove_call_permissions
Revises: 0021_remove_call_integration
Create Date: 2026-08-26 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022_remove_call_permissions"
down_revision: Union[str, None] = "0021_remove_call_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (code, group_name, description, is_sensitive) exactly as app/rbac.py declared
# them before 0d2997e removed the subsystem. Kept here so downgrade restores the
# original rows rather than inventing new text.
CALL_PERMISSIONS: tuple[tuple[str, str, str, bool], ...] = (
    ("calls.read", "Calls", "مشاهده تماس‌های پرونده‌های مجاز", False),
    ("calls.initiate", "Calls", "آغاز تماس با مشتری", False),
    ("calls.record_outcome", "Calls", "ثبت نتیجه و خلاصه تماس", False),
    ("calls.retry", "Calls", "تلاش مجدد تماس", False),
    ("calls.recording.read", "Calls", "مشاهده مرجع ضبط تماس", True),
    ("calls.override", "Calls", "Override الزام تماس با دلیل", True),
)

CALL_PERMISSION_CODES = tuple(entry[0] for entry in CALL_PERMISSIONS)


def upgrade() -> None:
    bind = op.get_bind()

    # Detach any role grants first; a live FK would otherwise block the delete.
    # After a normal restart seed_security_data has already rebuilt the system
    # roles without these codes, so this usually affects zero rows — but a
    # custom role could still hold one.
    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE code IN :codes
            )
            """
        ).bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": list(CALL_PERMISSION_CODES)},
    )

    bind.execute(
        sa.text("DELETE FROM permissions WHERE code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": list(CALL_PERMISSION_CODES)},
    )


def downgrade() -> None:
    """Restore the permission rows only.

    Role assignments are deliberately not restored: the grants were owned by
    SYSTEM_ROLES in app/rbac.py, which no longer lists these codes, so
    seed_security_data would strip them again on the next start. Re-enabling the
    call subsystem means restoring the RBAC entries in code as well, not just
    these rows.
    """
    bind = op.get_bind()
    for code, group_name, description, is_sensitive in CALL_PERMISSIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (code, group_name, description, is_sensitive)
                VALUES (:code, :group_name, :description, :is_sensitive)
                """
            ),
            {
                "code": code,
                "group_name": group_name,
                "description": description,
                "is_sensitive": is_sensitive,
            },
        )
