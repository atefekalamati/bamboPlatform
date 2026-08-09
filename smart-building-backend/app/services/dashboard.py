"""Read-only, scope-aware operational dashboard queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AuditLog,
    CommercialProposal,
    CustomerFollowUp,
    ExternalEvidenceCheck,
    FinalOutcome,
    Incident,
    Mission,
    Pilot,
    FormF04,
    Project,
    User,
)
from app.models.workflow import PilotGate, PilotStage, StageSubmission
from app.services.security import AuthContext, effective_permissions
from app.schemas.dashboard import ActionItem, DashboardResponse, Pagination, PilotDashboardItem


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _roles(context: AuthContext) -> set[str]:
    return {role.name for role in context.user.roles if role.is_active}


def _all_access(context: AuthContext) -> bool:
    permissions = effective_permissions(context.user)
    return bool({"super_admin"} & _roles(context)) or "dashboard.read_all" in permissions or "pilots.read_all" in permissions


def scoped_pilots_query(db: Session, context: AuthContext):
    query = db.query(Pilot)
    if _all_access(context):
        return query
    roles = _roles(context)
    # Roles whose business responsibility is cross-pilot may see the operational
    # overview; restricted roles are limited to records assigned to the user.
    if roles.intersection({"pilot_manager", "operations", "support", "customer_success", "product_manager"}):
        return query
    user_id = context.user.id
    return query.filter(
        or_(
            Pilot.missions.any(Mission.expert_user_id == user_id),
            Pilot.missions.any(Mission.created_by_user_id == user_id),
            Pilot.incidents.any(Incident.owner_user_id == user_id),
            Pilot.customer_follow_ups.any(CustomerFollowUp.owner_user_id == user_id),
            Pilot.commercial_proposal.has(CommercialProposal.responsible_user_id == user_id),
            Pilot.form_f04.has(or_(
                FormF04.responsible_user_id == user_id,
                FormF04.sales_user_id == user_id,
                FormF04.customer_success_user_id == user_id,
            )),
        )
    )


def _load_pilots(query):
    return query.options(
        selectinload(Pilot.project).selectinload(Project.owner),
        selectinload(Pilot.stages).selectinload(PilotStage.submissions).selectinload(StageSubmission.review),
        selectinload(Pilot.gates),
        selectinload(Pilot.missions).selectinload(Mission.form_f03),
        selectinload(Pilot.missions).selectinload(Mission.expert),
        selectinload(Pilot.missions).selectinload(Mission.floor_states),
        selectinload(Pilot.incidents).selectinload(Incident.owner),
        selectinload(Pilot.customer_follow_ups).selectinload(CustomerFollowUp.owner),
        selectinload(Pilot.form_f04).selectinload(FormF04.responsible),
        selectinload(Pilot.form_f04).selectinload(FormF04.pilot_manager_user),
        selectinload(Pilot.commercial_proposal).selectinload(CommercialProposal.responsible),
        selectinload(Pilot.final_outcome),
        selectinload(Pilot.evaluation),
        selectinload(Pilot.external_evidence_checks).selectinload(ExternalEvidenceCheck.checked_by),
        selectinload(Pilot.notifications),
        selectinload(Pilot.form_f01),
        selectinload(Pilot.form_f02),
    )


def _sla_for_pilot(pilot: Pilot, now: datetime) -> str:
    due_dates = [m.sla_due_at for m in pilot.missions if m.status not in {"completed", "cancelled"}]
    due_dates.extend(i.response_due_at for i in pilot.incidents if i.status != "closed")
    if not due_dates:
        return "not_applicable"
    if min(due_dates) < now:
        return "overdue"
    if min(due_dates) <= now + timedelta(hours=48):
        return "at_risk"
    return "on_track"


def _pilot_item(pilot: Pilot, now: datetime) -> PilotDashboardItem:
    stage = next((s for s in pilot.stages if s.number == pilot.current_stage), None)
    gate = next((g for g in pilot.gates if g.status not in {"passed", "approved"} and g.after_stage <= pilot.current_stage), None)
    stage_count = len(pilot.stages) or 19
    open_incidents = [i for i in pilot.incidents if i.status != "closed"]
    due_dates = [m.sla_due_at for m in pilot.missions if m.status not in {"completed", "cancelled"}]
    due_at = min(due_dates) if due_dates else None
    assignee = None
    if stage and stage.submissions:
        assignee = stage.submissions[-1].submitted_by
    commercial = pilot.commercial_proposal
    outcome = pilot.final_outcome
    return PilotDashboardItem(
        id=pilot.id,
        pilot_code=pilot.code,
        project=pilot.project.display_name if pilot.project else pilot.display_name,
        owner_company=pilot.project.owner.name if pilot.project and pilot.project.owner else None,
        current_stage=pilot.current_stage,
        pilot_status=pilot.status,
        stage_status=stage.status if stage else None,
        progress_percent=round(
            min(100.0, sum(stage.status == "approved" for stage in pilot.stages) / stage_count * 100),
            2,
        ),
        current_assignee=assignee,
        next_action=("review" if stage and stage.status == "submitted" else "complete_stage" if stage and stage.status in {"open", "needs_revision"} else None),
        due_at=due_at,
        sla_status=_sla_for_pilot(pilot, now),
        open_incidents=len(open_incidents),
        critical_incidents=sum(1 for i in open_incidents if i.severity == "critical"),
        current_gate=gate.code if gate else None,
        commercial_status="proposal_sent" if commercial else None,
        final_outcome=outcome.outcome if outcome else None,
        last_updated_at=pilot.updated_at,
    )


def visible_pilots(db: Session, context: AuthContext) -> list[Pilot]:
    return _load_pilots(scoped_pilots_query(db, context).order_by(Pilot.updated_at.desc(), Pilot.id)).all()


def dashboard_summary(db: Session, context: AuthContext) -> DashboardResponse:
    now = _now()
    items = [_pilot_item(p, now) for p in visible_pilots(db, context)]
    all_total = db.query(Pilot.id).count()
    if not items:
        state = "NO_DATA" if all_total == 0 else "NO_ACCESS"
    else:
        state = "SUCCESS"
    summary = {
        "total_pilots": len(items),
        "active": sum(1 for p in items if p.pilot_status not in {"completed", "closed", "converted", "rejected", "stopped"}),
        "completed": sum(1 for p in items if p.current_stage >= 19),
        "stopped": sum(1 for p in items if p.final_outcome in {"closed", "rejected"}),
        "contracted": sum(1 for p in items if p.final_outcome == "contract"),
        "waiting_action": sum(1 for p in items if p.next_action),
        "sla_at_risk": sum(1 for p in items if p.sla_status == "at_risk"),
        "sla_overdue": sum(1 for p in items if p.sla_status == "overdue"),
        "open_critical_incidents": sum(p.critical_incidents for p in items),
        "blocked_gates": sum(1 for p in items if p.current_gate),
        "without_assignee": sum(1 for p in items if not p.current_assignee),
        "without_due_at": sum(1 for p in items if not p.due_at),
    }
    return DashboardResponse(generated_at=now.replace(tzinfo=UTC), filters={}, summary=summary, items=[], state=state)


def dashboard_pilots(db: Session, context: AuthContext, *, page: int, page_size: int, q: str | None, stage: int | None, status: str | None, sla: str | None, sort: str) -> DashboardResponse:
    now = _now()
    pilots = visible_pilots(db, context)
    items = [_pilot_item(p, now) for p in pilots]
    if q:
        needle = q.casefold()
        items = [p for p in items if needle in p.pilot_code.casefold() or needle in p.project.casefold() or (p.owner_company and needle in p.owner_company.casefold())]
    if stage is not None:
        items = [p for p in items if p.current_stage == stage]
    if status:
        items = [p for p in items if p.stage_status == status or p.final_outcome == status]
    if sla:
        items = [p for p in items if p.sla_status == sla]
    if sort == "stage":
        items.sort(key=lambda p: (p.current_stage, p.id))
    elif sort == "sla":
        items.sort(key=lambda p: (p.sla_status, p.due_at or datetime.max))
    elif sort == "code":
        items.sort(key=lambda p: p.pilot_code)
    total = len(items)
    start = (page - 1) * page_size
    state = "SUCCESS" if total else ("NO_DATA" if db.query(Pilot.id).count() == 0 else "NO_ACCESS")
    return DashboardResponse(
        generated_at=now.replace(tzinfo=UTC), filters={"q": q, "stage": stage, "status": status, "sla": sla, "sort": sort},
        summary={}, items=items[start:start + page_size], pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size) if total else 0), state=state,
    )


def dashboard_actions(db: Session, context: AuthContext) -> DashboardResponse:
    now = _now()
    pilots = visible_pilots(db, context)
    result: list[ActionItem] = []
    roles = _roles(context)
    for pilot in pilots:
        stage = next((s for s in pilot.stages if s.number == pilot.current_stage), None)
        if stage and stage.status in {"open", "needs_revision", "submitted"}:
            action = "review" if stage.status == "submitted" else "complete"
            result.append(ActionItem(id=f"stage:{pilot.id}:{stage.number}", priority="HIGH" if stage.status == "submitted" else "NORMAL", entity_type="stage", entity_id=stage.id, pilot_id=pilot.id, title=f"{action} stage {stage.number}", action_url=f"/pilots/{pilot.id}/stages/{stage.number}", status=stage.status))
        for mission in pilot.missions:
            if mission.status not in {"completed", "cancelled"} and (mission.expert_user_id == context.user.id or roles.intersection({"super_admin", "operations"})):
                result.append(ActionItem(id=f"mission:{mission.id}", priority="HIGH" if mission.sla_due_at < now else "NORMAL", entity_type="mission", entity_id=mission.id, pilot_id=pilot.id, title="Mission requires action", due_at=mission.sla_due_at, action_url=f"/missions/{mission.id}"))
        for incident in pilot.incidents:
            if incident.status != "closed" and (incident.owner_user_id == context.user.id or _all_access(context)):
                result.append(ActionItem(id=f"incident:{incident.id}", priority="CRITICAL" if incident.severity == "critical" else "HIGH", entity_type="incident", entity_id=incident.id, pilot_id=pilot.id, title="Incident requires action", due_at=incident.response_due_at, action_url=f"/pilots/{pilot.id}/incidents/{incident.id}"))
        for follow_up in pilot.customer_follow_ups:
            if follow_up.completed_at is None and follow_up.owner_user_id == context.user.id:
                result.append(ActionItem(id=f"followup:{follow_up.id}", priority="NORMAL", entity_type="customer_follow_up", entity_id=follow_up.id, pilot_id=pilot.id, title="Customer follow-up", due_at=follow_up.due_at, action_url=f"/pilots/{pilot.id}/customer-success"))
    return DashboardResponse(generated_at=now.replace(tzinfo=UTC), filters={}, summary={"count": len(result)}, items=result, state="SUCCESS" if result else "NO_DATA")


def breakdown(db: Session, context: AuthContext, kind: str) -> DashboardResponse:
    now = _now()
    pilots = visible_pilots(db, context)
    items: list[dict[str, Any]] = []
    if kind == "stages":
        for number in range(1, 20):
            stages = [s for p in pilots for s in p.stages if s.number == number]
            items.append({"stage": number, "title": stages[0].title if stages else None, "total": len(stages), "submitted": sum(s.status == "submitted" for s in stages), "approved": sum(s.status == "approved" for s in stages), "open": sum(s.status == "open" for s in stages)})
    elif kind == "gates":
        for code in ("G1", "G2", "G3", "G4", "G5"):
            gates = [g for p in pilots for g in p.gates if g.code == code]
            items.append({"gate": code, "total": len(gates), "passed": sum(g.status in {"passed", "approved"} for g in gates), "blocked": sum(g.status not in {"passed", "approved"} for g in gates)})
    elif kind == "missions":
        missions = [m for p in pilots for m in p.missions]
        items = [{"status": value, "count": sum(m.status == value for m in missions)} for value in ("scheduled", "assigned", "ready", "in_progress", "completed", "cancelled")]
    elif kind == "incidents":
        incidents = [i for p in pilots for i in p.incidents]
        items = [{"severity": value, "open": sum(i.severity == value and i.status != "closed" for i in incidents), "total": sum(i.severity == value for i in incidents)} for value in ("normal", "important", "critical")]
    elif kind == "sla":
        pilot_items = [_pilot_item(p, now) for p in pilots]
        items = [{"status": value, "count": sum(i.sla_status == value for i in pilot_items)} for value in ("on_track", "at_risk", "overdue", "not_applicable")]
    elif kind == "forms":
        for code, attr in (("F01", "form_f01"), ("F02", "form_f02"), ("F04", "form_f04")):
            items.append({"form": code, "completed": sum(getattr(p, attr) is not None for p in pilots), "total": len(pilots)})
        missions = [m for p in pilots for m in p.missions]
        incidents = [i for p in pilots for i in p.incidents]
        items.extend((
            {"form": "F03", "completed": sum(m.form_f03 is not None and m.form_f03.mission_completed for m in missions), "total": len(missions)},
            {"form": "F05", "completed": sum(i.status == "closed" for i in incidents), "total": len(incidents)},
        ))
    elif kind == "commercial":
        outcomes = [p.final_outcome.outcome for p in pilots if p.final_outcome]
        items = [{"outcome": value, "count": outcomes.count(value)} for value in ("contract", "ready_on_date", "negotiation", "rejected", "closed")]
    elif kind == "activities":
        pilot_ids = [p.id for p in pilots]
        logs = db.query(AuditLog).filter(AuditLog.pilot_id.in_(pilot_ids)).order_by(AuditLog.created_at.desc()).limit(50).all() if pilot_ids else []
        items = [{"id": log.id, "action": log.action, "entity_type": log.entity_type, "entity_id": log.entity_id, "pilot_id": log.pilot_id, "created_at": log.created_at} for log in logs]
    return DashboardResponse(generated_at=now.replace(tzinfo=UTC), filters={"kind": kind}, summary={"count": len(items)}, items=items, state="SUCCESS" if pilots else ("NO_DATA" if db.query(Pilot.id).count() == 0 else "NO_ACCESS"))
