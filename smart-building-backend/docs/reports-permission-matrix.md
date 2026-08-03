# ماتریس Permission و Scope گزارش‌ها

| Endpoint | Permission | Scope |
|---|---|---|
| overview/pipeline/pilots/gates/actions/incidents/one-page/evidence | reports.read | Scope مشترک Dashboard |
| sla | reports.sla | Scope مشترک Dashboard |
| kpis | reports.kpi | Scope مشترک Dashboard |

Super Admin، `dashboard.read_all` یا `pilots.read_all` همه پرونده‌ها را می‌بینند. نقش‌های مدیریتی عملیاتی مطابق Policy موجود دید سازمانی دارند. نقش محدود فقط Pilot مرتبط با Mission، Incident، Follow-up، Proposal یا F04 خود را می‌بیند. درخواست one-page/evidence خارج از Scope با 404 پاسخ می‌گیرد تا IDOR وجود Pilot را افشا نکند.

Permission جدید و Migration RBAC اضافه نشده است؛ Permissionهای موجود منبع حقیقت‌اند. مشتری خارجی در MVP Permission گزارش داخلی ندارد.
