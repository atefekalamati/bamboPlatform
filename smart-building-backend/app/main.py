"""FastAPI entrypoint for the BAMBO Pilot Backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import ensure_schema, get_session
from app.exceptions import SecurityError, WorkflowError
from app.routers.pilots import router as pilots_router
from app.routers.security import audit_router, auth_router, roles_router, users_router
from app.services.security import seed_security_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    with get_session() as db:
        seed_security_data(db)
    yield


app = FastAPI(title="BAMBO Pilot Backend", version="0.3.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(audit_router)
app.include_router(pilots_router)


@app.exception_handler(WorkflowError)
async def workflow_error_handler(_, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.exception_handler(SecurityError)
async def security_error_handler(_, exc: SecurityError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
