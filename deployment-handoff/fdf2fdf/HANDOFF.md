# BAMBO Platform — Deployment Handoff

## Release identity

- Release: `fdf2fdf`
- Commit: `fdf2fdfa02cc92049f93e26413358ca4978a3a81`
- Branch: `master`
- Commit date: `2026-08-03T14:43:05+03:30`
- Package: `bambo-platform-fdf2fdf-deploy.tar.gz`
- Frontend: static HTML/CSS/JavaScript served by unprivileged Nginx on port `8080`
- Backend: FastAPI/Uvicorn on port `8000`
- Database: PostgreSQL 17
- Database migrations: Alembic; current repository head includes `0016_form_f04_other_issue_description.py`

The archive is a clean snapshot of the commit above. Local `.env`, database data,
logs, `.git`, Python caches, frontend `dist`, and the developer-only runtime
configuration pointing to `127.0.0.1:8002` are not included.

## Release status

- Frontend tests: `38 passed`
- Frontend production build: passed
- Backend tests: `75 passed, 5 skipped`
- Docker image build/smoke on the handoff machine: not run because Docker Engine was unavailable

## Production blockers — resolve before public traffic

1. **Production SMS/OTP adapter is not implemented.**
   `smart-building-backend/app/config.py` currently has no approved provider in
   `SUPPORTED_PRODUCTION_SMS_PROVIDERS`. The backend intentionally rejects
   `APP_ENV=production` until a real adapter is implemented and approved. Do not
   bypass this by deploying with `APP_ENV=development`; development returns an OTP
   debug code and is not safe for a public VPS.
2. **Database TLS must match the target PostgreSQL.** The production example uses
   `sslmode=require`. Keep it only when the database endpoint is configured for TLS.
   Do not silently disable TLS for a database reached over an untrusted network.
3. **DWG local storage supports a single backend replica.** For multiple replicas,
   replace the local volume with an approved shared/object storage implementation.
4. Configure a tested backup/restore policy for PostgreSQL and DWG storage before go-live.
5. Power BI embed configuration and its backend-issued token must be configured if
   managerial analytics is enabled. No Power BI secret belongs in the frontend.

## Required VPS prerequisites

- Linux VPS with Docker Engine and Docker Compose v2
- A domain and TLS termination through the platform ingress/reverse proxy
- Private container registry or permission to build images on the VPS
- PostgreSQL backup destination and persistent disk
- Approved SMS provider credentials stored outside Git and outside the image
- At least 2 CPU cores, 4 GB RAM, and sufficient persistent storage for the initial deployment

## Files to review

- `smart-building-backend/.env.production.example`
- `smart-building-backend/compose.prod.example.yaml`
- `deploy/compose.frontend.yaml`
- `deploy/deploy.env.example`
- `smart-building-backend/docs/backend-deployment-runbook.md`
- `docs/frontend-deployment-runbook.md`
- `smart-building-backend/docs/backup-and-restore-runbook.md`
- `docs/frontend-deployment-rollback.md`
- `smart-building-backend/docs/backend-deployment-rollback.md`

## Build immutable images

Run from the extracted package root. Replace `<registry>` with the deployment registry.

```bash
export BAMBO_RELEASE=fdf2fdfa02cc92049f93e26413358ca4978a3a81

docker build \
  -f smart-building-backend/Dockerfile \
  -t <registry>/bambo-backend:${BAMBO_RELEASE} \
  smart-building-backend

docker build \
  -f smart-building-frontend/Dockerfile \
  --build-arg BAMBO_RELEASE=${BAMBO_RELEASE} \
  -t <registry>/bambo-frontend:${BAMBO_RELEASE} \
  .
```

The frontend production build generates `runtime-config.js` with `/backend`.
Nginx proxies `/backend/*` to the Docker DNS name `bambo-backend:8000`.

## Prepare secrets and environment

```bash
cp smart-building-backend/.env.production.example smart-building-backend/.env.production
cp deploy/deploy.env.example deploy/deploy.env
install -d -m 700 deploy/secrets
openssl rand -base64 48 > deploy/secrets/postgres_password
chmod 600 deploy/secrets/postgres_password
```

Replace every `REPLACE_*`, `example.invalid`, image name, host, release, provider,
and proxy CIDR before continuing. Generate `AUTH_SECRET` independently:

```bash
openssl rand -hex 48
```

Never send the completed `.env.production` or files under `deploy/secrets/` through Git or chat.

## Validate configuration

After the production SMS adapter has been implemented:

```bash
docker compose \
  --env-file deploy/deploy.env \
  -f smart-building-backend/compose.prod.example.yaml \
  -f deploy/compose.frontend.yaml \
  config
```

Confirm that no placeholder remains:

```bash
grep -RInE 'REPLACE_|example\.invalid|<registry>' \
  smart-building-backend/.env.production deploy/deploy.env
```

## Database backup and deployment

For an existing environment, take and verify a PostgreSQL backup and a DWG snapshot first.
The migration service is designed to run once before backend startup.

```bash
docker compose \
  --env-file deploy/deploy.env \
  -f smart-building-backend/compose.prod.example.yaml \
  -f deploy/compose.frontend.yaml \
  pull

docker compose \
  --env-file deploy/deploy.env \
  -f smart-building-backend/compose.prod.example.yaml \
  -f deploy/compose.frontend.yaml \
  up -d db

docker compose \
  --env-file deploy/deploy.env \
  -f smart-building-backend/compose.prod.example.yaml \
  -f deploy/compose.frontend.yaml \
  run --rm migrate

docker compose \
  --env-file deploy/deploy.env \
  -f smart-building-backend/compose.prod.example.yaml \
  -f deploy/compose.frontend.yaml \
  up -d backend frontend
```

Do not run two migration jobs concurrently.

## Reverse proxy and TLS

Publish the frontend container only through the VPS reverse proxy. The overlay binds
it to `127.0.0.1:8080`; terminate TLS at the host proxy and forward to that address.
Set the public HTTPS origin in `CORS_ORIGINS` and the public API/domain host in
`TRUSTED_HOSTS`. Preserve the forwarded headers and configure `FORWARDED_ALLOW_IPS`
to the actual reverse-proxy IP/CIDR—not `*`.

## Verification after deployment

```bash
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
```

Then test through the public HTTPS domain:

1. Frontend loads without mixed-content or CSP errors.
2. Real OTP is delivered and verification succeeds.
3. `/auth/me`, logout, refresh/session handling, and permissions work.
4. Pilot list/detail and stages 1–19 load with the real database.
5. Stage submission, rejection/resubmission, Gates, Forms F01–F05, Incidents,
   Notifications, Dashboard, DWG upload/download, and Persian dates work.
6. Unauthorized users receive 403 and cannot see protected actions.
7. Check frontend/backend health, 5xx rate, DB pool, SMS delivery failures,
   storage errors, and latency for at least 15 minutes before accepting traffic.

## Super-admin bootstrap

Use `ALLOW_SUPER_ADMIN_BOOTSTRAP=true` and `BOOTSTRAP_SUPER_ADMIN_MOBILE` only in a
controlled one-time deployment window. After the account is created, remove both
variables and restart the backend. Never store the bootstrap mobile in logs or Git.

## Rollback

1. Keep the previous immutable frontend/backend image digests.
2. Stop traffic to the failing release.
3. Restore the previous image pair.
4. Downgrade a migration only after reviewing it and confirming backup integrity.
5. Re-run `/health/live`, `/health/ready`, login, pilot, stage, and DWG smoke tests.

See the rollback documents listed above for the complete procedure.

