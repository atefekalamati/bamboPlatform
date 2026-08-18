"""FastAPI entrypoint for the BAMBO Pilot Backend."""

from contextlib import asynccontextmanager
import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import (
    get_app_env,
    get_cors_origin_regex,
    get_cors_origins,
    get_docs_enabled,
    get_dwg_storage_root,
    get_log_level,
    get_release_version,
    get_trusted_hosts,
    validate_production_settings,
)
from app.database import ensure_schema, get_session
from app.exceptions import SecurityError, WorkflowError
from app.routers.pilots import router as pilots_router
from app.routers.product import router as product_router
from app.routers.operations import router as operations_router
from app.routers.experience import router as experience_router
from app.routers.evaluation import router as evaluation_router
from app.routers.forms import router as forms_router
from app.routers.notifications import router as notifications_router
from app.routers.commercial import router as commercial_router
from app.routers.security import audit_router, auth_router, roles_router, users_router
from app.routers.dashboard import router as dashboard_router
from app.routers.reports import router as reports_router
from app.routers.calls import router as calls_router
from app.services.security import seed_security_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    logging.basicConfig(
        level=getattr(logging, get_log_level()),
        format="%(message)s",
        force=True,
    )
    ensure_schema()
    with get_session() as db:
        seed_security_data(db)
    yield


docs_enabled = get_docs_enabled()
app = FastAPI(
    title="BAMBO Pilot Backend",
    version="0.8.0",
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_trusted_hosts())
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=get_cors_origin_regex(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(audit_router)
app.include_router(pilots_router)
app.include_router(product_router)
app.include_router(operations_router)
app.include_router(experience_router)
app.include_router(evaluation_router)
app.include_router(commercial_router)
app.include_router(forms_router)
app.include_router(notifications_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(calls_router)


@app.exception_handler(WorkflowError)
async def workflow_error_handler(_, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.exception_handler(SecurityError)
async def security_error_handler(_, exc: SecurityError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/live", tags=["health"])
def health_live() -> dict[str, str]:
    return {"status": "live"}


def _migration_is_current(db) -> bool:
    if get_app_env() != "production":
        return True
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    current = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    config = Config("alembic.ini")
    expected = ScriptDirectory.from_config(config).get_current_head()
    return current == expected


@app.get("/health/ready", tags=["health"])
def health_ready(response: Response) -> dict[str, object]:
    checks = {"database": False, "migration": False, "storage": False}
    try:
        with get_session() as db:
            db.execute(text("SELECT 1"))
            checks["database"] = True
            checks["migration"] = _migration_is_current(db)
        root = get_dwg_storage_root()
        root.mkdir(parents=True, exist_ok=True)
        probe = root / f".readiness-{uuid4().hex}"
        probe.write_bytes(b"ok")
        probe.unlink()
        checks["storage"] = True
    except Exception:
        logging.getLogger("bambo.health").exception("readiness_check_failed")
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "checks": checks}


@app.get("/version", tags=["health"])
def version() -> dict[str, str]:
    return {"service": "bambo-backend", "release": get_release_version()}


@app.middleware("http")
async def production_security_and_logging(request: Request, call_next):
    started = perf_counter()
    supplied_request_id = request.headers.get("X-Request-ID", "")[:128]
    request_id = (
        supplied_request_id
        if re.fullmatch(r"[A-Za-z0-9._:-]+", supplied_request_id)
        else uuid4().hex
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith(("/auth", "/users", "/roles", "/audit")):
        response.headers["Cache-Control"] = "no-store"
    if get_app_env() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logging.getLogger("bambo.request").info(
        json.dumps(
            {
                "event": "http_request",
                "environment": get_app_env(),
                "release": get_release_version(),
                "request_id": request_id,
                "route": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
            separators=(",", ":"),
        )
    )
    return response
