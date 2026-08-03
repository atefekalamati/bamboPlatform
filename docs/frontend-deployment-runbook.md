# Runbook انتشار فرانت BAMBO

1. SHA نسخه را تعیین کنید: `BAMBO_RELEASE=<commit-sha>`.
2. تست‌ها: `node --test smart-building-frontend/tests/*.test.mjs`.
3. Artifact: `./smart-building-frontend/scripts/build-production.sh` یا PowerShell معادل.
4. اسکن Artifact باید بدون localhost، Mock فعال، debug OTP و سند داخلی تمام شود.
5. Image: `docker build --build-arg BAMBO_RELEASE=<sha> -t bambo-frontend:<sha> .`.
6. Image را immutable به Registry Push کنید.
7. Backend سرویس `bambo-backend:8000` یا upstream سازمانی را در Nginx تنظیم کنید.
8. TLS باید در Ingress/Load Balancer سازمان terminate شود؛ HTTP به HTTPS redirect شود.
9. Staging deploy، سپس Smoke: `/healthz`، assets، OTP، `/auth/me`، pilots، stage، permission و logout.
10. پس از تأیید دستی Release Manager همان Image digest در Production فعال شود.

`runtime-config.js`، `index.html` بدون Cache و Source assetها با Cache کوتاه سرو می‌شوند. Secret در runtime config ممنوع است.

