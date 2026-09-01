# پایگاه داده محلی — راه‌اندازی و بازرسی با DBeaver

این سند توضیح می‌دهد داده‌های پلتفرم BAMBO کجا ذخیره می‌شوند و چطور می‌توان
مستقیم به آن‌ها نگاه کرد. رمز عبور عمداً اینجا نوشته نشده است؛ تنها جای آن
فایل `.env` محلی است که در `.gitignore` قرار دارد.

## موتور و محل

| مورد | مقدار |
| --- | --- |
| موتور | PostgreSQL 17.6 (portable، بدون Docker) |
| باینری‌ها | `E:\bamboo\_local\pgsql` |
| دایرکتوری داده | `E:\bamboo\_local\pgdata` |
| پورت | `5433` |
| گوش‌دادن | `127.0.0.1` و `::1` — فقط loopback |
| دیتابیس | `bambo` |
| کاربر | `bambo` |

پورت ۵۴۳۳ به این دلیل انتخاب شده که ۵۴۳۲ روی این ماشین در اختیار سرویس
دیگری است. `listen_addresses` در `postgresql.conf` تنظیم شده، نه با پرچم
`pg_ctl -o`، تا هر بار راه‌اندازی یکسان باشد.

### چرا هر دو نشانی IPv4 و IPv6

روی ویندوز `localhost` اول به `::1` ترجمه می‌شود. اگر PostgreSQL تنها روی
IPv4 گوش بدهد، درایور تا وقتی مهلت TCP تمام نشود منتظر می‌ماند — در عمل
بک‌اند در «Waiting for application startup» می‌ماند. با گوش‌دادن روی هر دو،
اتصال در حدود ۰٫۳ ثانیه برقرار می‌شود.

> نکته باقی‌مانده: `app/database.py` هیچ `connect_timeout` در `connect_args`
> ندارد. تنظیم فعلی مسئله را برای این ماشین حل می‌کند، اما یک میزبان با
> پیکربندی متفاوت دوباره همان انتظار نامحدود را می‌بیند.

## منبع نشانی دیتابیس

`app/config.py` تنها یک منبع دارد:

```python
DEFAULT_DATABASE_URL = "postgresql+psycopg://<user>:<password>@localhost:5432/bambo"

def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
```

مقدار واقعی از `.env` می‌آید. SQLite تنها در تست‌ها استفاده می‌شود:
`conftest.py` متغیر `DATABASE_URL` را به یک فایل موقت monkeypatch می‌کند و
`ensure_schema()` تنها وقتی `init_db()` را صدا می‌زند که نشانی SQLite باشد.
هیچ مسیر اجرایی دیگری SQLite نمی‌سازد.

## اتصال DBeaver

```
Driver    PostgreSQL
Host      localhost
Port      5433
Database  bambo
Username  bambo
Password  از خط DATABASE_URL در فایل .env محلی بردارید
SSL       خاموش (اتصال loopback است)
```

## دستورهای بازتولید

```bash
PG=E:/bamboo/_local/pgsql/bin
DATA=E:/bamboo/_local/pgdata

# راه‌اندازی سرور
"$PG/pg_ctl.exe" -D "$DATA" -l "$DATA/server.log" start

# وضعیت
"$PG/pg_ctl.exe" -D "$DATA" status

# اتصال
"$PG/psql.exe" -h 127.0.0.1 -p 5433 -U bambo -d bambo

# بردن schema به آخرین نسخه
cd smart-building-backend && alembic upgrade head && alembic current
```

## جدول‌ها

۴۰ جدول به‌علاوه `alembic_version`. همه‌شان از مدل‌های SQLAlchemy در
`app/models/` می‌آیند و همه با migration ساخته می‌شوند.

### هویت و دسترسی

| جدول | نقش |
| --- | --- |
| `users` | حساب کاربر؛ کلید یکتا `mobile` |
| `roles` | ۱۱ ردیف: ۱۰ نقش فعال + `customer_success` غیرفعال |
| `permissions` | ۱۲۸ مجوز |
| `role_permissions` | نگاشت نقش↔مجوز |
| `user_roles` | نگاشت کاربر↔نقش |
| `auth_sessions` | نشست؛ توکن‌ها به صورت SHA-256 ذخیره می‌شوند، نه خام |
| `otp_requests` | درخواست OTP؛ `code_hash` است، کد خام ذخیره نمی‌شود |
| `user_preferences` | تنظیمات کاربر، شامل `notification_preferences` به شکل JSON |

`customer_success` حذف نشده بلکه `is_active = false` شده تا ارجاع‌های
تاریخی نشکنند. کاربری که این نقش را داشت به `support` منتقل شده است.

### پرونده و گردش‌کار

| جدول | نقش |
| --- | --- |
| `pilots` | پرونده پایلوت — ریشه همه چیز |
| `projects` | پروژه هر پایلوت |
| `owners` / `contacts` | مالک ساختمان و راه‌های تماس |
| `floors` | طبقات پروژه |
| `pilot_stages` | ۱۹ مرحله هر پایلوت |
| `pilot_gates` | ۵ گیت (G1@2, G2@4, G3@9, G4@13, G5@15) |
| `stage_submissions` | ثبت مرحله برای بررسی |
| `stage_approvals` | تأیید یا رد |
| `immutable_snapshots` | تصویر تغییرناپذیر با hash محتوا |

### فرم‌ها و عملیات

| جدول | نقش |
| --- | --- |
| `form_f01` … `form_f04` | چهار فرم رسمی |
| `missions` / `mission_floors` | مأموریت برداشت و طبقات آن |
| `incidents` | رخداد |
| `continuation_reviews` | بررسی ادامه پس از مأموریت |
| `pilot_evaluations` | ارزیابی |
| `commercial_proposals` | پیشنهاد تجاری |
| `final_outcomes` | نتیجه نهایی |
| `customer_follow_ups` | پیگیری مشتری |

### نقشه و شواهد

| جدول | نقش |
| --- | --- |
| `dwg_files` | یک ردیف به ازای هر طبقه |
| `dwg_versions` | نسخه‌های نقشه؛ فایل روی دیسک، متادیتا اینجا |
| `external_platform_references` | ارجاع به سامانه بیرونی |
| `external_evidence_checks` | بررسی شواهد بیرونی |

فایل DWG خودش در فایل‌سیستم است و `storage_key` به آن اشاره می‌کند. پس از
migration 0024 چند طبقه می‌توانند به یک فایل مشترک اشاره کنند.

### اعلان و تاریخچه

| جدول | نقش |
| --- | --- |
| `notifications` | اعلان درون‌برنامه‌ای |
| `notification_deliveries` | تلاش ارسال هر کانال، شامل پیامک |
| `audit_logs` | تاریخچه کامل؛ به `users`، `pilots` و `auth_sessions` وصل است |

### جدول‌های بی‌استفاده

`buildings`، `equipment` و `sensors` از schema اولیه smart-building
باقی مانده‌اند. هیچ router یا service ای به آن‌ها نمی‌نویسد و هر سه خالی‌اند.
حذفشان کار این سند نیست، ولی ارزش پیگیری دارد.

## ذخیره‌سازی موقت وجود ندارد

- `useMockApi: false` در `src/config/appConfig.js`؛ هیچ Mock API ای در کد نیست.
- هیچ متغیر ماژول یا cache درون‌حافظه‌ای داده نگه نمی‌دارد.
- `FakeSmsProvider` تنها وقتی `SMS_PROVIDER=fake` باشد ساخته می‌شود.
- `localStorage` در مرورگر تنها نشست و تم را نگه می‌دارد، نه داده دامنه.
