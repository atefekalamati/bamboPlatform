# Runbook Rollback فرانت

- مسئول: Release Manager با هماهنگی Backend Owner.
- شرط: خطای Auth/Stage/Gate، ناسازگاری Contract، افزایش 5xx یا شکست Smoke بحرانی.
- زمان تصمیم پیشنهادی: حداکثر ۱۵ دقیقه پس از تشخیص Blocker.
- دستور: Deployment را به digest نسخه تأییدشده قبلی برگردانید؛ Config همان نسخه را بازیابی کنید؛ rollout status را بررسی کنید.
- Cache: `index.html` و `runtime-config.js` purge شوند؛ Assetهای Release قبلی حذف فوری نشوند.
- Smoke نسخه قبلی: health، login، me، pilot list/detail، stage status، logout.
- اگر Migration Backend ناسازگار است، Rollback صرف فرانت کافی فرض نشود و Matrix سازگاری Backend اجرا شود.
- نتیجه و کاربران متاثر در کانال رخداد Release ثبت شوند؛ داده شخصی در پیام قرار نگیرد.

