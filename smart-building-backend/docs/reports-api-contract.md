# قرارداد API گزارش‌های مدیریتی

Base path: `/api/v1/reports`. همه Endpointها Read-only هستند و قالب عمومی زیر را دارند:

```json
{"generated_at":"UTC","filters":{},"summary":{},"items":[],"pagination":null,"state":"SUCCESS"}
```

Stateها: `SUCCESS`، `PARTIAL_DATA`، `NO_DATA` و `NO_ACCESS`.

| Method | Path | کاربرد |
|---|---|---|
| GET | `/overview` | کارت‌های مدیریتی |
| GET | `/pipeline` | قیف وضعیت |
| GET | `/pilots` | پیشرفت ۱۹ مرحله‌ای و Drill-down |
| GET | `/gates` | G1 تا G5 و مانع‌ها |
| GET | `/actions` | اقدام‌های باز و موعدها |
| GET | `/sla` | SLA فعالیت‌ها و Breakdown داده‌محور |
| GET | `/kpis` | KPI، target، numerator/denominator |
| GET | `/incidents` | رخدادهای امن و خلاصه |
| GET | `/pilots/{id}/one-page` | گزارش یک‌صفحه‌ای جاری |
| GET | `/pilots/{id}/external-evidence` | فقط نتیجه کوتاه بررسی شواهد |

فیلتر مرکزی: `date_from`، `date_to`، `pilot_id`، `project_id`، `pilot_status`، `stage`، `stage_status`، `gate`، `sla`، `assignee_id`، `has_open_incident`، `has_critical_incident`، `final_outcome`، `q`، `page`، `page_size` و `sort`. تاریخ‌ها باید timezone-aware باشند، `page_size <= 100` و بازه معکوس با 422 رد می‌شود.

`progress_percent = approved_stages_count / 19 * 100`. وضعیت‌های open/submitted/needs_revision کامل نیستند. شرح Incident حداکثر 160 کاراکتر است و متن کامل شواهد خارجی حداکثر 500 کاراکتر نتیجه کوتاه برمی‌گردد.

در قیف، `pilot_status` می‌تواند کلید مدیریتی گروه باشد. برای نمونه
`pilot_status=closed` همه وضعیت‌های داخلی `closed`، `completed`، `rejected` و
`stopped` را برمی‌گرداند. هر آیتم قیف علاوه بر `drill_down_filter`، فهرست
`source_statuses` را برای ردیابی محاسبه اعلام می‌کند.
