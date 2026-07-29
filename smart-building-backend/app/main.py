"""FastAPI entrypoint for the BAMBO Pilot Backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import ensure_schema, get_session
from app.exceptions import SecurityError, WorkflowError
from app.routers.pilots import router as pilots_router
from app.routers.product import router as product_router
from app.routers.operations import router as operations_router
from app.routers.experience import router as experience_router
from app.routers.evaluation import router as evaluation_router
from app.routers.commercial import router as commercial_router
from app.routers.security import audit_router, auth_router, roles_router, users_router
from app.services.security import seed_security_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    with get_session() as db:
        seed_security_data(db)
    yield


app = FastAPI(title="BAMBO Pilot Backend", version="0.8.0", lifespan=lifespan)
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


@app.exception_handler(WorkflowError)
async def workflow_error_handler(_, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.exception_handler(SecurityError)
async def security_error_handler(_, exc: SecurityError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.response_body())


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
