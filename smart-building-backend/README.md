# BAMBO Pilot Backend

Backend MVP for the BAMBO pilot checklist and workflow platform. The product
contract is defined by `BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Implemented

- FastAPI application and OpenAPI documentation
- SQLAlchemy database and session management
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
uvicorn app.main:app --reload
```

OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

## Test

```powershell
python -m pytest -q
```

SQLite is currently used for local development and tests. PostgreSQL and
Alembic migrations remain required before production deployment.
