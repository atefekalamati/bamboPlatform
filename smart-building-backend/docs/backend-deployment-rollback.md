# Runbook Rollback Backend

حداکثر زمان تصمیم اولیه ۱۵ دقیقه است. Release Manager با تأیید مالک محصول و DBA تصمیم می‌گیرد.

1. Traffic را متوقف یا Maintenance mode را در Proxy فعال کنید.
2. اگر Schema backward-compatible است، Image قبلی را با digest دقیق Deploy کنید.
3. Migration داده‌بر یا غیرقابل‌بازگشت را downgrade نکنید؛ Forward-fix ترجیح دارد.
4. Downgrade فقط پس از بررسی Migration و Backup اجرا شود: `alembic downgrade <revision>`.
5. در خرابی داده، DB و DWG را از یک Recovery Point هماهنگ Restore کنید.
6. `/health/ready` و Smokeهای Auth، Pilot، Stage، Gate، Snapshot و DWG را اجرا کنید.
7. رخداد، زمان‌ها، SHAها و مسئول تصمیم را در Incident ثبت کنید.

Rollback موفق بدون تطبیق DB metadata و فایل‌های DWG کامل نیست. Snapshotهای تأییدشده و Audit باید پس از Restore قابل خواندن و hash آن‌ها معتبر باشند.
