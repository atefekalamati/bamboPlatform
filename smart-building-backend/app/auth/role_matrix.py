"""Role, stage, gate, and menu access matrix for BAMBO RBAC.

The persisted role names are kept in the existing lowercase format for backward
compatibility with the frontend and seeded data.  ``official_code`` exposes the
business-facing role code requested by the PRD/access-control matrix.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    official_code: str
    display_name: str
    data_scope: str
    menu_access: tuple[str, ...]


ROLE_DEFINITIONS: dict[str, RoleDefinition] = {
    "super_admin": RoleDefinition(
        "super_admin",
        "SUPER_ADMIN",
        "سوپر ادمین",
        "ALL",
        ("*",),
    ),
    "admin": RoleDefinition("admin", "ADMIN", "ادمین", "ALL", ("users", "roles", "access")),
    "pilot_manager": RoleDefinition(
        "pilot_manager",
        "PILOT_MANAGER",
        "مدیر پایلوت",
        "PILOT_MEMBER",
        ("pilots", "stages", "gates", "forms", "reports", "incidents"),
    ),
    "sales": RoleDefinition(
        "sales",
        "SALES",
        "جذب/فروش",
        "ROLE_RELATED",
        ("pilots", "stages", "commercial", "forms"),
    ),
    "setup": RoleDefinition(
        "setup",
        "SETUP_MANAGER",
        "مسئول راه‌اندازی",
        "ROLE_RELATED",
        ("pilots", "projects", "dwg", "stages", "forms"),
    ),
    "operations": RoleDefinition(
        "operations",
        "OPERATIONS_COORDINATOR",
        "هماهنگ‌کننده عملیات",
        "ROLE_RELATED",
        ("pilots", "missions", "stages", "gates", "incidents", "forms"),
    ),
    "capture_expert": RoleDefinition(
        "capture_expert",
        "FIELD_EXPERT",
        "کارشناس برداشت",
        "ASSIGNED",
        ("missions", "checklists", "incidents", "forms"),
    ),
    "support": RoleDefinition(
        "support",
        "SUPPORT_TRAINING",
        "آموزش/پشتیبانی",
        "ROLE_RELATED",
        ("pilots", "training", "notifications", "incidents", "forms"),
    ),
    "customer_success": RoleDefinition(
        "customer_success",
        "CUSTOMER_SUCCESS",
        "موفقیت مشتری",
        "ROLE_RELATED",
        ("pilots", "customer-success", "stages", "gates", "forms"),
    ),
    "technical": RoleDefinition(
        "technical",
        "TECHNICAL_TEAM",
        "تیم فنی",
        "ASSIGNED",
        ("incidents", "external-platform", "forms"),
    ),
    "product_manager": RoleDefinition(
        "product_manager",
        "PRODUCT_MANAGER",
        "مدیر محصول",
        "ROLE_RELATED",
        ("feedback", "reports", "incidents", "forms"),
    ),
}


STAGE_MATRIX: dict[int, dict[str, tuple[str, ...]]] = {
    1: {"edit": ("sales",), "submit": ("sales",), "approve": ("pilot_manager",)},
    2: {"edit": ("sales", "support"), "submit": ("sales", "support"), "approve": ("pilot_manager",)},
    3: {"edit": ("setup",), "submit": ("setup",), "approve": ("setup", "pilot_manager")},
    4: {"edit": ("setup",), "submit": ("setup",), "approve": ("setup",)},
    5: {"edit": ("operations",), "submit": ("operations",), "approve": ("operations",)},
    6: {"edit": ("capture_expert",), "submit": ("capture_expert",), "approve": ("operations",)},
    7: {"edit": ("capture_expert",), "submit": ("capture_expert",), "approve": ("operations",)},
    8: {"edit": ("capture_expert",), "submit": ("capture_expert",), "approve": ("operations",)},
    9: {"edit": ("capture_expert",), "submit": ("capture_expert",), "approve": ("operations",)},
    10: {"edit": ("technical",), "submit": ("technical",), "approve": ("technical", "operations")},
    11: {"edit": ("support",), "submit": ("support",), "approve": ("support",)},
    12: {"edit": ("support",), "submit": ("support",), "approve": ("support",)},
    13: {"edit": ("customer_success",), "submit": ("customer_success",), "approve": ("customer_success",)},
    14: {"edit": ("operations",), "submit": ("operations",), "approve": ("pilot_manager", "operations")},
    15: {"edit": ("pilot_manager", "customer_success"), "submit": ("pilot_manager", "customer_success"), "approve": ("pilot_manager",)},
    16: {"edit": ("customer_success", "sales"), "submit": ("customer_success", "sales"), "approve": ("pilot_manager", "sales")},
    17: {"edit": ("sales",), "submit": ("sales",), "approve": ("pilot_manager", "sales")},
    18: {"edit": ("sales",), "submit": ("sales",), "approve": ("pilot_manager", "sales")},
    19: {
        "edit": ("sales",),
        "submit": ("sales",),
        "approve": ("pilot_manager", "customer_success"),
    },
}

GATE_MATRIX: dict[str, tuple[str, ...]] = {
    "G1": ("pilot_manager",),
    "G2": ("setup",),
    "G3": ("operations",),
    "G4": ("customer_success",),
    "G5": ("pilot_manager", "sales"),
}

