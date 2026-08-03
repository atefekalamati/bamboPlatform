# ممیزی آمادگی Production بک‌اند BAMBO

تاریخ ممیزی: 2026-08-03. این سند وضعیت قابل اثبات از سورس را ثبت می‌کند؛ موارد وابسته به Credential یا زیرساخت با وضعیت Blocked باقی می‌مانند.

| شناسه | حوزه | وضعیت فعلی | مسیر فایل | ریسک | شدت | تغییر لازم | تست پذیرش | وضعیت نهایی |
|---|---|---|---|---|---|---|---|---|
| PR-01 | Application configuration | کنترل محدود Secret و DWG | app/config.py | شروع ناامن Production | Blocker | Validation مرکزی fail-fast | تست مقادیر ناامن | تکمیل سورس |
| PR-02 | Secrets | Environment؛ مقدار توسعه پیش‌فرض دارد | app/config.py | استفاده تصادفی از Secret توسعه | Critical | رد Production و عدم ورود env به Image | startup failure | در حال اصلاح |
| PR-03 | Database | SQLite فقط test/dev؛ pool حداقلی | app/database.py | pool/timeout نامتناسب | High | تنظیم pool و PostgreSQL session | تست config | تکمیل سورس |
| PR-04 | Alembic migrations | CI PostgreSQL و downgrade موجود | alembic/, backend-ci.yml | اجرای هم‌زمان migration | High | Job مستقل پیش‌استقرار | upgrade/check | قابل قبول با Runbook |
| PR-05 | Authentication | Token hash، expiry و revoke موجود | app/services/security.py | افشای Token | Critical | حفظ تست‌های امنیت | Auth suite | قابل قبول |
| PR-06 | Authorization | RBAC و محافظت آخرین مدیر موجود | app/routers/* | IDOR/ارتقای اختیار | Critical | ماتریس Endpoint و تست Scope | RBAC/IDOR | در حال مستندسازی |
| PR-07 | OTP/SMS | Fake در dev/test؛ Production unconfigured | app/providers/sms.py | ورود Production ناممکن | Blocker | Provider مصوب و Credential Runtime | ارسال و delivery واقعی | Blocked |
| PR-08 | Session management | hash/expiry/revoke و permission live | app/services/security.py | نشست منقضی/کاربر قفل | High | Cleanup عملیاتی و Runbook | Session suite | Partial |
| PR-09 | CORS | Environment ولی wildcard methods/headers | app/main.py | دسترسی Origin ناامن | Critical | validate origin و محدودسازی | production config tests | تکمیل سورس |
| PR-10 | Security headers | Middleware اختصاصی ندارد | app/main.py | cache/sniffing policy | High | Header middleware | health/security test | تکمیل سورس |
| PR-11 | Rate limiting | PostgreSQL-based OTP controls | app/services/security.py | چند Replica | High | حفظ منبع مشترک DB و load test | rate-limit test | Partial |
| PR-12 | DWG storage | Local امن، signature/hash/size/path دارد | app/storage/dwg.py | از دست‌رفتن فایل/عدم اشتراک Replica | Blocker | Volume پایدار؛ حداکثر یک Replica تا Storage مشترک | storage readiness/restore | آماده مشروط برای VPS تک‌Replica؛ Blocked برای multi-replica |
| PR-13 | Audit log | Audit و masking موجود | app/models, app/services | حذف/retention نامشخص | High | retention و backup policy | audit tests | Partial |
| PR-14 | Logging | Structured request log کامل ندارد | app/main.py | ردیابی ضعیف | High | log JSON بدون داده حساس | log smoke test | تکمیل پایه |
| PR-15 | Monitoring | Error tracker/alerts مصوب نیست | Deployment | کشف دیرهنگام خطا | High | اتصال ابزار مصوب | alert drill | Blocked |
| PR-16 | Health checks | فقط /health process | app/main.py | ارسال Traffic به Replica ناسالم | Critical | live/ready + DB/migration/storage | health tests | تکمیل سورس |
| PR-17 | Backup | Runbook موجود نیست | docs | از دست‌رفتن DB | Blocker | pg_dump رمزگذاری‌شده | backup artifact | در حال مستندسازی |
| PR-18 | Restore | Restore واقعی اجرا نشده | محیط عملیات | Backup غیرقابل اتکا | Blocker | restore drill دوره‌ای | checksum/smoke | Blocked |
| PR-19 | Performance | selectinload و pagination در مسیرهای اصلی | services/dashboard.py | latency در بار واقعی | Medium | load plan و budget | p95 test | Partial |
| PR-20 | Docker image | Dockerfile.dev با root و reload | Dockerfile.dev | اجرای Development | Blocker | Image مستقل non-root | image smoke/health | تکمیل سورس؛ build محلی لازم |
| PR-21 | Container runtime | Compose توسعه با رمز حدس‌پذیر | compose.yaml | DB ناامن | Blocker | manifest نمونه بدون Secret | config inspection | نمونه Production تکمیل |
| PR-22 | CI/CD | SQLite + PostgreSQL migration/integration | .github/workflows/backend-ci.yml | نبود scan/build/SBOM | High | lint/audit/build/SBOM | pipeline green | Pipeline تکمیل؛ اجرای Remote لازم |
| PR-23 | Tests | suite گسترده؛ PostgreSQL در CI | tests | Skip وابسته به محیط | High | health/config و release gates | pytest | در حال اصلاح |
| PR-24 | Rollback | Runbook رسمی ندارد | docs | افزایش downtime | High | rollback/forward-fix | tabletop drill | در حال مستندسازی |
| PR-25 | Data retention | سیاست رسمی ثبت نشده | docs | نگهداری بیش‌ازحد/حذف زودهنگام | Medium | سیاست مصوب سازمان | policy review | Blocked |
| PR-26 | Incident handling | Incident محصول موجود؛ incident عملیاتی ناقص | services/experience.py | پاسخ دیرهنگام Production | High | alert/runbook/escalation | incident drill | Partial |
| PR-27 | Dependencies | Range بدون Lock قطعی | requirements.txt | supply-chain و نسخه آسیب‌پذیر | Critical | Lock hashدار Python 3.13 و audit | pip --require-hashes / pip-audit | تکمیل؛ بدون آسیب‌پذیری شناخته‌شده |

## نتیجه Audit اولیه

تا زمان پیکربندی SMS واقعی، اجرای Restore آزمایشی، انتخاب Storage پایدار و تأیید Monitoring، انتشار **No-Go** است. کنترل‌های سورسی در این تغییر ریسک استقرار تصادفی ناامن را کاهش می‌دهند، اما جایگزین تصمیم زیرساختی نیستند.
