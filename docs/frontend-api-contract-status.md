# وضعیت قرارداد API فرانت

همه درخواست‌ها به‌جز جریان چاپ فرم از `httpClient` مرکزی، Bearer Session، Timeout ۳۰ ثانیه، AbortSignal و قرارداد خطای استاندارد استفاده می‌کنند. Retry خودکار Mutation وجود ندارد.

| Service | Endpointهای کلیدی | Method/Payload | Auth/Permission | Pagination/وضعیت |
|---|---|---|---|---|
| auth | `/auth/otp/request`, `/verify`, `/me`, `/logout` | POST JSON / GET | عمومی سپس Bearer | cooldown/429/expiry واقعی |
| user | `/users`, roles/status | GET/POST/PATCH | users.read/manage | لیست فعلی بدون pagination فرانت |
| role | `/roles`, permissions, clone | GET/POST/PATCH/DELETE | roles.read/manage | بدون pagination |
| pilot | `/pilots`, `/pilots/{id}` | GET/POST JSON | pilots.read/create | لیست فعلی array |
| stage | F01/F02، submit/approve/reject/snapshot | GET/PUT/POST | forms/checklists/gate | 409/422 بدون retry |
| dwg | floors، reference، versions، upload/download | GET/POST/DELETE/Blob | dwg.manage | validation نهایی Backend |
| mission | missions/F03/floors | GET/POST/PUT/PATCH | missions.manage | واقعی |
| experience | external platform/F04/notification/incidents | GET/PUT/POST | customer/notification | واقعی |
| evaluation | evaluation/evidence/continuation | GET/PUT | evaluation/customer | واقعی |
| commercial | proposal/follow-up/final outcome | GET/PUT/POST | commercial.manage | واقعی |
| form | forms/preview/pdf | GET/Blob | forms.read | چاپ window از Blob |
| incident | list/detail/create/update/close | GET/POST/PATCH | incidents.read/manage | قرارداد paginated + سازگاری array |
| notification | list/read/delete/preferences | GET/PATCH/POST/DELETE | notifications.* | query pagination |
| dashboard | `/api/v1/dashboard/*` | GET + filters | dashboard.* | server-side |
| reports | `/api/v1/reports/*` | GET + filters | reports.read/kpi/sla | server-side |

Schema خطا: `message/detail`، `code`، `stage`، `errors[]`، `trace_id`، `retry_after`. 401 Session را پاک می‌کند؛ 403 Session را حفظ می‌کند.

