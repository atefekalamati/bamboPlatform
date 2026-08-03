# تحلیل فاصله گزارش‌های مدیریتی Backend

این تحلیل بر مبنای PRD v0.4، SOP نسخه 1.0 و کد عملیاتی موجود تهیه شده است. راهکار نهایی جدول یا Reporting Engine جدید نمی‌سازد و Scope موجود Dashboard را استفاده می‌کند.

| گزارش موردنیاز | داده منبع | Endpoint فعلی | وضعیت فعلی | نقص | تغییر لازم | Permission | تست موردنیاز | وضعیت نهایی |
|---|---|---|---|---|---|---|---|---|
| نمای کلی | Pilot/Stage/Outcome/Incident/SLA | dashboard/summary | جزئی | Outcome و Action ناقص | reports/overview | reports.read | شمارش و Scope | تکمیل |
| قیف | Pilot.status/FinalOutcome | ندارد | فاقد قرارداد | Mapping مرکزی و Drill-down چندوضعیتی نداشت | reports/pipeline با source_statuses | reports.read | Drill-down و تطبیق شمارش | تکمیل |
| پیشرفت ۱۹ مرحله | PilotStage | dashboard/pilots | نادرست | از current_stage محاسبه می‌شد | reports/pilots و اصلاح Dashboard | reports.read | Approved-only | تکمیل |
| Gateها | PilotGate/StageApproval/Incident | dashboard/gates | Aggregate ساده | Reviewer/Blocker ندارد | reports/gates | reports.read | G1-G5 | تکمیل |
| اقدامات | Stage/Mission/Incident | dashboard/my-actions | محدود | فیلتر و دلیل/مسئول ناقص | reports/actions | reports.read | overdue/owner | تکمیل MVP |
| SLA | Mission/Incident | dashboard/sla | شمارش سطح Pilot | فعالیت و مدت ندارد | reports/sla | reports.sla | overdue/at-risk | Partial؛ فیلدهای بازنگری موعد موجود نیست |
| KPI | MissionFloor/F04/Notification/Commercial | ندارد | فاقد قرارداد | denominator و target ندارد | reports/kpis | reports.kpi | zero denominator | تکمیل داده‌های موجود |
| رخدادها | Incident | dashboard/incidents | Aggregate ساده | جزئیات امن و Pagination ندارد | reports/incidents | reports.read | critical/closed | تکمیل |
| یک‌صفحه‌ای | همه Aggregateهای Pilot | ندارد | فاقد API | تصمیم شفاف و مسائل برتر ندارد | reports/pilots/{id}/one-page | reports.read | IDOR/حداکثر ۳ | تکمیل MVP |
| شواهد خارجی | ExternalEvidenceCheck | API عملیاتی | داده خام مجاز | View مدیریتی ندارد | reports/pilots/{id}/external-evidence | reports.read | عدم افشای محتوا | تکمیل |

## فاصله‌های داده‌ای باقی‌مانده

`revised_due_at`، `delay_reason`، `corrective_action` و `escalated_at` برای SLA عمومی مدل نشده‌اند؛ پاسخ SLA با `PARTIAL_DATA` این کمبود را اعلام می‌کند. برنامه کاری مستقل Floor و تاریخ برنامه‌شده هر Floor وجود ندارد، بنابراین KPI «طبق برنامه» فعلاً completion ثبت‌شده را با sample واقعی گزارش می‌کند و مقدار جعلی تولید نمی‌شود.
