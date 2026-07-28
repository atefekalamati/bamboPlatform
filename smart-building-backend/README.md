# BAMBO Pilot Backend

Backend MVP for the BAMBO pilot checklist and workflow platform. The product
contract is defined by `BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Implemented

- FastAPI application and OpenAPI documentation
- PostgreSQL production configuration with psycopg
- Alembic schema migrations and PostgreSQL JSONB storage
- SQLite-isolated unit and migration tests
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

## Test

```powershell
python -m pytest -q
```

Production schema changes must be made through Alembic. The application does
not call `create_all` for PostgreSQL. SQLite schema creation remains available
only for isolated tests and lightweight local diagnostics.
