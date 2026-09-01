"""Customer success, support and training are one role: ``support``.

There was never a separate ``training`` role — ``support`` was defined as
"آموزش/پشتیبانی" with official code SUPPORT_TRAINING from the start — so the
merge only had to retire ``customer_success``. These tests pin the outcome:
the union of permissions, the transferred stage and gate ownership, and the fact
that the retired role cannot come back through a reseed.
"""

import itertools

import pytest

from conftest import BOOTSTRAP_MOBILE, login_with_otp

from app.auth.role_matrix import GATE_MATRIX, ROLE_DEFINITIONS, STAGE_MATRIX
from app.database import get_session
from app.models import Role, User
from app.rbac import (
    ALL_PERMISSION_CODES,
    CUSTOMER_SUCCESS_PERMISSIONS,
    SUPPORT_PERMISSIONS,
    SYSTEM_ROLES,
)
from app.services.security import effective_permissions, seed_security_data

RETIRED = "customer_success"
CANONICAL = "support"

# Roles whose permissions this merge must not touch.
UNTOUCHED_ROLES = (
    "super_admin", "admin", "pilot_manager", "sales", "setup",
    "operations", "capture_expert", "technical", "product_manager",
)


# ------------------------------------------------------------ role definitions


def test_only_support_remains_for_this_area():
    assert RETIRED not in SYSTEM_ROLES
    assert RETIRED not in ROLE_DEFINITIONS
    assert CANONICAL in SYSTEM_ROLES
    assert SYSTEM_ROLES[CANONICAL][0] == "پشتیبانی"


def test_there_was_never_a_separate_training_role():
    """Guards the discovery this merge rested on."""
    assert "training" not in SYSTEM_ROLES
    assert "training" not in ROLE_DEFINITIONS
    assert ROLE_DEFINITIONS[CANONICAL].official_code == "SUPPORT_TRAINING"


def test_support_holds_the_union_of_both_permission_sets():
    assert CUSTOMER_SUCCESS_PERMISSIONS <= SUPPORT_PERMISSIONS, (
        "a customer success permission was dropped by the merge"
    )
    codes = SYSTEM_ROLES[CANONICAL][1]
    for code in CUSTOMER_SUCCESS_PERMISSIONS:
        assert code in codes


def test_merge_grants_no_permission_outside_the_two_sets():
    """The union and nothing more — no privilege crept in."""
    granted = set(SYSTEM_ROLES[CANONICAL][1])
    # seed adds these to every non-super_admin role, so they are expected.
    from app.rbac import NOTIFICATION_SELF_PERMISSIONS

    allowed = SUPPORT_PERMISSIONS | set(NOTIFICATION_SELF_PERMISSIONS) | {"dashboard.read"}
    assert granted <= allowed


def test_support_is_not_super_admin():
    granted = set(SYSTEM_ROLES[CANONICAL][1])
    assert granted != set(ALL_PERMISSION_CODES)
    for forbidden in ("gates.override", "stages.unlock", "audit.read",
                      "users.manage", "roles.manage", "system.manage_settings"):
        assert forbidden not in granted, f"support must not gain {forbidden}"


def test_customer_success_permission_codes_still_exist():
    """The role is gone; the permissions it named are still real."""
    for code in ("customer_success.read", "customer_success.update",
                 "customer_success.followup", "customer_success.training_record",
                 "customer_success.feedback", "customer_success.manage"):
        assert code in ALL_PERMISSION_CODES


@pytest.mark.parametrize("role", UNTOUCHED_ROLES)
def test_other_roles_are_unchanged(role):
    from app.rbac import (
        ADMIN_PERMISSIONS, FIELD_EXPERT_PERMISSIONS, OPERATIONS_PERMISSIONS,
        PILOT_MANAGER_PERMISSIONS, PRODUCT_MANAGER_PERMISSIONS, SALES_PERMISSIONS,
        SETUP_PERMISSIONS, TECHNICAL_PERMISSIONS,
    )

    expected = {
        "admin": ADMIN_PERMISSIONS, "pilot_manager": PILOT_MANAGER_PERMISSIONS,
        "sales": SALES_PERMISSIONS, "setup": SETUP_PERMISSIONS,
        "operations": OPERATIONS_PERMISSIONS, "capture_expert": FIELD_EXPERT_PERMISSIONS,
        "technical": TECHNICAL_PERMISSIONS, "product_manager": PRODUCT_MANAGER_PERMISSIONS,
    }
    if role == "super_admin":
        assert set(SYSTEM_ROLES[role][1]) == set(ALL_PERMISSION_CODES)
    else:
        assert SYSTEM_ROLES[role][1] is expected[role]


# ------------------------------------------------------- workflow and gates


def test_no_matrix_still_names_the_retired_role():
    stage_roles = {r for m in STAGE_MATRIX.values() for r in itertools.chain(*m.values())}
    gate_roles = {r for v in GATE_MATRIX.values() for r in v}
    assert RETIRED not in stage_roles
    assert RETIRED not in gate_roles
    # Every role a matrix names must be a real, live role.
    assert (stage_roles | gate_roles) <= set(SYSTEM_ROLES)


@pytest.mark.parametrize("stage", [13, 15, 16, 19])
def test_support_inherited_the_customer_success_stages(stage):
    entry = STAGE_MATRIX[stage]
    named = set(itertools.chain(*entry.values()))
    assert CANONICAL in named, f"stage {stage} lost its owner"


def test_support_inherited_gate_g4():
    assert GATE_MATRIX["G4"] == (CANONICAL,)


def test_support_keeps_its_own_stages():
    """Stages 11 and 12 were support's before the merge and stay support's."""
    for stage in (11, 12):
        assert STAGE_MATRIX[stage]["approve"] == (CANONICAL,)


# --------------------------------------------------------------- seed and API


def test_seed_is_idempotent_and_does_not_recreate_the_retired_role(client):
    with get_session() as db:
        for _ in range(3):
            seed_security_data(db)
        names = {r.name for r in db.query(Role).all()}
        assert RETIRED not in names or not (
            db.query(Role).filter(Role.name == RETIRED).one().is_active
        )
        support = db.query(Role).filter(Role.name == CANONICAL).one()
        assert support.display_name == "پشتیبانی"
        assert support.is_active is True


def test_role_api_exposes_support_and_not_a_live_retired_role(client):
    headers = login_with_otp(client, BOOTSTRAP_MOBILE)
    response = client.get("/roles", headers=headers)
    assert response.status_code == 200
    roles = response.json()

    by_name = {r["name"]: r for r in roles}
    assert CANONICAL in by_name
    assert by_name[CANONICAL]["display_name"] == "پشتیبانی"
    # If the row exists at all it must not be selectable.
    if RETIRED in by_name:
        assert by_name[RETIRED]["is_active"] is False


def test_a_support_user_gets_the_merged_permissions(client):
    headers = login_with_otp(client, BOOTSTRAP_MOBILE)
    roles = {r["name"]: r["id"] for r in client.get("/roles", headers=headers).json()}

    created = client.post(
        "/users",
        json={"mobile": "09159990001", "display_name": "پشتیبان",
              "role_ids": [roles[CANONICAL]]},
        headers=headers,
    )
    assert created.status_code == 201, created.json()
    granted = set(created.json()["permissions"])

    # Both halves of the merge are present.
    assert "customer_success.followup" in granted   # was customer_success only
    assert "incidents.create" in granted            # was support only
    assert "gates.approve" in granted               # was customer_success only
    assert "notifications.manage" in granted        # was support only


def test_effective_permissions_ignore_a_deactivated_role(client):
    """The retirement mechanism itself: inactive roles grant nothing."""
    with get_session() as db:
        user = User(mobile="+989159990002", display_name="آزمایشی")
        retired = Role(name="retired_probe", display_name="بازنشسته",
                       is_system=False, is_active=False)
        support = db.query(Role).filter(Role.name == CANONICAL).one()
        retired.permissions = list(support.permissions)
        user.roles.append(retired)
        db.add_all([user, retired])
        db.commit()
        assert effective_permissions(user) == set()
