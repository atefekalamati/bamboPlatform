# BAMBO Pilot Backend

Backend MVP for the BAMBO pilot checklist and workflow platform. The product
contract is defined by `BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Implemented

- FastAPI application and OpenAPI documentation
- PostgreSQL production configuration with psycopg
- Alembic schema migrations and PostgreSQL JSONB storage
- SQLite-isolated unit and migration tests
- OTP request/verify flow with expiry, attempt limits, mobile/IP rate limiting, and masking
- Opaque bearer sessions with hashed tokens and revocation
- User, role, grouped permission, and toggle-style RBAC APIs
- Backend permission enforcement for every Pilot workflow endpoint
- Audit logging for authentication, users, roles, permissions, and stage transitions
- Unique `PIL-{year}-{sequence}` and `project-{number}` identifiers
- Automatic creation of all 19 PRD stages and gates G1 through G5
- Sequential stage locking and transition validation
- Stage submission, approval, rejection, and revision versions
- Field-level `STAGE_VALIDATION_FAILED` error contract
- SHA-256 hashed immutable JSON snapshots after approval
- Initial building/equipment/sensor scaffold from the earlier prototype

See `docs/implementation-status.md` for PRD coverage and remaining work.

## Workflow API

- `GET /pilots`
- `POST /pilots`
- `GET /pilots/{id}`
- `POST /pilots/{id}/stages/{stage}/submit`
- `POST /pilots/{id}/stages/{stage}/approve`
- `POST /pilots/{id}/stages/{stage}/reject`
- `GET /pilots/{id}/stages/{stage}/snapshots`

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
- `GET /audit`

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

## Test

```powershell
python -m pytest -q
```

Production schema changes must be made through Alembic. The application does
not call `create_all` for PostgreSQL. SQLite schema creation remains available
only for isolated tests and lightweight local diagnostics.
