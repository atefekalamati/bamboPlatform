# ممیزی آمادگی Production فرانت BAMBO

تاریخ ممیزی: ۱۴۰۵/۰۵/۱۲ — مبنا: سورس `master`، PRD v0.4 و قراردادهای جاری Backend.

| شناسه | حوزه | وضعیت فعلی و مسیر | ریسک | شدت | تغییر لازم | تست پذیرش | وضعیت نهایی |
|---|---|---|---|---|---|---|---|
| PR-01 | Config | `appConfig.js` دارای `127.0.0.1:8002` و `useMockApi:true` | Artifact وابسته به سیستم توسعه | Blocker | Runtime config و منع Mock در Production | اسکن Artifact | باز |
| PR-02 | Mock | Mock اجرایی در Serviceها یافت نشد؛ README وضعیت قدیمی را Mock معرفی می‌کند | برداشت اشتباه و امکان فعال‌سازی Config | High | حذف فلگ Production و اصلاح README | جست‌وجوی Mock/localhost | باز |
| PR-03 | Server | فقط Python dev server؛ Docker production وجود ندارد | Header/Cache/Compression نامطمئن | Blocker | Nginx production مستقل | تست Header و Health | باز |
| PR-04 | Artifact | کل سورس شامل tests/docs قابل سرو است | افشای مستندات داخلی | High | Allow-list build به `dist/` | بررسی فهرست Artifact | باز |
| PR-05 | CSP/XSS | Script inline Theme و سه مورد `innerHTML` ثابت | CSP نیازمند unsafe-inline | High | انتقال Theme به فایل و حذف HTML sinkها | CSP و جست‌وجوی sink | باز |
| PR-06 | Auth | Bearer در `sessionStorage`؛ 401 پاک‌سازی می‌شود؛ Backend Cookie/Refresh ندارد | XSS می‌تواند Token نشست را بخواند | High | حفظ موقت Bearer، CSP سخت‌گیرانه؛ مهاجرت Cookie نیازمند Backend | تست logout/401/no URL token | تصمیم موقت |
| PR-07 | OTP | API واقعی، cooldown/rate limit backend؛ UI فعال است | پاک‌سازی و timer/focus نیازمند بازبینی | High | سخت‌سازی UI و تست | request/verify/resend/expire | باز |
| PR-08 | Route Guard | Bootstrap بدون Token را می‌بندد؛ Route-level matrix مرکزی وجود ندارد | Direct route ممکن است UI غیرمجاز بسازد | High | Guard مرکزی مبتنی بر Permission | direct URL/403 | باز |
| PR-09 | API | Serviceها واقعی‌اند؛ `formService` fetch مستقل دارد | رفتار Error/Auth دوگانه | Medium | استفاده از Client مرکزی یا مستندسازی استثنا | Contract tests | باز |
| PR-10 | Workflow | Stageهای ۱ تا ۱۹ وضعیت Backend و Gate را می‌خوانند؛ تست جامع E2E موجود نیست | Regression عبور مراحل | Blocker | تست Stage/Gate در Staging | ۱۹ Stage و ۵ Gate | وابسته به Staging |
| PR-11 | Forms | F01-F05 متصل‌اند؛ Validation پراکنده است | خطای UX/Accessibility | High | Audit فیلدها و تست Contract | required/owner mobile/date/errors | باز |
| PR-12 | DWG | MIME/extension/size و Blob download نیازمند تأیید کامل | فایل نامعتبر یا URL leak | High | تست و revoke Object URL | invalid/duplicate/cancel/download | باز |
| PR-13 | Error | Contract مرکزی 400..503، Trace ID در مدل؛ App error boundary ندارد | صفحه سفید روی exception | High | Boundary و unhandled rejection UI | خطای render/rejection | باز |
| PR-14 | Offline | Network error API هست؛ وضعیت online/offline سراسری نیست | ابهام ارسال فرم | Medium | Offline banner و عدم Fake success | قطع/وصل شبکه | باز |
| PR-15 | Accessibility | Skip link، Modal و RTL موجود؛ Audit خودکار کامل نیست | عدم انطباق WCAG AA | High | Focus/error semantics و تست axe در CI بعدی | keyboard/zoom/contrast | باز |
| PR-16 | Responsive | قواعد Responsive گسترده موجود است | مرورگر/ابعاد واقعی تست نشده | Medium | Smoke matrix 360..1440 | بدون overflow | وابسته به Browser farm |
| PR-17 | Performance | فونت محلی با `font-display`؛ Build hashing ندارد | Cache و نسخه قدیمی | Medium | Manifest نسخه و سیاست cache | اندازه/Cache/Lighthouse | باز |
| PR-18 | Privacy | Tracker یافت نشد؛ Token در URL/Console یافت نشد | داده حساس در Error ابزار آینده | Medium | سیاست masking و منع tracker | source scan | قابل قبول |
| PR-19 | Release | CI/CD، runbook و rollback وجود ندارد | انتشار غیرقابل تکرار | Blocker | Pipeline، checklist و artifact immutable | اجرای CI/build/smoke | باز |

## پوشش قابلیت‌ها

Login، Users، Roles، Pilots، Pilot Detail، Stage 1–19، F01–F05، DWG، Mission، Incident، Evaluation، Commercial، Snapshot، Dashboard و Reports در Route/Service/Page موجود بررسی شدند. Mock اجرایی در مسیر Serviceها یافت نشد؛ ریسک اصلی Config و نبود Artifact محدودشده است.

## نتیجه اولیه

**No-Go** تا بسته‌شدن PR-01، PR-03، PR-10 و PR-19. تغییر Auth به HttpOnly Cookie بدون قرارداد Backend انجام نمی‌شود.

## به‌روزرسانی پس از اصلاح

- PR-01، PR-02، PR-03، PR-04، PR-05، PR-08، PR-13، PR-14 و PR-19 در سطح سورس/Artifact بسته شدند.
- PR-06 با تصمیم مستند حفظ Bearer تا آماده‌شدن Cookie/CSRF Backend پذیرفته شد.
- PR-07 در UI برای cooldown/expiry/double-submit سخت‌سازی شد؛ Provider واقعی باید در Staging تأیید شود.
- PR-09 با Contract status مستند و تست‌های موجود پوشش داده شد؛ `formService` برای چاپ Blob همچنان استثنای کنترل‌شده است.
- PR-10، PR-11، PR-12، PR-15، PR-16 و سنجه‌های مرورگری PR-17 تا اجرای Staging باز هستند.
- نتیجه نهایی Audit: **No-Go مشروط به تست Staging**؛ جزئیات در `frontend-production-readiness-report.md`.
