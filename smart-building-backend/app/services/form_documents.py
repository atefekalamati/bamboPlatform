"""Aggregate official BAMBO forms from the existing operational data model."""

from __future__ import annotations

from datetime import UTC, date, datetime
from html import escape
from typing import Any

from persiantools.jdatetime import JalaliDateTime
from sqlalchemy.orm import Session

from app.exceptions import SecurityError
from app.models import (
    CommercialProposal,
    CustomerFollowUp,
    DwgVersion,
    FinalOutcome,
    FormF01,
    FormF02,
    FormF03,
    FormF04,
    Incident,
    Mission,
    Pilot,
    User,
)
from app.schemas.forms import (
    FormDocument,
    FormFieldMapping,
    FormInstanceSummary,
    FormMissingField,
    FormSummary,
)

FORM_META = {
    "F01": ("BAMBO-PILOT-F01", "پذیرش و اطلاعات اولیه پایلوت"),
    "F02": ("BAMBO-PILOT-F02", "دریافت نقشه و راه‌اندازی پروژه"),
    "F03": ("BAMBO-PILOT-F03", "مأموریت، برداشت و بارگذاری"),
    "F04": ("BAMBO-PILOT-F04", "موفقیت مشتری و تبدیل به قرارداد"),
    "F05": ("BAMBO-PILOT-F05", "ثبت رخداد و اقدام اصلاحی"),
}

ENUM_LABELS = {
    "approved": "تأیید شد",
    "complete_information": "نیازمند تکمیل اطلاعات",
    "referred": "ارجاع شد",
    "rejected": "رد شد",
    "normal": "عادی",
    "important": "مهم",
    "critical": "بحرانی",
    "safety": "ایمنی",
    "equipment": "تجهیزات",
    "dwg": "فایل یا بارگذاری",
    "main_platform": "سامانه",
    "access": "دسترسی",
    "customer": "مشتری",
    "process": "فرایند",
    "open": "باز",
    "contained": "مهارشده",
    "resolved": "رفع شد",
    "closed": "بسته شد",
    "completed": "انجام شد",
    "not_started": "شروع نشده",
    "incomplete": "ناقص",
    "not_done": "انجام نشد",
    "needs_revision": "نیازمند اصلاح",
    "contract": "قرارداد شد",
    "ready_on_date": "آماده در تاریخ مشخص",
    "negotiation": "مذاکره ادامه دارد",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _jalali(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=UTC)
        return JalaliDateTime(aware).strftime("%Y/%m/%d - %H:%M")
    return JalaliDateTime(value.year, value.month, value.day).strftime("%Y/%m/%d")


def _label(value: Any) -> Any:
    if isinstance(value, bool):
        return "بله" if value else "خیر"
    return ENUM_LABELS.get(value, value)


def _name(user: User | None) -> str | None:
    return user.display_name if user else None


def _user_names(db: Session, ids: set[int | None]) -> dict[int, str]:
    clean_ids = {item for item in ids if item is not None}
    if not clean_ids:
        return {}
    return {
        user.id: user.display_name
        for user in db.query(User).filter(User.id.in_(clean_ids)).all()
    }


def _require_pilot(db: Session, pilot_id: int) -> Pilot:
    pilot = db.get(Pilot, pilot_id)
    if pilot is None:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    return pilot


def _require_mission(db: Session, pilot: Pilot, mission_id: int) -> Mission:
    mission = db.get(Mission, mission_id)
    if mission is None or mission.pilot_id != pilot.id:
        raise SecurityError(
            "MISSION_NOT_FOUND",
            "مأموریت برای این پرونده پیدا نشد.",
            404,
            [],
        )
    return mission


def _require_incident(db: Session, pilot: Pilot, incident_id: int) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None or incident.pilot_id != pilot.id:
        raise SecurityError(
            "INCIDENT_NOT_FOUND",
            "رخداد برای این پرونده پیدا نشد.",
            404,
            [],
        )
    return incident


def _missing(
    missing_fields: list[FormMissingField],
    field: str,
    label: str,
    value: Any,
) -> None:
    if value is None or value == "" or value == []:
        missing_fields.append(FormMissingField(field=field, label=label))


def _mapping(
    form: str,
    section: str,
    field: str,
    source_model: str,
    source_field: str,
    transformation: str = "DIRECT",
    source_stage: str | None = None,
    policy: str = "empty_field",
) -> FormFieldMapping:
    return FormFieldMapping(
        form=form,
        section=section,
        field=field,
        source_model=source_model,
        source_field=source_field,
        source_stage=source_stage,
        transformation=transformation,
        missing_data_policy=policy,
    )


def _base_document(
    pilot: Pilot,
    form_code: str,
    data: dict[str, Any],
    missing_fields: list[FormMissingField],
    mapping: list[FormFieldMapping],
) -> FormDocument:
    document_code, title = FORM_META[form_code]
    return FormDocument(
        form_code=form_code,
        document_code=document_code,
        title=title,
        pilot_id=pilot.id,
        pilot_code=pilot.code,
        is_complete=not missing_fields,
        missing_fields=missing_fields,
        mapping=mapping,
        data=data,
        generated_at=_now(),
    )


def build_f01(db: Session, pilot_id: int) -> FormDocument:
    pilot = _require_pilot(db, pilot_id)
    project = pilot.project
    owner = project.owner if project else None
    form: FormF01 | None = pilot.form_f01
    users = _user_names(
        db,
        {
            form.case_owner_user_id if form else None,
            form.sales_user_id if form else None,
            form.pilot_manager_user_id if form else None,
        },
    )
    missing: list[FormMissingField] = []
    for field, label, value in (
        ("general.case_code", "کد پرونده", pilot.code),
        ("project.owner_name", "نام مالک یا شرکت", owner.name if owner else None),
        ("project.name", "نام پروژه", project.name if project else None),
        ("acceptance.result", "نتیجه پذیرش", form.result if form else None),
    ):
        _missing(missing, field, label, value)
    data = {
        "اطلاعات عمومی": {
            "کد پرونده": pilot.code,
            "تاریخ تشکیل": _jalali(pilot.created_at),
            "مسئول پرونده": users.get(form.case_owner_user_id) if form else None,
        },
        "بخش الف: اطلاعات مالک و پروژه": {
            "نام مالک یا شرکت": owner.name if owner else None,
            "نام تصمیم‌گیرنده و سمت": (
                f"{owner.decision_maker_name} - {owner.decision_maker_position}"
                if owner
                else None
            ),
            "شماره تماس": owner.primary_mobile if owner else None,
            "نام پروژه": project.name if project else None,
            "تعداد طبقات": project.total_floors if project else None,
            "نشانی پروژه": project.address if project else None,
            "مرحله پیشرفت": project.progress_stage if project else None,
            "نیاز یا مسئله اصلی مشتری": project.customer_need if project else None,
            "ارزش مورد انتظار از BAMBO": project.expected_value if project else None,
        },
        "بخش ب: تناسب پایلوت": {
            "پروژه فعال": form.project_active if form else None,
            "نیاز مشاهده غیرحضوری": form.remote_viewing_need if form else None,
            "دسترسی ممکن": form.access_possible if form else None,
            "نقشه قابل دریافت": form.dwg_available if form else None,
            "ظرفیت همکاری بعدی": form.continued_capacity if form else None,
        },
        "بخش ج: موافقت و هماهنگی": {
            "معرفی پایلوت انجام شد": form.introduction_completed if form else None,
            "موافقت تصویربرداری اخذ شد": form.imaging_accepted if form else None,
            "ارائه نقشه پذیرفته شد": form.dwg_accepted if form else None,
            "ارائه بازخورد پذیرفته شد": form.feedback_accepted if form else None,
            "نام هماهنگ‌کننده محل": form.coordinator_name if form else None,
            "شماره تماس": form.coordinator_mobile if form else None,
            "محدودیت ورود، تصویربرداری یا محرمانگی": form.limitation if form else None,
        },
        "نتیجه پذیرش": {
            "نتیجه": _label(form.result) if form else None,
            "ارجاع به": users.get(form.sales_user_id) if form else None,
            "مهلت اقدام بعدی": _jalali(form.referral_deadline) if form else None,
            "نام مسئول جذب یا فروش": users.get(form.sales_user_id) if form else None,
            "تأیید مدیر پایلوت": users.get(form.pilot_manager_user_id) if form else None,
            "تاریخ و ساعت ارجاع": _jalali(form.referred_at) if form else None,
        },
    }
    mapping = [
        _mapping("F01", "اطلاعات عمومی", "کد پرونده", "Pilot", "code"),
        _mapping("F01", "اطلاعات مالک", "نام مالک", "Owner", "name"),
        _mapping("F01", "تناسب پایلوت", "Checkboxها", "FormF01", "*", "AGGREGATED", "1-2"),
    ]
    return _base_document(pilot, "F01", data, missing, mapping)


def build_f02(db: Session, pilot_id: int) -> FormDocument:
    pilot = _require_pilot(db, pilot_id)
    project = pilot.project
    form: FormF02 | None = pilot.form_f02
    users = _user_names(
        db,
        {
            form.responsible_user_id if form else None,
            form.configured_by_user_id if form else None,
            form.controlled_by_user_id if form else None,
        },
    )
    floors = list(project.floors) if project else []
    rows = []
    for index, floor in enumerate(floors, start=1):
        versions: list[DwgVersion] = floor.dwg_file.versions if floor.dwg_file else []
        latest = versions[-1] if versions else None
        rows.append(
            {
                "ردیف": index,
                "نام یا نوع پلان": floor.name,
                "فرمت": latest.mime_type if latest else None,
                "نسخه یا تاریخ": (
                    f"{latest.version} - {_jalali(latest.uploaded_at)}" if latest else None
                ),
                "طبقات مرتبط": floor.code,
                "تأیید خوانایی": latest.is_readable if latest else floor.dwg_reference_confirmed,
            }
        )
    missing: list[FormMissingField] = []
    _missing(missing, "setup.form", "فرم راه‌اندازی", form)
    _missing(missing, "plans.rows", "جدول پلان‌ها", rows)
    data = {
        "اطلاعات عمومی": {
            "کد پرونده": pilot.code,
            "نام پروژه": project.name if project else None,
            "مسئول راه‌اندازی": users.get(form.responsible_user_id) if form else None,
        },
        "بخش الف: بسته اطلاعاتی": {
            "نام و نشانی": bool(project and project.name and project.address),
            "تعداد طبقات": bool(project and project.total_floors),
            "وضعیت پیشرفت": bool(project and project.progress_stage),
            "تماس مالک": bool(project and project.owner and project.owner.primary_mobile),
            "تماس هماهنگ‌کننده": bool(form and form.contacts_summary),
            "محدودیت‌ها": bool(form and form.limitation),
        },
        "بخش ب: جدول تطبیق پلان و طبقه": rows,
        "بخش ج: کنترل راه‌اندازی در سامانه": {
            "پروژه با نام استاندارد ایجاد شد": form.main_project_registered if form else None,
            "طبقات به ترتیب صحیح تعریف شدند": form.floor_order_confirmed if form else None,
            "طبقات تیپ یا غیرتیپ مشخص شدند": form.typical_floors_identified if form else None,
            "پلان صحیح هر طبقه بارگذاری شد": form.plan_connections_registered if form else None,
            "نقطه شروع پیشنهادی ثبت شد": form.start_point_registered if form else None,
            "دسترسی کارشناس فعال شد": form.expert_access_tested if form else None,
            "نمایش در اپلیکیشن آزمایش شد": form.main_app_display_tested if form else None,
            "پروژه آماده برداشت شد": form.ready_for_capture if form else None,
            "ابهام، نقص یا توضیحات": form.ambiguity if form else None,
            "تاریخ و ساعت آماده‌شدن": _jalali(form.configured_at) if form else None,
            "ارجاع به هماهنگ‌کننده عملیات": _jalali(form.referred_at) if form else None,
            "تنظیم‌کننده پروژه": users.get(form.configured_by_user_id) if form else None,
            "کنترل‌کننده نمایش در اپ": users.get(form.controlled_by_user_id) if form else None,
        },
    }
    mapping = [
        _mapping("F02", "پلان‌ها", "جدول پلان و طبقه", "Floor/DwgVersion", "*", "AGGREGATED", "3-4"),
        _mapping("F02", "کنترل راه‌اندازی", "Checkboxها", "FormF02", "*", "DIRECT", "4"),
    ]
    return _base_document(pilot, "F02", data, missing, mapping)


def build_f03(db: Session, pilot_id: int, mission_id: int) -> FormDocument:
    pilot = _require_pilot(db, pilot_id)
    mission = _require_mission(db, pilot, mission_id)
    form: FormF03 | None = mission.form_f03
    incidents = [item for item in pilot.incidents if item.mission_id == mission.id]
    rows = [
        {
            "طبقه": state.floor.name,
            "شروع": _jalali(state.capture_started_at),
            "پایان": _jalali(state.capture_finished_at),
            "پوشش کامل": state.coverage_completed,
            "ذخیره": state.saved_in_main_app,
            "بارگذاری": state.main_upload_completed,
            "توضیح یا علت عدم انجام": state.failure_reason,
        }
        for state in mission.floor_states
    ]
    missing: list[FormMissingField] = []
    _missing(missing, "mission.form_f03", "فرم کنترل مأموریت", form)
    _missing(missing, "mission.floors", "گزارش طبقات مأموریت", rows)
    data = {
        "اطلاعات عمومی": {
            "کد مأموریت یا پروژه": mission.code,
            "کارشناس": _name(mission.expert),
            "تاریخ و ساعت": f"{_jalali(mission.scheduled_start)} تا {_jalali(mission.scheduled_end)}",
            "نشانی یا Location": mission.location,
            "تماس محل": f"{mission.site_contact_name} - {mission.site_contact_mobile}",
        },
        "بخش الف: برنامه مأموریت": {
            "ورود تأیید شد": form.site_entry_confirmed if form else None,
            "طبقات مشخص‌اند": bool(mission.floor_states),
            "محدودیت ثبت شد": bool(mission.limitation),
            "مجوز لازم موجود است": form.permission_confirmed if form else None,
            "مأموریت دریافت شد": form.assignment_accepted if form else None,
        },
        "بخش ب: کنترل پیش از ضبط": {
            "تجهیزات حفاظت فردی": form.ppe_ready if form else None,
            "نصب محکم و زاویه دوربین": form.camera_ready if form else None,
            "اتصال دوربین به اپ": form.main_app_connected if form else None,
            "شارژ کافی دوربین و موبایل": form.battery_ready if form else None,
            "حافظه کافی": form.storage_ready if form else None,
            "پروژه و طبقه صحیح": form.project_floor_plan_confirmed if form else None,
            "پلان صحیح": form.project_floor_plan_confirmed if form else None,
            "تست تصویر واضح و پایدار": form.test_image_completed if form else None,
        },
        "بخش ج: گزارش طبقات": rows,
        "بخش د: پایان مأموریت": {
            "همه فایل‌ها کامل‌اند": all(row["بارگذاری"] for row in rows) if rows else None,
            "طبقات صحیح‌اند": all(state.correct_floor for state in mission.floor_states) if rows else None,
            "Upload Complete": all(state.main_upload_completed for state in mission.floor_states) if rows else None,
            "عملیات مطلع شد": form.operations_confirmed if form else None,
            "رخداد ندارد": not incidents,
            "F05 پیوست شد": bool(incidents),
            "توضیحات نهایی": form.stop_condition_reason if form else None,
            "کارشناس برداشت": _name(mission.expert),
            "تأیید هماهنگ‌کننده عملیات": form.operations_confirmed if form else None,
            "تاریخ و ساعت پایان": _jalali(form.finished_at) if form else None,
        },
    }
    mapping = [
        _mapping("F03", "مأموریت", "برنامه مأموریت", "Mission", "*", "DIRECT", "5"),
        _mapping("F03", "طبقات", "گزارش طبقات", "MissionFloor", "*", "AGGREGATED", "7-9"),
    ]
    return _base_document(pilot, "F03", data, missing, mapping)


def build_f04(db: Session, pilot_id: int) -> FormDocument:
    pilot = _require_pilot(db, pilot_id)
    project = pilot.project
    form: FormF04 | None = pilot.form_f04
    proposal: CommercialProposal | None = pilot.commercial_proposal
    outcome: FinalOutcome | None = pilot.final_outcome
    followups: list[CustomerFollowUp] = list(pilot.customer_follow_ups)
    users = _user_names(
        db,
        {
            form.responsible_user_id if form else None,
            form.customer_success_user_id if form else None,
            form.sales_user_id if form else None,
            form.pilot_manager_user_id if form else None,
            proposal.responsible_user_id if proposal else None,
            outcome.responsible_user_id if outcome else None,
            outcome.approved_by_user_id if outcome else None,
        },
    )
    missing: list[FormMissingField] = []
    _missing(missing, "customer_success.form_f04", "فرم موفقیت مشتری", form)
    data = {
        "اطلاعات عمومی": {
            "کد پرونده": pilot.code,
            "مالک یا شرکت": project.owner.name if project and project.owner else None,
            "مسئول پیگیری": users.get(form.responsible_user_id) if form else None,
        },
        "بخش الف: پیگیری ۲۴ ساعت اول": {
            "پیام تحویل شد": any(item.status == "delivered" for item in pilot.notifications),
            "مالک وارد شد": form.owner_logged_in if form else None,
            "پروژه باز شد": form.project_opened if form else None,
            "تور مشاهده شد": form.main_tour_viewed if form else None,
            "آموزش موفق": form.training_completed if form else None,
            "مشاهده موفق": form.viewing_result == "مشاهده موفق" if form else None,
            "نیازمند آموزش": form.viewing_result == "نیازمند آموزش" if form else None,
            "مشکل فنی": form.viewing_result == "مشکل فنی" if form else None,
            "هنوز مشاهده نکرده": form.viewing_result == "هنوز مشاهده نکرده" if form else None,
            "عدم پاسخ": form.viewing_result == "عدم پاسخ" if form else None,
            "نوع مشکل یا ارجاع به": form.issue_category if form else None,
            "مسئول و موعد حل": (
                f"{users.get(form.issue_owner_user_id, '')} - {_jalali(form.issue_due_at)}"
                if form and form.issue_owner_user_id
                else None
            ),
        },
        "بخش ب: پیگیری روز ۳ تا ۵": {
            "آیا مشاهده غیرحضوری مفید بود؟": form.useful if form else None,
            "پوشش مسیر و کیفیت تصویر": (
                f"{form.coverage_score or ''} / {form.quality_score or ''}" if form else None
            ),
            "مفیدترین بخش BAMBO": form.most_useful_part if form else None,
            "بخش مورد انتظار که ثبت نشده": form.missing_part if form else None,
            "کاربران یا افراد دیگر": form.other_users if form else None,
            "نیاز به آموزش بیشتر": form.more_training_needed if form else None,
            "رضایت از ۱۰": form.satisfaction_score if form else None,
            "تمایل به ادامه": form.continuation_interest if form else None,
            "آمادگی دریافت پیشنهاد": form.proposal_ready if form else None,
            "پیگیری‌ها": [
                {
                    "بازه": item.schedule_slot,
                    "مانع": item.obstacle,
                    "اقدام": item.action,
                    "نتیجه": item.result,
                    "موعد": _jalali(item.due_at),
                }
                for item in followups
            ],
        },
        "بخش ج: جمع‌بندی تجاری": {
            "ارزش واقعی ایجادشده برای مشتری": (
                form.realized_value if form and form.realized_value else None
            ),
            "مانع اصلی خرید": form.purchase_blocker if form else None,
            "تعداد پروژه‌ها": proposal.project_count if proposal else form.project_count if form else None,
            "تناوب برداشت": proposal.frequency if proposal else form.usage_frequency if form else None,
            "تعداد کاربران": proposal.user_count if proposal else form.user_count if form else None,
            "تصمیم‌گیرنده نهایی": proposal.decision_maker if proposal else form.decision_maker if form else None,
            "تاریخ اقدام یا تصمیم بعدی": _jalali(proposal.follow_up_at) if proposal else None,
            "نتیجه نهایی": _label(outcome.outcome) if outcome else form.final_result if form else None,
            "علت نتیجه و اقدام بعدی": outcome.reason if outcome else form.final_reason if form else None,
            "مسئول موفقیت مشتری": users.get(form.customer_success_user_id) if form else None,
            "مسئول فروش": users.get(form.sales_user_id) if form else None,
            "تأیید مدیر پایلوت": (
                users.get(outcome.approved_by_user_id)
                if outcome and outcome.pilot_manager_approved
                else users.get(form.pilot_manager_user_id) if form else None
            ),
        },
    }
    mapping = [
        _mapping("F04", "موفقیت مشتری", "پیگیری ۲۴ ساعت", "FormF04/Notification", "*", "AGGREGATED", "11-13"),
        _mapping("F04", "جمع‌بندی تجاری", "پیشنهاد و نتیجه", "CommercialProposal/FinalOutcome", "*", "LATEST_VALUE", "17-19"),
    ]
    return _base_document(pilot, "F04", data, missing, mapping)


def build_f05(db: Session, pilot_id: int, incident_id: int) -> FormDocument:
    pilot = _require_pilot(db, pilot_id)
    incident = _require_incident(db, pilot, incident_id)
    users = _user_names(
        db,
        {
            incident.reported_by_user_id,
            incident.owner_user_id,
            incident.closed_by_user_id,
        },
    )
    missing: list[FormMissingField] = []
    _missing(missing, "incident.description", "شرح دقیق رخداد", incident.description)
    data = {
        "اطلاعات": {
            "شماره رخداد": incident.code,
            "کد پروژه یا مأموریت": incident.mission.code if incident.mission else pilot.code,
            "تاریخ و ساعت": _jalali(incident.occurred_at),
            "ثبت‌کننده": users.get(incident.reported_by_user_id),
            "محل یا مرحله وقوع": f"Stage {incident.stage_number}",
        },
        "سطح و نوع رخداد": {
            "سطح": _label(incident.severity),
            "نوع": _label(incident.incident_type),
        },
        "شرح و اقدام": {
            "شرح دقیق رخداد": incident.description,
            "محل وقوع": incident.mission.location if incident.mission else None,
            "اثر رخداد": incident.result,
            "اقدام فوری برای مهار": incident.containment_action,
            "افراد یا واحدهای مطلع‌شده": "، ".join(incident.notified_people or []),
            "زمان اطلاع": _jalali(incident.created_at),
            "علت ریشه‌ای یا علت محتمل": incident.root_cause,
            "اقدام اصلاحی یا پیشگیرانه": incident.corrective_action,
            "مسئول اقدام": users.get(incident.owner_user_id),
            "موعد": _jalali(incident.correction_due_at or incident.response_due_at),
        },
        "نتیجه": {
            "رفع شد": incident.status in {"resolved", "closed"},
            "راه‌حل موقت": incident.status == "contained",
            "برداشت مجدد": False,
            "در انتظار فنی": incident.status == "open",
            "توقف پایلوت": False,
            "شاهد کنترل اثربخشی": incident.evidence,
            "درس‌آموخته": incident.lessons_learned,
            "ثبت‌کننده": users.get(incident.reported_by_user_id),
            "مسئول اقدام اصلاحی": users.get(incident.owner_user_id),
            "تأیید بستن توسط مدیر پایلوت": users.get(incident.closed_by_user_id),
        },
    }
    mapping = [
        _mapping("F05", "رخداد", "اطلاعات رخداد", "Incident", "*", "DIRECT"),
        _mapping("F05", "مأموریت", "محل وقوع", "Mission", "location", "USER_REFERENCE"),
    ]
    return _base_document(pilot, "F05", data, missing, mapping)


def list_forms(db: Session, pilot_id: int) -> list[FormSummary]:
    pilot = _require_pilot(db, pilot_id)
    documents = [build_f01(db, pilot_id), build_f02(db, pilot_id), build_f04(db, pilot_id)]
    mission_instances = [
        FormInstanceSummary(
            id=mission.id,
            code=mission.code,
            title=mission.code,
            is_complete=bool(mission.form_f03),
            last_changed=mission.updated_at,
            href=f"/pilots/{pilot.id}/forms/f03/{mission.id}",
            print_href=f"/pilots/{pilot.id}/forms/f03/{mission.id}/print",
            pdf_href=f"/pilots/{pilot.id}/forms/f03/{mission.id}/pdf",
        )
        for mission in pilot.missions
    ]
    incident_instances = [
        FormInstanceSummary(
            id=incident.id,
            code=incident.code,
            title=incident.code,
            is_complete=True,
            last_changed=incident.updated_at,
            href=f"/pilots/{pilot.id}/forms/f05/{incident.id}",
            print_href=f"/pilots/{pilot.id}/forms/f05/{incident.id}/print",
            pdf_href=f"/pilots/{pilot.id}/forms/f05/{incident.id}/pdf",
        )
        for incident in pilot.incidents
    ]
    summaries = [
        FormSummary(
            form_code=document.form_code,
            document_code=document.document_code,
            title=document.title,
            is_complete=document.is_complete,
            status_label="کامل" if document.is_complete else "ناقص",
            printable_count=1,
            last_changed=pilot.updated_at,
            missing_fields=document.missing_fields,
            instances=[
                FormInstanceSummary(
                    title=document.title,
                    is_complete=document.is_complete,
                    last_changed=pilot.updated_at,
                    href=f"/pilots/{pilot.id}/forms/{document.form_code.lower()}/preview",
                    print_href=f"/pilots/{pilot.id}/forms/{document.form_code.lower()}/print",
                    pdf_href=f"/pilots/{pilot.id}/forms/{document.form_code.lower()}/pdf",
                )
            ],
        )
        for document in documents[:2]
    ]
    summaries.append(
        FormSummary(
            form_code="F03",
            document_code=FORM_META["F03"][0],
            title=FORM_META["F03"][1],
            status_label=f"{len(mission_instances)} مأموریت",
            is_complete=all(item.is_complete for item in mission_instances) if mission_instances else False,
            printable_count=len(mission_instances),
            last_changed=max((item.last_changed for item in mission_instances if item.last_changed), default=None),
            instances=mission_instances,
            missing_fields=[] if mission_instances else [FormMissingField(field="missions", label="مأموریت")],
        )
    )
    f04 = documents[2]
    summaries.append(
        FormSummary(
            form_code="F04",
            document_code=f04.document_code,
            title=f04.title,
            status_label="کامل" if f04.is_complete else "ناقص",
            is_complete=f04.is_complete,
            printable_count=1,
            last_changed=pilot.updated_at,
            missing_fields=f04.missing_fields,
            instances=[
                FormInstanceSummary(
                    title=f04.title,
                    is_complete=f04.is_complete,
                    last_changed=pilot.updated_at,
                    href=f"/pilots/{pilot.id}/forms/f04/preview",
                    print_href=f"/pilots/{pilot.id}/forms/f04/print",
                    pdf_href=f"/pilots/{pilot.id}/forms/f04/pdf",
                )
            ],
        )
    )
    summaries.append(
        FormSummary(
            form_code="F05",
            document_code=FORM_META["F05"][0],
            title=FORM_META["F05"][1],
            status_label=f"{len(incident_instances)} رخداد" if incident_instances else "رخدادی ثبت نشده است",
            is_complete=True,
            printable_count=len(incident_instances),
            last_changed=max((item.last_changed for item in incident_instances if item.last_changed), default=None),
            instances=incident_instances,
        )
    )
    return summaries


def get_document(db: Session, pilot_id: int, form_code: str, item_id: int | None = None) -> FormDocument:
    normalized = form_code.upper()
    if normalized == "F01":
        return build_f01(db, pilot_id)
    if normalized == "F02":
        return build_f02(db, pilot_id)
    if normalized == "F03" and item_id is not None:
        return build_f03(db, pilot_id, item_id)
    if normalized == "F04":
        return build_f04(db, pilot_id)
    if normalized == "F05" and item_id is not None:
        return build_f05(db, pilot_id, item_id)
    raise SecurityError("FORM_NOT_FOUND", "فرم درخواستی پیدا نشد.", 404, [])


def form_filename(document: FormDocument, suffix: str) -> str:
    code = document.data.get("اطلاعات", {}).get("شماره رخداد")
    mission = document.data.get("اطلاعات عمومی", {}).get("کد مأموریت یا پروژه")
    extra = code or (mission if document.form_code == "F03" else None)
    parts = [document.pilot_code]
    if extra and extra != document.pilot_code:
        parts.append(str(extra))
    parts.append(document.form_code)
    return "_".join(parts).replace("/", "-") + suffix


def render_form_html(document: FormDocument, *, print_mode: bool = False) -> str:
    body_parts = []
    for section, value in document.data.items():
        body_parts.append(f"<section class='form-section'><h2>{escape(section)}</h2>")
        if isinstance(value, list):
            body_parts.append(_table(value))
        else:
            body_parts.append("<dl class='form-grid'>")
            for key, item in value.items():
                body_parts.append(
                    f"<dt>{escape(str(key))}</dt><dd>{_render_value(item)}</dd>"
                )
            body_parts.append("</dl>")
        body_parts.append("</section>")
    if document.missing_fields:
        body_parts.append("<section class='form-section screen-only'><h2>فیلدهای ناقص</h2><ul>")
        for item in document.missing_fields:
            body_parts.append(f"<li>{escape(item.label)} <small>{escape(item.field)}</small></li>")
        body_parts.append("</ul></section>")
    print_button = "" if print_mode else "<button class='screen-only' onclick='window.print()'>چاپ</button>"
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>{escape(document.form_code)} - {escape(document.title)}</title>
  <style>
    @page {{ size: A4; margin: 14mm; }}
    body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; color: #111827; }}
    .toolbar {{ margin-bottom: 12px; }}
    .official-form {{ border: 1px solid #111827; padding: 16px; }}
    header {{ display: grid; grid-template-columns: 1fr auto; gap: 12px; border-bottom: 2px solid #111827; padding-bottom: 10px; margin-bottom: 12px; }}
    h1 {{ margin: 0; font-size: 22px; }}
    h2 {{ font-size: 16px; margin: 16px 0 8px; border-bottom: 1px solid #9ca3af; padding-bottom: 4px; }}
    .meta {{ font-size: 12px; line-height: 1.9; }}
    .form-grid {{ display: grid; grid-template-columns: 190px 1fr; gap: 0; border: 1px solid #d1d5db; }}
    dt, dd {{ border-bottom: 1px solid #e5e7eb; padding: 7px; margin: 0; min-height: 22px; }}
    dt {{ background: #f9fafb; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; page-break-inside: auto; }}
    tr {{ page-break-inside: avoid; page-break-after: auto; }}
    th {{ background: #f9fafb; }}
    th, td {{ border: 1px solid #d1d5db; padding: 7px; text-align: right; vertical-align: top; }}
    thead {{ display: table-header-group; }}
    .checkbox {{ font-family: Arial, sans-serif; font-size: 16px; }}
    footer {{ border-top: 1px solid #111827; margin-top: 18px; padding-top: 8px; font-size: 11px; }}
    @media print {{ .screen-only {{ display: none !important; }} body {{ margin: 0; }} }}
  </style>
</head>
<body>
  <div class="toolbar screen-only">{print_button}</div>
  <article class="official-form">
    <header>
      <div>
        <h1>{escape(document.title)}</h1>
        <div>{escape(document.document_code)} / نسخه {escape(document.version)}</div>
      </div>
      <div class="meta">
        کد پرونده: {escape(document.pilot_code)}<br>
        تاریخ تولید: {escape(_jalali(document.generated_at) or "")}<br>
        وضعیت: {"کامل" if document.is_complete else "اطلاعات ناقص"}
      </div>
    </header>
    {''.join(body_parts)}
    <footer>{escape(document.pilot_code)} - {escape(document.form_code)} - صفحه <span class="page-number"></span></footer>
  </article>
</body>
</html>"""


def _render_value(value: Any) -> str:
    if isinstance(value, bool):
        return f"<span class='checkbox'>{'☑' if value else '☐'}</span>"
    if value is None:
        return ""
    if isinstance(value, list):
        return _table(value) if value and isinstance(value[0], dict) else escape("، ".join(map(str, value)))
    return escape(str(_label(value)))


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p></p>"
    headers = list(rows[0].keys())
    html = ["<table><thead><tr>"]
    html.extend(f"<th>{escape(str(header))}</th>" for header in headers)
    html.append("</tr></thead><tbody>")
    for row in rows:
        html.append("<tr>")
        html.extend(f"<td>{_render_value(row.get(header))}</td>" for header in headers)
        html.append("</tr>")
    html.append("</tbody></table>")
    return "".join(html)
