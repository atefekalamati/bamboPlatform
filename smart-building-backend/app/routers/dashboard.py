"""Operational dashboard read-only endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import breakdown, dashboard_actions, dashboard_pilots, dashboard_summary
from app.services.security import AuthContext, require_permission

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardResponse)
def summary(
    context: AuthContext = Depends(require_permission("dashboard.read")),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return dashboard_summary(db, context)


@router.get("/pilots", response_model=DashboardResponse)
def pilots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=160),
    stage: int | None = Query(None, ge=1, le=19),
    status: str | None = Query(None, max_length=40),
    sla: str | None = Query(None, pattern="^(on_track|at_risk|overdue|not_applicable)$"),
    sort: str = Query("updated", pattern="^(updated|stage|sla|code)$"),
    context: AuthContext = Depends(require_permission("dashboard.read")),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return dashboard_pilots(db, context, page=page, page_size=page_size, q=q, stage=stage, status=status, sla=sla, sort=sort)


@router.get("/my-actions", response_model=DashboardResponse)
def my_actions(
    context: AuthContext = Depends(require_permission("dashboard.read")),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return dashboard_actions(db, context)


@router.get("/{kind}", response_model=DashboardResponse)
def dashboard_breakdown(
    kind: str,
    context: AuthContext = Depends(require_permission("dashboard.read")),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    allowed = {"stages", "gates", "missions", "incidents", "sla", "forms", "commercial", "activities"}
    if kind not in allowed:
        raise HTTPException(status_code=404, detail="Dashboard section not found")
    return breakdown(db, context, kind)
