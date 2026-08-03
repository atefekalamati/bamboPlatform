# برنامه Load Test Backend

هدف PRD: 95٪ پاسخ‌های عادی زیر ۲ ثانیه و Save زیر ۳ ثانیه. ابزار پیشنهادی k6/Locust در محیط Stage با داده غیرواقعی است.

| مسیر | سناریو | معیار |
|---|---|---|
| OTP request/verify | burst و rate-limit مشترک | بدون bypass و duplicate SMS |
| Pilot list/detail | 50 کاربر هم‌زمان، pagination | p95 < 2s، query ثابت |
| Stage submit/approve | تصمیم هم‌زمان | p95 < 3s، یک Snapshot |
| DWG upload/download | فایل نزدیک limit | memory bounded، hash صحیح |
| Dashboard/Reports | filter و page | p95 < 2s، بدون N+1 |

Load test واقعی در این محیط اجرا نشده و نتیجه Production قابل ادعا نیست. قبل از Go باید latency، throughput، error rate، DB connections، CPU/RAM و SMS quota در Artifact Release ثبت شوند.
