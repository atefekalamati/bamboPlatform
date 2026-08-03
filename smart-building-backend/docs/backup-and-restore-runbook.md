# Runbook Backup و Restore

هدف پیشنهادی تا تصویب سازمان: `RPO <= 15m` و `RTO <= 4h`.

## Backup

- PostgreSQL: Backup کامل روزانه با `pg_dump --format=custom` و WAL/PITR در Hosting پشتیبان.
- DWG: Snapshot versioned از Volume/Object Storage در همان Recovery Point منطقی DB.
- رمزگذاری در انتقال و سکون، checksum، دسترسی least-privilege و کپی خارج از Host الزامی است.
- Retention پیشنهادی: روزانه ۳۰ روز، هفتگی ۱۲ هفته و ماهانه ۱۲ ماه؛ تصویب حقوقی لازم است.
- Secret، OTP خام و Token نباید وارد خروجی‌های تشخیصی شوند.

## Restore Drill

1. محیط ایزوله و DB خالی بسازید.
2. Backup را Restore و `alembic current/check` اجرا کنید.
3. DWG همان Recovery Point را Restore و تعداد/sha256 نمونه‌ها را با Metadata تطبیق دهید.
4. Smokeهای Auth، Pilot، Stage/Gate، Snapshot/Audit و Download را اجرا کنید.
5. زمان RTO، آخرین تراکنش قابل بازیابی و checksum را ثبت و Artifact آزمایش را امضا کنید.

وجود Runbook به معنی Restore تست‌شده نیست؛ تا ثبت Drill واقعی، این Gate انتشار Blocked است.
