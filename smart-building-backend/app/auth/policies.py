"""Central policy helpers for role, stage, gate, and bootstrap access."""

from __future__ import annotations

from app.auth.role_matrix import GATE_MATRIX, ROLE_DEFINITIONS, STAGE_MATRIX
from app.models import Role, User


def active_role_names(user: User) -> set[str]:
    return {role.name for role in user.roles if role.is_active}


def role_names_from_role(role: Role) -> set[str]:
    return {role.name} if role.is_active else set()


def is_super_admin_role_names(role_names: set[str]) -> bool:
    return "super_admin" in role_names


def can_review_stage(
    role_names: set[str],
    stage_number: int,
    action: str,
) -> bool:
    """Authorize the configured reviewer or the general-manager substitute."""
    if action not in {"approve", "reject"}:
        return False
    if is_super_admin_role_names(role_names):
        return stage_number in STAGE_MATRIX
    allowed_roles = STAGE_MATRIX.get(stage_number, {}).get("approve", ())
    return bool(role_names.intersection(allowed_roles))


def can_submit_stage(role_names: set[str], stage_number: int) -> bool:
    if is_super_admin_role_names(role_names):
        return stage_number in STAGE_MATRIX
    allowed_roles = STAGE_MATRIX.get(stage_number, {}).get("submit", ())
    return bool(role_names.intersection(allowed_roles))


def scopes_for_roles(role_names: set[str]) -> list[str]:
    if is_super_admin_role_names(role_names):
        return ["ALL"]
    scopes = {
        ROLE_DEFINITIONS[name].data_scope
        for name in role_names
        if name in ROLE_DEFINITIONS
    }
    return sorted(scopes or {"READ_ONLY"})


def menu_access_for_roles(role_names: set[str]) -> list[str]:
    if is_super_admin_role_names(role_names):
        return ["*"]
    menus: set[str] = set()
    for name in role_names:
        definition = ROLE_DEFINITIONS.get(name)
        if definition:
            menus.update(definition.menu_access)
    return sorted(menus)


def stage_access_for_roles(role_names: set[str]) -> dict[str, list[int]]:
    access = {"edit": [], "submit": [], "review": [], "approve": [], "reject": []}
    if is_super_admin_role_names(role_names):
        all_stages = sorted(STAGE_MATRIX)
        return {key: all_stages for key in access}
    for stage_number, rules in STAGE_MATRIX.items():
        for action, allowed_roles in rules.items():
            if role_names.intersection(allowed_roles):
                access[action].append(stage_number)
        if role_names.intersection(rules.get("approve", ())):
            access["review"].append(stage_number)
            access["reject"].append(stage_number)
    return {key: sorted(set(value)) for key, value in access.items()}


def gate_access_for_roles(role_names: set[str]) -> dict[str, list[str]]:
    access = {"read": sorted(GATE_MATRIX), "approve": [], "reject": [], "override": []}
    if is_super_admin_role_names(role_names):
        gates = sorted(GATE_MATRIX)
        return {"read": gates, "approve": gates, "reject": gates, "override": gates}
    for gate_code, allowed_roles in GATE_MATRIX.items():
        if role_names.intersection(allowed_roles):
            access["approve"].append(gate_code)
            access["reject"].append(gate_code)
    return {key: sorted(value) for key, value in access.items()}


def role_metadata(role_names: set[str]) -> list[dict[str, str]]:
    result = []
    for name in sorted(role_names):
        definition = ROLE_DEFINITIONS.get(name)
        result.append(
            {
                "name": name,
                "official_code": definition.official_code if definition else name.upper(),
                "display_name": definition.display_name if definition else name,
                "scope": definition.data_scope if definition else "READ_ONLY",
            }
        )
    return result


def access_preview(role_names: set[str], permissions: set[str]) -> dict:
    return {
        "roles": role_metadata(role_names),
        "permissions": sorted(permissions),
        "scopes": scopes_for_roles(role_names),
        "menu_access": menu_access_for_roles(role_names),
        "stage_access": stage_access_for_roles(role_names),
        "gate_access": gate_access_for_roles(role_names),
        "operations": sorted(permissions),
    }

