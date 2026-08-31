"""Merge the customer success role into support.

Customer success, support and training are one team, so ``support`` becomes the
single role for that area. ``support`` was already "آموزش/پشتیبانی" and carried
the training side from the start — there was never a separate ``training`` role
— so this migration only has to move ``customer_success``.

Everyone holding ``customer_success`` is moved to ``support``, which by now
carries the union of both permission sets, so nobody loses an ability. A user
who held both ends up with one assignment, not a duplicate.

The role row is deactivated rather than deleted. ``audit_logs`` records role
assignments by id in its JSON payloads, and dropping the row would leave that
history pointing at nothing. ``is_active = false`` is enough to retire it:
``effective_permissions``, ``active_role_names`` and the workflow recipient
lookup all filter on it, and the frontend role selector already lists only
active roles.

Revision ID: 0023_merge_customer_success_into_support
Revises: 0022_remove_call_permissions
Create Date: 2026-08-31 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023_merge_customer_success_into_support"
down_revision: Union[str, None] = "0022_remove_call_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RETIRED_ROLE = "customer_success"
CANONICAL_ROLE = "support"
MERGED_DISPLAY_NAME = "پشتیبانی"
PREVIOUS_DISPLAY_NAME = "آموزش/پشتیبانی"


def upgrade() -> None:
    bind = op.get_bind()

    # Move assignments. The NOT EXISTS guard is what keeps a user who held both
    # roles from ending up with a duplicate support assignment.
    bind.execute(
        sa.text(
            """
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            SELECT ur.user_id, canonical.id, ur.assigned_at
            FROM user_roles ur
            JOIN roles retired ON retired.id = ur.role_id AND retired.name = :retired
            JOIN roles canonical ON canonical.name = :canonical
            WHERE NOT EXISTS (
                SELECT 1 FROM user_roles existing
                WHERE existing.user_id = ur.user_id
                  AND existing.role_id = canonical.id
            )
            """
        ),
        {"retired": RETIRED_ROLE, "canonical": CANONICAL_ROLE},
    )

    # Drop the old assignments so the retired role holds no members.
    bind.execute(
        sa.text(
            """
            DELETE FROM user_roles
            WHERE role_id IN (SELECT id FROM roles WHERE name = :retired)
            """
        ),
        {"retired": RETIRED_ROLE},
    )

    # Retire the role. Keep the row and its permission grants so historical
    # audit entries still resolve.
    bind.execute(
        sa.text(
            "UPDATE roles SET is_active = false, is_system = false "
            "WHERE name = :retired"
        ),
        {"retired": RETIRED_ROLE},
    )

    bind.execute(
        sa.text("UPDATE roles SET display_name = :name WHERE name = :canonical"),
        {"name": MERGED_DISPLAY_NAME, "canonical": CANONICAL_ROLE},
    )


def downgrade() -> None:
    """Reactivate the role and restore its display name.

    Membership is not restored: after the merge there is no record of which
    support users came from customer_success, and inventing one would hand
    people a role they may never have held. Reassign deliberately instead.
    """
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "UPDATE roles SET is_active = true, is_system = true "
            "WHERE name = :retired"
        ),
        {"retired": RETIRED_ROLE},
    )
    bind.execute(
        sa.text("UPDATE roles SET display_name = :name WHERE name = :canonical"),
        {"name": PREVIOUS_DISPLAY_NAME, "canonical": CANONICAL_ROLE},
    )
