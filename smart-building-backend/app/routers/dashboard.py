"""Operational dashboard and BI-safe read-only endpoints."""

import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.policies import is_super_admin_role_names
from app.database import get_db
from app.schemas.dashboard import DashboardResponse, EmbedTokenResponse
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


@router.get("/powerbi/embed-token", response_model=EmbedTokenResponse)
def powerbi_embed_token(
    context: AuthContext = Depends(require_permission("reports.powerbi")),
) -> EmbedTokenResponse:
    """Return an embed token only when an approved token broker is configured.

    A Power BI client secret is deliberately never returned by this API. In the
    current deployment the token broker is external, so missing configuration is
    reported as a service-unavailable response instead of exposing credentials.
    """
    values = {key: os.getenv(key) for key in ("POWERBI_TENANT_ID", "POWERBI_WORKSPACE_ID", "POWERBI_REPORT_ID", "POWERBI_DATASET_ID", "POWERBI_EMBED_TOKEN")}
    if not all(values.values()):
        raise HTTPException(status_code=503, detail="Power BI embed service is not configured")
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    return EmbedTokenResponse(
        tenant_id=values["POWERBI_TENANT_ID"],
        workspace_id=values["POWERBI_WORKSPACE_ID"],
        report_id=values["POWERBI_REPORT_ID"],
        dataset_id=values["POWERBI_DATASET_ID"],
        embed_token=values["POWERBI_EMBED_TOKEN"],
        expires_at=expires_at,
    )
