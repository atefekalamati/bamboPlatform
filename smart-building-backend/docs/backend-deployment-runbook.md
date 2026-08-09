# Runbook استقرار Backend

## پیش‌شرط‌های Go

- SMS Adapter مصوب با تست واقعی ارسال و Delivery فعال باشد.
- PostgreSQL و DWG Backup رمزگذاری‌شده و Restore آزمایشی موفق باشد.
- برای بیش از یک Replica، Storage مشترک مصوب باشد؛ Local volume فقط تک Replica است.
- Secretها از Secret Manager تزریق شوند؛ `.env` وارد Image نمی‌شود.
- CI، migration، security scan و smoke test سبز باشند.

## Pre-deploy

1. Release و Commit SHA را ثابت و Image را با digest ثبت کنید؛ از `latest` تنها استفاده نکنید.
2. `pg_dump --format=custom` و Snapshot هماهنگ DWG بگیرید؛ checksum و محل رمزگذاری‌شده را ثبت کنید.
3. سازگاری نسخه جدید با Schema و Frontend قبلی را تأیید کنید.
4. Migration را فقط یک‌بار با Job مستقل اجرا کنید: `python -m alembic upgrade head`.
5. `python -m alembic check` و مقدار `alembic_version` را کنترل کنید.

## Deploy و Verification

1. Replica جدید را بدون Traffic بالا بیاورید.
2. `/health/live` سپس `/health/ready` را کنترل کنید.
3. Smoke: ورود OTP واقعی، فهرست Pilot، جزئیات، Dashboard، DWG download و یک درخواست read-only.
4. نرخ 5xx، DB pool، SMS failure، latency p95 و Storage error را حداقل ۱۵ دقیقه پایش کنید.
5. پس از موفقیت Traffic را تدریجی منتقل و Release را علامت‌گذاری کنید.

Bootstrap مدیر کل فقط در پنجره کنترل‌شده با `ALLOW_SUPER_ADMIN_BOOTSTRAP=true` انجام و بلافاصله هر دو متغیر Bootstrap حذف می‌شوند. شماره در Ticket امن نگهداری می‌شود، نه Log.
