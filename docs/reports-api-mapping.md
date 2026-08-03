# نگاشت API گزارش‌ها

| UI | Endpoint | Permission |
|---|---|---|
| خلاصه | `GET /api/v1/reports/overview` | `reports.read` |
| قیف | `GET /api/v1/reports/pipeline` | `reports.read` |
| پیشرفت | `GET /api/v1/reports/pilots` | `reports.read` |
| Gate | `GET /api/v1/reports/gates` | `reports.read` |
| اقدامات | `GET /api/v1/reports/actions` | `reports.read` |
| SLA | `GET /api/v1/reports/sla` | `reports.sla` |
| KPI | `GET /api/v1/reports/kpis` | `reports.kpi` |
| رخداد | `GET /api/v1/reports/incidents` | `reports.read` |
| تک‌صفحه‌ای | `GET /api/v1/reports/pilots/{id}/one-page` | `reports.read` |
| شواهد | `GET /api/v1/reports/pilots/{id}/external-evidence` | `reports.read` |

