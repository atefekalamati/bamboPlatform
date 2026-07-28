"""Canonical BAMBO permission and system-role definitions."""

PERMISSIONS = (
    ("users.read", "Users", "مشاهده کاربران", False),
    ("users.manage", "Users", "ایجاد و مدیریت کاربران", True),
    ("roles.read", "Roles", "مشاهده نقش‌ها و دسترسی‌ها", False),
    ("roles.manage", "Roles", "ایجاد نقش و تغییر Permission", True),
    ("pilots.read", "Pilots", "مشاهده پرونده‌های پایلوت", False),
    ("pilots.create", "Pilots", "ایجاد پرونده پایلوت", False),
    ("pilots.manage", "Pilots", "ویرایش و مدیریت پرونده پایلوت", True),
    ("stage1.manage", "Stage 1", "مدیریت مرحله اول", False),
    ("forms.manage", "Forms", "ثبت و ویرایش F01 تا F05", False),
    ("dwg.manage", "DWG", "ثبت و نسخه‌بندی DWG", True),
    ("missions.manage", "Missions", "مدیریت مأموریت‌ها", False),
    ("checklists.manage", "Checklists", "ثبت چک‌لیست و ارسال مرحله", False),
    ("gate_approval.approve", "Gate Approval", "تأیید Gate و مرحله", True),
    ("gate_approval.reject", "Gate Approval", "رد Gate و مرحله", True),
    ("incidents.manage", "Incidents", "ثبت و مدیریت رخدادها", False),
    ("customer_success.manage", "Customer Success", "مدیریت موفقیت مشتری", False),
    ("commercial.manage", "Commercial", "پیشنهاد و نتیجه تجاری", False),
    ("reports.read", "Reports", "مشاهده گزارش‌ها و KPI", False),
    ("audit.read", "Audit", "مشاهده Audit Log", True),
)

ALL_PERMISSION_CODES = {item[0] for item in PERMISSIONS}

SYSTEM_ROLES = {
    "super_admin": ("مدیر کل", ALL_PERMISSION_CODES),
    "admin": (
        "ادمین",
        {
            "users.read",
            "users.manage",
            "roles.read",
            "roles.manage",
            "pilots.read",
            "pilots.create",
            "pilots.manage",
        },
    ),
    "pilot_manager": (
        "مدیر پایلوت",
        {
            "pilots.read",
            "pilots.create",
            "pilots.manage",
            "checklists.manage",
            "gate_approval.approve",
            "gate_approval.reject",
            "reports.read",
        },
    ),
    "sales": (
        "جذب و فروش",
        {
            "pilots.read",
            "pilots.create",
            "stage1.manage",
            "forms.manage",
            "checklists.manage",
            "commercial.manage",
        },
    ),
    "setup": ("مسئول راه‌اندازی", {"pilots.read", "forms.manage", "dwg.manage", "checklists.manage"}),
    "operations": (
        "هماهنگ‌کننده عملیات",
        {"pilots.read", "missions.manage", "checklists.manage", "gate_approval.approve"},
    ),
    "capture_expert": (
        "کارشناس برداشت",
        {"pilots.read", "missions.manage", "checklists.manage", "incidents.manage"},
    ),
    "support": (
        "پشتیبانی و آموزش",
        {"pilots.read", "checklists.manage", "incidents.manage"},
    ),
    "customer_success": (
        "موفقیت مشتری",
        {
            "pilots.read",
            "forms.manage",
            "customer_success.manage",
            "gate_approval.approve",
        },
    ),
    "technical": ("تیم فنی", {"pilots.read", "incidents.manage"}),
    "product_manager": (
        "مدیر محصول",
        {"pilots.read", "incidents.manage", "reports.read"},
    ),
}
