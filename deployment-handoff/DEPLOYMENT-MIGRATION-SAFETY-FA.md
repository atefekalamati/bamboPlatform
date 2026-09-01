# راهنمای امن Deploy و Migration سامانه BAMBO Pilot

این سند برای Release Manager، DevOps Engineer یا AI Coding/Deployment Assistant نوشته شده است. هدف آن جلوگیری از اجرای نسخه جدید Backend روی دیتابیس قدیمی، از دست‌رفتن دسترسی نقش‌ها و ناسازگاری Stage، Gate و Form است.

## قاعده قطعی انتشار

نسخه جدید Backend فقط زمانی می‌تواند Traffic دریافت کند که همه موارد زیر موفق باشند:

1. Backup قابل بازیابی PostgreSQL و فایل‌های DWG گرفته شده باشد.
2. Migration با **Image همان Release جدید** و فقط یک‌بار اجرا شده باشد.
3. خروجی `alembic current` با `alembic heads` برابر باشد.
4. `/health/ready` وضعیت HTTP 200 و مقدار `migration: true` برگرداند.
5. Smoke Testهای Auth، Role، Pilot، Stage، Gate و DWG موفق باشند.

اگر هرکدام شکست خورد، Deploy متوقف است. صرفاً بالا بودن `/health/live` به معنی آماده‌بودن سامانه نیست.

## هشدار مخصوص Migration نقش پشتیبانی

Migration زیر نقش `customer_success` را در نقش `support` ادغام می‌کند:

```text
0023_merge_customer_success_into_support
```

نتیجه مورد انتظار:

- `support` فعال و با نام نمایشی «پشتیبانی» باقی می‌ماند.
- `customer_success` غیرفعال می‌شود، ولی برای حفظ سابقه Audit حذف نمی‌شود.
- عضویت کاربران قبلی `customer_success` به `support` منتقل می‌شود.
- Permissionهای فنی `customer_success.*` حفظ و به نقش `support` اعطا می‌شوند.
- مسئولیت Stageهای 13، 15، 16 و 19 و Gate G4 به `support` منتقل می‌شود.

این Migration را قبل از Deploy کد جدید یا در حالی که Replicaهای قدیمی هنوز Traffic می‌گیرند، به‌صورت مستقل اجرا نکنید. برای این تغییر از Maintenance Window کوتاه یا Deploy هماهنگ استفاده کنید.

## کارهای ممنوع

- از Image با Tag شناور `latest` بدون Digest یا Commit SHA استفاده نکنید.
- Migration را هم‌زمان در چند Replica اجرا نکنید.
- فایل `.env.production`، رمز دیتابیس، Token، کلید خصوصی یا Backup را Commit نکنید.
- فرمان‌های `docker compose down -v`، حذف Volume یا پاک‌سازی دیتابیس اجرا نکنید.
- در شکست Migration، کورکورانه `alembic downgrade` اجرا نکنید.
- Backend را فقط براساس `/health/live` وارد Load Balancer نکنید.
- خروجی Secretها، Header احراز هویت یا OTP را در Log/Ticket قرار ندهید.

## ورودی‌های لازم پیش از شروع

- Commit SHA یا Digest دقیق Backend و Frontend
- مسیر فایل Compose تولیدی مبتنی بر `smart-building-backend/compose.prod.example.yaml`
- Secretهای Production در Secret Manager یا فایل‌های خارج از Repository
- مقدار صحیح `DATABASE_URL` در `.env.production`
- مسیر پایدار Volume یا Object Storage فایل‌های DWG
- روش فعال‌کردن Maintenance Mode در Reverse Proxy
- مسیر رمزگذاری‌شده Backup و مسئول تأیید Restore

## مرحله 1: بررسی Release

در ریشه Repository:

```bash
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Worktree باید تمیز باشد و SHA باید با Release مصوب تطبیق داشته باشد.

فایل Compose را بدون نمایش Secretها اعتبارسنجی کنید:

```bash
cd smart-building-backend
docker compose -f compose.prod.yaml config --quiet
```

اگر فایل واقعی نام دیگری دارد، همان نام را جایگزین کنید. فایل Example را مستقیماً به‌عنوان تنظیم Production بدون بازبینی استفاده نکنید.

## مرحله 2: Backup اجباری

پیش از Migration:

1. از PostgreSQL با `pg_dump --format=custom` Backup بگیرید.
2. از DWG Storage در همان Recovery Point منطقی Snapshot بگیرید.
3. checksum هر دو Artifact را ثبت کنید.
4. محل Backup باید خارج از Host اصلی و رمزگذاری‌شده باشد.
5. تأیید کنید Restore این نوع Backup قبلاً در محیط ایزوله آزمایش شده است.

نمونه عمومی PostgreSQL؛ مقادیر واقعی را از Secret Manager بگیرید و در Shell History ثبت نکنید:

```bash
pg_dump --format=custom --file=bambo-predeploy.dump "$DATABASE_URL"
sha256sum bambo-predeploy.dump
```

اگر Backup یا checksum شکست خورد، ادامه ندهید.

## مرحله 3: Maintenance و آماده‌سازی سرویس‌ها

1. Maintenance Mode را در Reverse Proxy فعال کنید یا Traffic نوشتنی را متوقف کنید.
2. اجازه ندهید Replica قدیمی هم‌زمان با Migration نقش‌ها درخواست جدید پردازش کند.
3. PostgreSQL را بالا و Healthy نگه دارید.
4. Image جدید Backend را Pull کنید.

```bash
docker compose -f compose.prod.yaml pull backend migrate
docker compose -f compose.prod.yaml up -d db
```

## مرحله 4: اجرای Migration فقط یک‌بار

Migration باید با Image نسخه جدید اجرا شود:

```bash
docker compose -f compose.prod.yaml run --rm migrate
```

در اجرای بدون Docker:

```bash
cd smart-building-backend
python -m alembic upgrade head
```

شرایط قبولی:

- Exit Code برابر صفر باشد.
- Traceback یا خطای SQL وجود نداشته باشد.
- Job برای بار دوم به‌صورت هم‌زمان اجرا نشده باشد.

## مرحله 5: اثبات همگام بودن Schema

با همان Image و همان `DATABASE_URL` محیط Production اجرا کنید:

```bash
docker compose -f compose.prod.yaml run --rm --no-deps backend python -m alembic current
docker compose -f compose.prod.yaml run --rm --no-deps backend python -m alembic heads
docker compose -f compose.prod.yaml run --rm --no-deps backend python -m alembic check
```

`current` و `heads` باید یک Revision نهایی یکسان نشان دهند و `alembic check` نباید تغییر Schema جدیدی گزارش کند.

برای Release شامل ادغام نقش‌ها، زنجیره Migration باید شامل Revision `0023_merge_customer_success_into_support` باشد. ممکن است Head نهایی در آینده شماره بالاتری داشته باشد؛ در آن صورت فقط برابر بودن `current` و `heads` ملاک نهایی است.

## مرحله 6: اجرای Backend جدید

```bash
docker compose -f compose.prod.yaml up -d backend
docker compose -f compose.prod.yaml ps
```

سرویس Backend در Compose مرجع باید به موفقیت سرویس `migrate` وابسته باشد. Migration را داخل Startup همه Replicaها قرار ندهید؛ Job مستقل ایمن‌تر است.

## مرحله 7: کنترل Health و Readiness

ابتدا Liveness:

```bash
curl -fsS http://127.0.0.1:8000/health/live
```

سپس Readiness:

```bash
curl -fsS http://127.0.0.1:8000/health/ready
```

خروجی قابل قبول Readiness:

```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "migration": true,
    "storage": true
  }
}
```

اگر HTTP 503 یا هر مقدار `false` دریافت شد:

1. Traffic را باز نکنید.
2. Log همان Release را بررسی کنید.
3. `alembic current` و `alembic heads` را دوباره با همان Environment اجرا کنید.
4. مطمئن شوید Backend و Migration Job به یک دیتابیس متصل‌اند.
5. از اجرای مجدد کورکورانه Migration یا تغییر دستی جدول `alembic_version` خودداری کنید.

## مرحله 8: Smoke Test ادغام نقش‌ها

با حساب Super Admin و بدون ثبت Token در Log:

1. صفحه Roles را باز کنید.
2. نقش فعال «پشتیبانی» باید وجود داشته باشد.
3. نقش `customer_success` نباید قابل تخصیص باشد.
4. یک کاربر پشتیبانی باید Permissionهای لازم، از جمله موارد زیر، را دریافت کند:

```text
customer_success.manage
customer_success.followup
customer_success.feedback
gates.approve
```

5. دسترسی مجاز کاربر پشتیبانی به Stageهای 13، 15 و 16 بررسی شود.
6. مسئولیت مربوط به پشتیبانی در Stage 19 بررسی شود.
7. امکان بررسی Gate G4 برای کاربر مجاز کنترل شود.
8. کاربر پشتیبانی نباید Permissionهای مدیریتی نامرتبط مانند `roles.manage` یا `users.manage` را بدون تخصیص صریح دریافت کند.

کاربران دارای Session قدیمی باید Logout/Login کنند یا Session آن‌ها Refresh شود تا Permissionهای جدید از Backend دریافت شود.

## مرحله 9: Smoke Test عمومی

- ورود OTP واقعی
- `GET /auth/me`
- Dashboard و فهرست Pilotهای مجاز
- بازکردن جزئیات یک Pilot
- مشاهده Stageهای مجاز و قفل‌بودن Stageهای غیرمجاز
- Submit و Review آزمایشی در محیط Staging
- مشاهده Gate و Permission Guard
- دانلود یک DWG نمونه
- نمایش زمان صحیح اعلان جدید، بدون اختلاف 3.5 ساعت
- نبود خطای 401، 403، 409 و 500 غیرمنتظره در Console و Backend Log

## مرحله 10: بازکردن Traffic و پایش

پس از موفقیت همه Gateها:

1. Maintenance Mode را غیرفعال کنید.
2. Traffic را تدریجی منتقل کنید.
3. حداقل 15 دقیقه موارد زیر را پایش کنید:
   - نرخ 5xx و 4xx غیرعادی
   - latency p95
   - DB connection pool
   - خطاهای Storage و DWG
   - خطاهای OTP/SMS
   - خطاهای Stage/Gate Permission
   - تعداد اعلان‌های ناموفق

## Rollback

Migration `0023` در Downgrade نمی‌تواند تشخیص دهد کدام کاربر پشتیبانی قبلاً عضو `customer_success` بوده است؛ بنابراین عضویت قبلی را خودکار بازسازی نمی‌کند.

ترتیب تصمیم:

1. Traffic را متوقف و Incident ثبت کنید.
2. اگر Schema با نسخه قبلی سازگار است، ابتدا Forward-fix را ترجیح دهید.
3. Downgrade فقط با تأیید DBA و بررسی کد Migration انجام شود.
4. در خرابی داده یا نیاز به بازگرداندن عضویت‌های قبلی، Backup هماهنگ PostgreSQL و DWG را Restore کنید.
5. پس از Restore دوباره `alembic current/check`، `/health/ready` و Smoke Testها را اجرا کنید.

## چک‌لیست امضای انتشار

- [ ] SHA/Digest نسخه ثبت شد.
- [ ] Worktree و Artifact نهایی تأیید شد.
- [ ] Backup دیتابیس و DWG با checksum ثبت شد.
- [ ] Maintenance Mode فعال شد.
- [ ] Migration Job با Exit Code صفر اجرا شد.
- [ ] `alembic current == alembic heads` تأیید شد.
- [ ] `alembic check` موفق بود.
- [ ] `/health/live` موفق بود.
- [ ] `/health/ready` برابر 200 و `migration: true` بود.
- [ ] نقش پشتیبانی و Stage/G4 Smoke Test شد.
- [ ] Auth، Pilot، DWG و اعلان Smoke Test شد.
- [ ] Traffic باز شد.
- [ ] پایش 15 دقیقه‌ای بدون خطای بحرانی انجام شد.
- [ ] Release، زمان، مسئول و نتیجه در گزارش Deploy ثبت شد.

## دستور نهایی برای AI دیپلوی‌کننده

اگر اطلاعات Environment، مسیر Backup، Image Digest، فایل Compose واقعی یا تأیید اجرای Migration موجود نیست، حدس نزن و Deploy را ادامه نده. وضعیت دقیق فقدان اطلاعات را گزارش کن و از مسئول Release ورودی لازم را بگیر. هیچ Secret یا داده Production را در پاسخ، Log یا Git نمایش نده.
