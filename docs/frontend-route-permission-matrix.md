# ماتریس Route و Permission فرانت

| Route | Page | Permission | بدون Auth | بدون Permission | API اصلی |
|---|---|---|---|---|---|
| `#/` | Dashboard | `dashboard.read` | Login | Access denied | `/api/v1/dashboard/*` |
| `#/pilots` | Pilots | `pilots.read` | Login | Access denied | `/pilots` |
| `#/pilots/{id}` و Stage 1–19 | Pilot/Stage | `pilots.read` + Permission اقدام در خود صفحه | Login | Access denied/Action hidden | `/pilots/{id}`, `/stages/*` |
| `#/users` | Users | `users.read` | Login | Access denied | `/users` |
| `#/roles` | Roles | `roles.read` | Login | Access denied | `/roles*` |
| `#/incidents` و جزئیات | Incidents | `incidents.read` | Login | Access denied | `/incidents*` |
| `#/pilots/{id}/incidents/new` | IncidentCreate | `incidents.manage` | Login | Access denied | `/pilots/{id}/incidents` |
| `#/notifications*` | Notifications | `notifications.read` | Login | Access denied | `/notifications*` |
| `#/reports*` | Reports | `reports.read`؛ KPI/SLA مجوز جدا | Login | Access denied | `/api/v1/reports/*` |

Backend مرجع نهایی Scope و مجوز Mutation است. Guard فرانت صرفاً جلوگیری UX/افشای ناخواسته DOM است.

