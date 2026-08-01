# BAMBO Pilot Backend

Backend MVP for the BAMBO pilot checklist and workflow platform. The product
contract is defined by `BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Implemented

- FastAPI application and OpenAPI documentation
- GitHub Actions CI for every pull request and push to `master`
- Live PostgreSQL migration, schema-drift, JSONB, persistence, and reversible
  migration checks in CI
- PostgreSQL production configuration with psycopg
- Alembic schema migrations and PostgreSQL JSONB storage
- SQLite-isolated unit and migration tests
- OTP request/verify flow with expiry, attempt limits, mobile/IP rate limiting, and masking
- Opaque bearer sessions with hashed tokens and revocation
- User, role, grouped permission, and toggle-style RBAC APIs
- Backend permission enforcement for every Pilot workflow endpoint
- Audit logging for authentication, users, roles, permissions, and stage transitions
- Unique `PIL-{year}-{sequence}` and `project-{number}` identifiers
- Canonical Owner, primary Contact, Project, F01-F05, Floor, DWG, Mission,
  external-status, evidence-check, and Incident entities
- F01-driven stages 1/2 and F02-driven stage 4; client checklist payloads cannot
  override the canonical form data
- Secure DWG-only streaming upload with extension, MIME, signature, and size checks
- SHA-256 duplicate detection, per-Floor version history, protected download, and
  standardized Jalali-date filenames
- Automatic reopening of affected workflow stages when approved source data or a
  DWG version changes
- Mission scheduling with `MIS-{pilotCode}-{sequence}` codes, expert overlap
  protection, per-Floor capture state, and a one-day SLA deadline
- F03-driven stages 5-9 and G3 validation, including mobile readiness, Stop
  Conditions, capture state, and main-platform Upload status
- Mission-created/rescheduled notification records with console delivery in
  development/test and explicit provider-failure recording in production
- Read-only external-platform status/reference tracking without Viewer, tour URL,
  report payload, or platform integration
- Canonical stages 10-13 and G4 validation for processing readiness, output
  notification, owner training, follow-up, and owner viewing
- F04 customer-success tracking with issue routing, assignee/deadline, feedback,
  value, training, decision-maker, next-action, and commercial-readiness fields
- F05 Incident lifecycle with `INC-{pilotCode}-{sequence}` codes, severity/type,
  containment, corrective action, closure approval, immutable audit history, and
  response SLA deadlines
- Critical Incident blocking for G4, including automatic stage-13 reopening while
  preserving prior approved snapshots
- External evidence checks that persist only capability, status, checker, time,
  and a short result
- Main-output notification records with delivered/failed status and alternate
  delivery registration when SMS fails
- Continuation-capture Missions with per-cycle revalidation of stages 5-13 and
  an independent result; updates reopen stage 14 without rewriting earlier gates
- Five-dimension operations/quality/technical/customer/commercial evaluation
  with a text-only one-page summary
- Canonical stages 14-16 and G5 validation using all continuation cycles,
  minimal external-evidence status, evaluation, and F04 closing-session data
- CommercialProposal persistence for stage 17 with project/floor/area/frequency,
  period, users, support, feature, decision-maker, follow-up, and secure
  proposal-file metadata (name, size, and SHA-256 only; no path or URL)
- Four-slot customer follow-up calendar for stage 18 (`day_0`, `day_2`,
  `day_5`, and `day_7_10`) with obstacle, action, owner, due time, and result
- Canonical final outcome for stage 19, including contract handoff details,
  dedicated Pilot Manager confirmation, source-change invalidation, and
  preserved immutable snapshots
- Automatic creation of all 19 PRD stages and gates G1 through G5
- Sequential stage locking and transition validation
- Stage submission, approval, rejection, and revision versions
- Field-level `STAGE_VALIDATION_FAILED` error contract
- SHA-256 hashed immutable JSON snapshots after approval

See `docs/implementation-status.md` for PRD coverage and remaining work.

## Workflow API

- `GET /pilots`
- `POST /pilots`
- `GET /pilots/{id}`
- `POST /pilots/{id}/stages/{stage}/submit`
- `POST /pilots/{id}/stages/{stage}/approve`
- `POST /pilots/{id}/stages/{stage}/reject`
- `GET /pilots/{id}/stages/{stage}/snapshots`

## Project data and DWG API

- `GET|PUT /pilots/{id}/forms/f01`
- `GET|PUT /pilots/{id}/forms/f02`
- `GET|POST /pilots/{id}/floors`
- `POST /floors/{id}/dwg`
- `GET /floors/{id}/dwg/versions`
- `GET /dwg/versions/{id}/download`

## Mission and F03 API

- `GET|POST /pilots/{id}/missions`
- `GET|PATCH /missions/{id}`
- `GET|PUT /missions/{id}/forms/f03`
- `PUT /missions/{id}/floors/{floor_id}`

## Customer experience, evidence, and Incident API

- `GET|PUT /pilots/{id}/external-platform`
- `GET|PATCH /pilots/{id}/forms/f04`
- `GET /pilots/{id}/external-evidence`
- `PUT /pilots/{id}/external-evidence/{capability}`
- `POST /pilots/{id}/notifications/main-output`
- `GET|POST /pilots/{id}/incidents`
- `GET|PATCH /incidents/{id}`
- `POST /incidents/{id}/close`

## Continuation and evaluation API

- `GET|PUT /missions/{id}/continuation-review`
- `GET|PUT /pilots/{id}/evaluation`

## Commercial closing API

- `GET|PUT /pilots/{id}/commercial-proposal`
- `GET /pilots/{id}/commercial-follow-ups`
- `PUT /pilots/{id}/commercial-follow-ups/{schedule_slot}`
- `GET|PUT /pilots/{id}/final-outcome`
- `POST /pilots/{id}/final-outcome/approve`

## Authentication and RBAC API

- `POST /auth/otp/request`
- `POST /auth/otp/verify`
- `GET /auth/me`
- `POST /auth/logout`
- `GET /users`
- `POST /users`
- `PUT /users/{id}/roles`
- `PATCH /users/{id}/status`
- `GET /roles`
- `POST /roles`
- `GET /roles/permissions`
- `PUT /roles/{id}/permissions`
- `GET /audit` (optional pagination and exact filters for action, entity, actor, and UTC range)

## Run locally

```powershell
cd smart-building-backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d db
python -m alembic upgrade head
uvicorn app.main:app --reload
```

OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

The mobile configured by `BOOTSTRAP_SUPER_ADMIN_MOBILE` receives the
`super_admin` role after its first successful OTP verification. The console
OTP provider and `debug_code` response are enabled only in development/test.
Production intentionally rejects OTP requests until an approved SMS provider
adapter is configured.

Mission notifications are recorded independently from the mission transaction.
Development/test marks the console adapter as delivered. Production records a
failed/unconfigured delivery until the PRD's SMS provider decision is supplied;
the mission itself remains safely persisted for operational follow-up.

Main-output notifications use the same explicit delivery model. Stage 11 accepts
either a delivered provider result or a recorded alternate contact method; a
failed SMS without alternate delivery cannot pass.

Saving or changing a commercial proposal creates a follow-up notification for
the responsible user. Development/test records console delivery; production
records an explicit unconfigured-provider failure until an approved adapter is
available.

DWG files currently use the configurable local backend under
`DWG_STORAGE_ROOT`. `DWG_MAX_BYTES` must be set explicitly in production.
The PRD still requires a product decision for the final storage backend and
maximum file size.

## Test

```powershell
python -m pytest -q
```

The regular suite uses isolated SQLite databases. The PostgreSQL integration
test runs when `POSTGRES_TEST_DATABASE_URL` is set and otherwise reports a
deliberate skip:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://bambo:bambo@localhost:5432/bambo"
$env:POSTGRES_TEST_DATABASE_URL = $env:DATABASE_URL
python -m alembic upgrade head
python -m alembic check
python -m pytest tests/test_postgres_integration.py -q
```

The `Backend CI` workflow runs both suites and verifies that the complete
Alembic chain can downgrade to `base`, upgrade back to `head`, and finish
without schema drift on PostgreSQL 17.

Production schema changes must be made through Alembic. The application does
not call `create_all` for PostgreSQL. SQLite schema creation remains available
only for isolated tests and lightweight local diagnostics.
