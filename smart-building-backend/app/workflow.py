"""Authoritative workflow definitions derived from the BAMBO pilot PRD."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StageDefinition:
    number: int
    title: str
    required_checklist: tuple[str, ...]
    required_form_fields: tuple[str, ...] = ()


STAGE_DEFINITIONS = (
    StageDefinition(
        1,
        "انتخاب پروژه مناسب برای پایلوت",
        (
            "project_active",
            "imaging_value",
            "decision_maker_available",
            "safe_access",
            "dwg_available",
            "not_demo_only",
            "cooperation_capacity",
        ),
        ("owner_name", "project_address"),
    ),
    StageDefinition(
        2,
        "معرفی و موافقت",
        (
            "introduction_completed",
            "site_coordinator_registered",
            "imaging_consent",
            "dwg_consent",
            "feedback_consent",
            "f01_result_approved",
        ),
        ("site_coordinator_phone",),
    ),
    StageDefinition(
        3,
        "دریافت DWG و اطلاعات طبقات",
        ("floors_registered", "valid_dwg_registered"),
    ),
    StageDefinition(
        4,
        "راه‌اندازی در پلتفرم اصلی",
        (
            "main_project_created",
            "floors_created",
            "main_dwg_configured",
            "typical_floors_identified",
            "start_point_registered",
            "expert_access_tested",
            "main_app_display_checked",
            "ready_for_capture",
        ),
    ),
    StageDefinition(
        5,
        "برنامه‌ریزی و تخصیص مأموریت",
        ("expert_assignment_confirmed",),
        ("scheduled_at", "expert", "floors", "site_contact"),
    ),
    StageDefinition(
        6,
        "آمادگی قبل از برداشت",
        (
            "assignment_accepted",
            "site_entry",
            "permission",
            "ppe",
            "camera",
            "connection",
            "charge",
            "storage",
            "project_floor_plan",
            "test_image",
            "no_stop_condition",
        ),
    ),
    StageDefinition(
        7,
        "اجرای برداشت طبقات",
        (
            "correct_floor",
            "start_point",
            "main_capture_started",
            "continuous_route",
            "coverage_completed",
            "capture_finished",
            "saved_in_main_app",
            "capture_times_registered",
        ),
    ),
    StageDefinition(8, "کنترل نتیجه چندطبقه", ("all_floors_resolved",)),
    StageDefinition(
        9,
        "وضعیت Upload در پلتفرم اصلی",
        (
            "all_floors_completed",
            "main_upload_started",
            "main_upload_completed",
            "correct_floor_link",
            "operations_notified",
            "mission_completed",
            "operations_confirmed",
        ),
    ),
    StageDefinition(
        10,
        "کنترل پردازش در پلتفرم اصلی",
        (
            "processing_started",
            "route_detected",
            "plan_connected",
            "tour_ready",
            "no_critical_error",
            "captures_menu_checked",
            "latest_capture_checked",
            "last_visit_checked",
        ),
    ),
    StageDefinition(
        11,
        "اطلاع‌رسانی آماده‌شدن بازدید",
        ("main_output_ready", "notification_sent", "delivery_registered"),
        ("delivery_status",),
    ),
    StageDefinition(
        12,
        "آموزش اولیه مالک",
        (
            "login",
            "project",
            "floor",
            "plan",
            "tour",
            "navigation",
            "training_completed",
            "support",
            "independent_use",
        ),
    ),
    StageDefinition(
        13,
        "موفقیت مشتری",
        ("first_follow_up", "second_follow_up", "owner_viewed", "no_open_critical_incident"),
        ("follow_up_result",),
    ),
    StageDefinition(
        14,
        "ادامه برداشت",
        (
            "new_mission",
            "stage_5_rechecked",
            "stage_6_rechecked",
            "stage_7_rechecked",
            "stage_8_rechecked",
            "stage_9_rechecked",
            "stage_10_rechecked",
            "stage_11_rechecked",
            "stage_12_rechecked",
            "stage_13_rechecked",
            "independent_result",
        ),
    ),
    StageDefinition(
        15,
        "ارزیابی",
        ("operations", "quality", "technical", "customer", "commercial", "one_page_report"),
    ),
    StageDefinition(
        16,
        "جلسه جمع‌بندی",
        ("value_clear", "need_clear", "decision_maker_clear", "blocker_clear"),
        ("decision", "decision_maker", "blocker"),
    ),
    StageDefinition(
        17,
        "پیشنهاد تجاری",
        ("proposal_text_registered",),
        (
            "project_count",
            "floor_count",
            "support_scope",
            "decision_maker",
            "follow_up_date",
        ),
    ),
    StageDefinition(
        18,
        "پیگیری",
        ("follow_up_registered",),
        ("obstacle", "action", "owner", "due_at", "result"),
    ),
    StageDefinition(
        19,
        "قرارداد یا بستن",
        ("final_result_registered", "pilot_manager_approved"),
        ("outcome",),
    ),
)

STAGES_BY_NUMBER = {stage.number: stage for stage in STAGE_DEFINITIONS}

GATE_DEFINITIONS = (
    ("G1", "پذیرش", 2),
    ("G2", "آمادگی فنی", 4),
    ("G3", "عملیات", 9),
    ("G4", "تجربه", 13),
    ("G5", "تجاری", 16),
)

PILOT_STATUS_AFTER_STAGE = {
    2: "waiting_documents",
    4: "ready_for_capture",
    9: "operations",
    10: "main_tour_processing",
    12: "ready_to_view",
    16: "evaluating",
    17: "proposal_sent",
}

FINAL_OUTCOMES = {"contract", "ready_on_date", "negotiation", "rejected", "closed"}
