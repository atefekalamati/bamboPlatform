# نقشه مسیریابی API در Frontend پروژه BAMBO Pilot

## هدف و محدوده

این سند قرارداد Prefix میان Frontend و Backend را ثبت می‌کند. در وضعیت فعلی، Backend هم Routeهای Legacy بدون Prefix نسخه و هم Routeهای Versioned زیر `/api/v1` دارد. این ترکیب عمدی و بخشی از قرارداد جاری است؛ Frontend نباید برای یکسان‌سازی ظاهری، Prefix هیچ Endpoint موجودی را تغییر دهد.

## نحوه ساخته‌شدن URL نهایی

`httpClient` آدرس نهایی را به‌شکل زیر می‌سازد:

```text
APP_CONFIG.apiBaseUrl + servicePath
```

- `APP_CONFIG.apiBaseUrl` از `window.__APP_CONFIG__.apiBaseUrl` خوانده می‌شود و در نبود تنظیم صریح، `/backend` است.
- `/backend` یک Prefix مربوط به Reverse Proxy یا محیط Deploy است و بخشی از Route داخلی FastAPI محسوب نمی‌شود.
- `servicePath` باید همیشه با `/` شروع شود.
- Prefixهای داخلی API در `smart-building-frontend/src/config/apiRoutes.js` ثبت شده‌اند:
  - Legacy: رشته خالی
  - Versioned v1: `/api/v1`

مثال در Deploy:

```text
/backend + /pilots                    -> /backend/pilots
/backend + /api/v1/dashboard/summary -> /backend/api/v1/dashboard/summary
```

مثال در توسعه محلی با `apiBaseUrl = http://127.0.0.1:8000`:

```text
http://127.0.0.1:8000 + /auth/me
http://127.0.0.1:8000 + /api/v1/reports/overview
```

## Mapping سرویس‌ها

| Service | Base path فعلی | نوع قرارداد | Backend Router | توضیحات |
|---|---|---|---|---|
| `authService` | `/auth` | Legacy | `app/routers/security.py`؛ `auth_router` | OTP، اطلاعات کاربر جاری و Logout. Refresh نیز در `httpClient` با `/auth/refresh` انجام می‌شود. |
| `preferenceService` | `/auth/preferences` | Legacy | `app/routers/security.py`؛ `auth_router` | تنظیمات کاربر جاری. |
| `userService` | `/users` | Legacy | `app/routers/security.py`؛ `users_router` | فهرست، ایجاد، نام، وضعیت و نقش‌های کاربر. |
| `roleService` | `/roles` | Legacy | `app/routers/security.py`؛ `roles_router` | نقش‌ها، Permissionها، Clone و Access Preview. |
| `pilotService` | `/pilots` | Legacy | `app/routers/pilots.py` | فهرست، جزئیات و ایجاد پرونده پایلوت. |
| `stageService` | `/pilots/{pilotId}/forms` و `/pilots/{pilotId}/stages` | Legacy | `app/routers/product.py` و `app/routers/pilots.py` | F01/F02 و عملیات Submit/Approve/Reject/Snapshot مراحل. |
| `dwgService` | `/pilots/{pilotId}/floors`، `/floors` و `/dwg/versions` | Legacy | `app/routers/product.py` | طبقات، DWG، تأیید مرجع و دانلود نسخه. |
| `missionService` | `/missions` و `/pilots/{pilotId}/missions` | Legacy | `app/routers/operations.py` | مأموریت، کارشناس برداشت، F03 و وضعیت طبقات مأموریت. |
| `experienceService` | `/pilots/{pilotId}` و `/incidents` | Legacy | `app/routers/experience.py` | پلتفرم اصلی، اعلان خروجی، F04 و رخدادهای پرونده. |
| `incidentService` | `/incidents` و `/pilots/{pilotId}/incidents` | Legacy | `app/routers/experience.py` | فهرست سراسری/پرونده، ایجاد، ویرایش و بستن رخداد. |
| `evaluationService` | `/pilots/{pilotId}/evaluation`، `/pilots/{pilotId}/external-evidence` و `/missions/{missionId}/continuation-review` | Legacy | `app/routers/evaluation.py` | ارزیابی نهایی، شواهد خارجی و بازبینی تداوم مأموریت. |
| `commercialService` | `/pilots/{pilotId}` | Legacy | `app/routers/commercial.py` | نتیجه نهایی، Follow-up تجاری و Proposal. |
| `formService` | `/pilots/{pilotId}/forms` و `href` دریافتی از Backend | Legacy | `app/routers/forms.py` | Preview، Print و PDF. مقدار `href` قرارداد Backend است و نباید در Client Prefix‌گذاری مجدد شود. |
| `notificationService` | `/notifications` و `/notification-preferences` | Legacy | `app/routers/notifications.py` | مرکز اعلان، شمارنده، وضعیت خوانده‌شدن، تنظیمات و Delivery Log. |
| `dashboardService` | `/api/v1/dashboard` | Versioned v1 | `app/routers/dashboard.py` | Base path از `API_BASE_PATHS.dashboard` دریافت می‌شود. |
| `reportService` | `/api/v1/reports` | Versioned v1 | `app/routers/reports.py` | Base path از `API_BASE_PATHS.reports` دریافت می‌شود. |
| `httpClient` | `APP_CONFIG.apiBaseUrl` | زیرساخت مشترک | همه Routerها | Base مربوط به Origin/Reverse Proxy، احراز هویت، Refresh، Timeout و مدیریت پاسخ را اعمال می‌کند؛ Endpoint مستقل تجاری ندارد. |

## Hardcodeهای متمرکز‌شده

دو Base path نسخه‌دار بدون تغییر در URL خروجی به `src/config/apiRoutes.js` منتقل شدند:

```text
/api/v1/dashboard
/api/v1/reports
```

مسیرهای Legacy عمداً داخل Service متناظر باقی مانده‌اند، زیرا بخش پس از Base path قرارداد همان Domain Service است و متمرکزکردن همه آن‌ها در یک فایل واحد، وابستگی غیرضروری و احتمال تغییر اشتباه قرارداد را افزایش می‌دهد.

## استاندارد توسعه آینده

1. Service جدید باید به‌صورت پیش‌فرض از Endpoint نسخه‌دار `/api/v1/...` استفاده کند.
2. استثنا فقط زمانی مجاز است که قرارداد صریح Backend یک Route بدون Prefix نسخه تعریف کرده باشد.
3. برای Domain نسخه‌دار جدید، Base path باید در `API_BASE_PATHS` تعریف و در Service مصرف شود.
4. هیچ Service نباید `/backend`، Host، Port یا Origin را Hardcode کند؛ این مقادیر فقط از `APP_CONFIG.apiBaseUrl` می‌آیند.
5. `href`های API که Backend برمی‌گرداند باید همان‌طور که هستند به `httpClient` داده شوند و نباید دوباره `/api/v1` دریافت کنند.
6. مهاجرت یک Route از Legacy به Versioned یک تغییر قرارداد است و باید هم‌زمان در Backend، Frontend، تست‌ها و این سند ثبت شود.

## کنترل عدم تغییر رفتار

متمرکزسازی فعلی فقط منبع ثابت دو Prefix نسخه‌دار را تغییر داده است. URLهای تولیدشده قبل و بعد از تغییر یکسان‌اند:

```text
/api/v1/dashboard/summary
/api/v1/dashboard/pilots
/api/v1/reports/overview
/api/v1/reports/pilots/{pilotId}/one-page
```
