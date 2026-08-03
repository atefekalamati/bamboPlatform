# BAMBO Pilot Frontend

فرانت سامانه مدیریت فرایند پایلوت BAMBO با HTML، CSS و JavaScript ES Modules، رابط فارسی RTL و ۱۹ مرحله عملیاتی.

## توسعه محلی

فایل `runtime-config.js` را با API محیط توسعه تنظیم و یک Static HTTP Server اجرا کنید. Dev server و `Dockerfile.dev` فقط برای توسعه‌اند و در Image تولید استفاده نمی‌شوند.

```powershell
python -m http.server 8080
```

OTP، Users، Roles، Pilots، Stageها، Forms، DWG، Mission، Incident، Dashboard و Reports به API واقعی متصل‌اند. Mock اجرایی در Production وجود ندارد و خطای Backend به‌عنوان موفقیت ساختگی نمایش داده نمی‌شود.

## تست و Artifact

```powershell
node --test tests/*.test.mjs
powershell -ExecutionPolicy Bypass -File scripts/build-production.ps1
```

Artifact محدودشده در `dist/` ساخته می‌شود و شامل tests، docs، PRD، dev server یا فایل Mock نیست. Config غیرحساس هنگام Deploy در `runtime-config.js` قرار می‌گیرد؛ Secret در Frontend ممنوع است.

## Docker Production

از ریشه Repository:

```powershell
docker build --build-arg BAMBO_RELEASE=<commit-sha> -t bambo-frontend:<commit-sha> .
docker run --rm -p 8080:8080 bambo-frontend:<commit-sha>
```

Image تولیدی از Nginx غیر Root، Healthcheck، Compression، Cache policy و Security Header استفاده می‌کند. مسیر `/backend/` به سرویس Backend reverse proxy می‌شود. TLS باید در Ingress یا Load Balancer سازمان فعال باشد.

## احراز هویت

قرارداد فعلی Backend از Bearer Token استفاده می‌کند؛ Token فقط در `sessionStorage` نشست قرار دارد و در Logout یا 401 پاک می‌شود. مهاجرت به HttpOnly Secure Cookie بدون پشتیبانی Backend و CSRF انجام نشده است.

## اسناد انتشار

- `docs/frontend-production-readiness-audit.md`
- `docs/frontend-api-contract-status.md`
- `docs/frontend-route-permission-matrix.md`
- `docs/frontend-deployment-runbook.md`
- `docs/frontend-deployment-rollback.md`
- `docs/frontend-release-checklist.md`

تا پاس‌شدن E2E تمام ۱۹ Stage/پنج Gate، OTP Provider، Browser Matrix و Performance در Staging، توصیه Release برابر **No-Go** است.
