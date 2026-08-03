# Checklist انتشار Backend

- [ ] Image immutable با SHA، non-root و بدون reload
- [x] Dependency lock hashدار و `pip-audit` بدون آسیب‌پذیری شناخته‌شده
- [ ] Secret scan، dependency scan، image scan و SBOM سبز
- [ ] Production config validation موفق
- [ ] PostgreSQL upgrade/check و تست Integration موفق
- [ ] Backup DB/DWG و Restore drill معتبر
- [ ] SMS واقعی و Delivery test موفق
- [ ] Storage مشترک برای چند Replica یا `WEB_CONCURRENCY/replicas=1`
- [ ] CORS/Trusted hosts/Proxy IP/HTTPS تأیید
- [ ] Unit، RBAC، IDOR، Workflow، DWG، Snapshot و Health سبز
- [ ] Readiness و Smoke پس از Deploy سبز
- [ ] Dashboard 5xx/latency/SMS/DB/Storage و On-call فعال
- [ ] Rollback digest و تصمیم‌گیر مشخص

هر مورد Blocker تیک‌نخورده نتیجه Release را **No-Go** می‌کند.
