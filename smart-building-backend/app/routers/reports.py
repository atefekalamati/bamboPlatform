"""Read-only, scope-aware management reporting API."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reports import ReportFilters, ReportResponse
from app.services.reports import (
    report_actions, report_external_evidence, report_gates, report_incidents,
    report_kpis, report_one_page, report_overview, report_pipeline,
    report_pilots, report_sla,
)
from app.services.security import AuthContext, require_permission

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def common_filters(
    date_from: datetime | None = Query(None), date_to: datetime | None = Query(None),
    pilot_id: int | None = Query(None, ge=1), project_id: int | None = Query(None, ge=1),
    pilot_status: str | None = Query(None, max_length=40), stage: int | None = Query(None, ge=1, le=19),
    stage_status: str | None = Query(None, max_length=32), gate: str | None = Query(None, pattern="^G[1-5]$"),
    sla: str | None = Query(None, pattern="^(on_track|at_risk|overdue|not_applicable)$"),
    assignee_id: int | None = Query(None, ge=1), has_open_incident: bool | None = Query(None),
    has_critical_incident: bool | None = Query(None), final_outcome: str | None = Query(None, max_length=24),
    q: str | None = Query(None, max_length=160), page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), sort: str = Query("updated", max_length=40),
) -> ReportFilters:
    try:
        return ReportFilters(**locals())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc


@router.get("/overview", response_model=ReportResponse)
def overview(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_overview(db, context, filters)

@router.get("/pipeline", response_model=ReportResponse)
def pipeline(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_pipeline(db, context, filters)

@router.get("/pilots", response_model=ReportResponse)
def pilots(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_pilots(db, context, filters)

@router.get("/gates", response_model=ReportResponse)
def gates(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_gates(db, context, filters)

@router.get("/actions", response_model=ReportResponse)
def actions(due: str | None = Query(None, pattern="^(today|overdue|upcoming|without_due_date)$"), priority: str | None = Query(None, pattern="^(critical|high|medium|low)$"), entity_type: str | None = Query(None), filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_actions(db, context, filters, due=due, priority=priority, entity_type=entity_type)

@router.get("/sla", response_model=ReportResponse)
def sla(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.sla")), db: Session = Depends(get_db)):
    return report_sla(db, context, filters)

@router.get("/kpis", response_model=ReportResponse)
def kpis(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.kpi")), db: Session = Depends(get_db)):
    return report_kpis(db, context, filters)

@router.get("/incidents", response_model=ReportResponse)
def incidents(filters: ReportFilters = Depends(common_filters), context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_incidents(db, context, filters)

@router.get("/pilots/{pilot_id}/one-page", response_model=ReportResponse)
def one_page(pilot_id: int, context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_one_page(db, context, pilot_id)

@router.get("/pilots/{pilot_id}/external-evidence", response_model=ReportResponse)
def external_evidence(pilot_id: int, context: AuthContext = Depends(require_permission("reports.read")), db: Session = Depends(get_db)):
    return report_external_evidence(db, context, pilot_id)
