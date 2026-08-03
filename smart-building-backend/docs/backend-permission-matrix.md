# ماتریس Permission بک‌اند

مرجع اجرایی نهایی dependencyهای `require_permission` در `app/routers` است. `super_admin` همه Permissionها و Scope `ALL` دارد؛ سایر نقش‌ها علاوه بر Permission تابع Scope و مالکیت پرونده‌اند.

| Method / Endpoint family | Permission | نقش‌های نمونه | مالکیت/Scope | Audit | تست |
|---|---|---|---|---|---|
| POST `/auth/otp/*` | عمومی با rate-limit | همه | mobile/IP | بله، masked | security |
| GET `/auth/me`, preferences | session معتبر | همه | خود کاربر | preference write | security |
| `/users/*` | `users.read/manage/assign_roles` | super_admin/admin مجاز | خیر | بله | security |
| `/roles/*` | `roles.read/manage/manage_permissions` | super_admin/admin مجاز | delegation ceiling | بله | security |
| GET `/audit` | `audit.read` | super_admin/admin مجاز | Scope فیلتر | read خیر | security |
| `/pilots` create/read | `pilots.create/read` | نقش‌های عملیاتی | Pilot Scope برای داده محدود | create بله | api/security |
| Stage submit | `checklists.manage` | submitter ماتریس Stage و super_admin | Pilot/Stage جاری | بله | api |
| Stage approve/reject | `gate_approval.approve/reject` | reviewer ماتریس و super_admin override | submitted Stage | بله + Snapshot | api/security |
| Snapshot list | `pilots.read` | کاربران پرونده | Pilot Scope | خیر | api |
| Project/F01/F02/DWG | `projects/forms/dwg.*` متناظر | sales/setup/admin | Pilot Scope | write/download بله | product |
| Mission/F03/Floor | `missions.*`, `forms.f03.*` | operations/capture_expert | assigned mission | بله | operations |
| F04/Incident | `customer_success.*`, `incidents.*` | customer_success/operations | Pilot/owner Scope | بله | experience |
| Evaluation | `evaluation.*` | product/pilot manager | Pilot Scope | بله | evaluation |
| Commercial/Outcome | `commercial.*` | sales/pilot manager | Pilot Scope | بله | commercial |
| Notifications | `notifications.*` | recipient/manager | recipient یا Scope | بله | notifications |
| `/api/v1/dashboard/*` | `dashboard.read` و read_all برای ALL | internal roles | Dashboard Scope | خیر | dashboard |
| `/api/v1/reports/*` | `reports.read/sla/kpi` | internal roles | Report Scope؛ IDOR=404 | خیر | reports |
| `/health/*`, `/version` | عمومی و حداقل داده | platform | ندارد | خیر | production readiness |

Download فایل تنها از Endpoint مجاز انجام می‌شود و Storage path عمومی نیست. Permission جدید باید همراه تست allow/deny و به‌روزرسانی این ماتریس وارد شود.
