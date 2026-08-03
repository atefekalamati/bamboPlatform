"""Decision-oriented reports derived from existing operational aggregates."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from math import ceil
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.exceptions import SecurityError
from app.models import Pilot
from app.schemas.reports import ReportFilters, ReportPagination, ReportResponse
from app.services.dashboard import _pilot_item, _sla_for_pilot, visible_pilots

TOTAL_STAGES = 19
PIPELINE = (
    ("candidate", "نامزد پایلوت"), ("waiting_documents", "در انتظار مدارک"),
    ("ready_for_operation", "آماده برداشت"), ("operations", "عملیات"),
    ("ready_for_customer", "آماده مشاهده"), ("evaluating", "در ارزیابی"),
    ("proposal_sent", "پیشنهاد ارسال‌شده"), ("converted", "تبدیل‌شده"),
    ("closed", "بسته‌شده"),
)
STATUS_TO_PIPELINE = {
    "candidate": "candidate", "waiting_documents": "waiting_documents",
    "ready_for_operation": "ready_for_operation", "operations": "operations",
    "ready_for_customer": "ready_for_customer", "evaluating": "evaluating",
    "proposal_sent": "proposal_sent", "converted": "converted",
    "completed": "closed", "closed": "closed", "rejected": "closed", "stopped": "closed",
}
EVIDENCE_LABELS = {
    "project_summary": "خلاصه وضعیت پروژه", "actual_progress": "پیشرفت واقعی",
    "delay_amount": "میزان عقب‌ماندگی", "last_visit": "آخرین بازدید",
    "planned_vs_actual_chart": "نمودار برنامه‌ای و واقعی", "progress_stages": "مراحل پیشرفت پروژه",
    "area": "زیربنا", "estimated_cost": "برآورد هزینه", "actual_cost": "هزینه انجام‌شده",
    "manager_audio_report": "گزارش صوتی مدیر پروژه", "this_week_report": "گزارش این هفته",
    "next_week_plan": "برنامه هفته آینده", "owner_actions": "اقدامات موردنیاز مالک",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _filters_dict(filters: ReportFilters) -> dict[str, Any]:
    return filters.model_dump(exclude_none=True)


def _state(db: Session, pilots: list[Pilot]) -> str:
    if pilots:
        return "SUCCESS"
    return "NO_DATA" if db.query(Pilot.id).count() == 0 else "NO_ACCESS"


def _current_stage(pilot: Pilot):
    return next((stage for stage in pilot.stages if stage.number == pilot.current_stage), None)


def _current_gate(pilot: Pilot):
    return next((gate for gate in pilot.gates if gate.after_stage >= pilot.current_stage and gate.status not in {"passed", "approved"}), None)


def _approved_count(pilot: Pilot) -> int:
    return sum(stage.status == "approved" for stage in pilot.stages)


def _open_incidents(pilot: Pilot):
    return [incident for incident in pilot.incidents if incident.status != "closed"]


def _assignee(pilot: Pilot):
    stage = _current_stage(pilot)
    if stage and stage.status == "submitted":
        return None, None
    active_mission = next((m for m in pilot.missions if m.status not in {"completed", "cancelled"}), None)
    if active_mission and active_mission.expert:
        return active_mission.expert.id, active_mission.expert.display_name
    if pilot.form_f04 and pilot.form_f04.responsible:
        return pilot.form_f04.responsible.id, pilot.form_f04.responsible.display_name
    return None, None


def _next_action(pilot: Pilot):
    stage = _current_stage(pilot)
    if not stage:
        return None, None
    if stage.status == "submitted":
        return f"بررسی و تصمیم Stage {stage.number}", None
    if stage.status == "needs_revision":
        return f"اصلاح Stage {stage.number}", None
    if stage.status == "open":
        return f"تکمیل Stage {stage.number}", None
    return None, None


def _due_at(pilot: Pilot):
    values = [m.sla_due_at for m in pilot.missions if m.status not in {"completed", "cancelled"}]
    values += [i.response_due_at for i in _open_incidents(pilot) if i.responded_at is None]
    values += [f.due_at for f in pilot.customer_follow_ups if f.completed_at is None]
    if pilot.commercial_proposal and pilot.final_outcome is None:
        values.append(pilot.commercial_proposal.follow_up_at)
    return min(values) if values else None


def _filter_pilots(db: Session, context, filters: ReportFilters) -> list[Pilot]:
    now = _now()
    pilots = visible_pilots(db, context)
    start = filters.date_from.astimezone(UTC).replace(tzinfo=None) if filters.date_from else None
    end = filters.date_to.astimezone(UTC).replace(tzinfo=None) if filters.date_to else None
    result = []
    for pilot in pilots:
        stage = _current_stage(pilot)
        open_items = _open_incidents(pilot)
        outcome = pilot.final_outcome.outcome if pilot.final_outcome else None
        gate = _current_gate(pilot)
        assignee_id, _ = _assignee(pilot)
        if filters.pilot_id and pilot.id != filters.pilot_id: continue
        if filters.project_id and (not pilot.project or pilot.project.id != filters.project_id): continue
        if filters.pilot_status and pilot.status != filters.pilot_status: continue
        if filters.stage and pilot.current_stage != filters.stage: continue
        if filters.stage_status and (not stage or stage.status != filters.stage_status): continue
        if filters.gate and (not gate or gate.code != filters.gate): continue
        if filters.sla and _sla_for_pilot(pilot, now) != filters.sla: continue
        if filters.assignee_id and assignee_id != filters.assignee_id: continue
        if filters.has_open_incident is not None and bool(open_items) != filters.has_open_incident: continue
        if filters.has_critical_incident is not None and any(i.severity == "critical" for i in open_items) != filters.has_critical_incident: continue
        if filters.final_outcome and outcome != filters.final_outcome: continue
        if start and pilot.created_at < start: continue
        if end and pilot.created_at > end: continue
        if filters.q:
            text = f"{pilot.code} {pilot.display_name} {pilot.project.name if pilot.project else ''} {pilot.project.owner.name if pilot.project and pilot.project.owner else ''}".casefold()
            if filters.q.casefold() not in text: continue
        result.append(pilot)
    return result


def _paginate(items: list[dict], filters: ReportFilters):
    total = len(items)
    start = (filters.page - 1) * filters.page_size
    return items[start:start + filters.page_size], ReportPagination(
        page=filters.page, page_size=filters.page_size, total=total,
        total_pages=ceil(total / filters.page_size) if total else 0,
    )


def report_overview(db: Session, context, filters: ReportFilters) -> ReportResponse:
    now = _now(); pilots = _filter_pilots(db, context, filters)
    actions = _action_rows(pilots, now)
    statuses = Counter(STATUS_TO_PIPELINE.get(p.status, "closed") for p in pilots)
    outcomes = Counter(p.final_outcome.outcome for p in pilots if p.final_outcome)
    open_incidents = [i for p in pilots for i in _open_incidents(p)]
    active = [p for p in pilots if not p.final_outcome and p.status not in {"closed", "rejected", "stopped", "converted", "completed"}]
    summary = {
        "total_pilots": len(pilots), "active_pilots": len(active),
        "waiting_documents": statuses["waiting_documents"], "ready_for_operation": statuses["ready_for_operation"],
        "in_operation": statuses["operations"], "ready_for_customer": statuses["ready_for_customer"],
        "under_evaluation": statuses["evaluating"], "proposal_sent": statuses["proposal_sent"],
        "contracted": outcomes["contract"],
        "closed_without_contract": sum(p.status in {"closed", "rejected", "stopped", "completed"} and (not p.final_outcome or p.final_outcome.outcome != "contract") for p in pilots),
        "stopped": sum(p.status == "stopped" for p in pilots),
        "overdue_pilots": sum(_sla_for_pilot(p, now) == "overdue" for p in pilots),
        "at_risk_pilots": sum(_sla_for_pilot(p, now) == "at_risk" for p in pilots),
        "open_incidents": len(open_incidents), "critical_open_incidents": sum(i.severity == "critical" for i in open_incidents),
        "ready_for_commercial_decision": sum(p.current_stage >= 17 and p.final_outcome is None for p in pilots),
        "actions_due_today": sum(bool(a["due_at"] and a["due_at"].date() == now.date()) for a in actions),
        "actions_without_owner": sum(a["assignee_id"] is None for a in actions),
        "actions_without_due_date": sum(a["due_at"] is None for a in actions),
    }
    return ReportResponse(generated_at=now.replace(tzinfo=UTC), filters=_filters_dict(filters), summary=summary, state=_state(db, pilots))


def report_pipeline(db: Session, context, filters: ReportFilters) -> ReportResponse:
    pilots = _filter_pilots(db, context, filters); counts = Counter(STATUS_TO_PIPELINE.get(p.status, "closed") for p in pilots)
    items = [{"key": key, "label": label, "count": counts[key], "drill_down_filter": {"pilot_status": key}} for key, label in PIPELINE]
    return ReportResponse(generated_at=_now().replace(tzinfo=UTC), filters=_filters_dict(filters), summary={"total": len(pilots)}, items=items, state=_state(db, pilots))


def _pilot_row(pilot: Pilot, now: datetime) -> dict:
    stage = _current_stage(pilot); gate = _current_gate(pilot); approved = _approved_count(pilot)
    incidents = _open_incidents(pilot); due = _due_at(pilot); assignee_id, assignee_name = _assignee(pilot); action, _ = _next_action(pilot)
    return {
        "pilot_id": pilot.id, "pilot_code": pilot.code,
        "project_name": pilot.project.name if pilot.project else pilot.display_name,
        "owner_name": pilot.project.owner.name if pilot.project and pilot.project.owner else None,
        "pilot_manager": pilot.form_f04.pilot_manager_user.display_name if pilot.form_f04 and pilot.form_f04.pilot_manager_user else None,
        "pilot_status": pilot.status, "current_stage_number": pilot.current_stage,
        "current_stage_title": stage.title if stage else None, "current_stage_status": stage.status if stage else None,
        "approved_stages_count": approved, "total_stages": TOTAL_STAGES,
        "progress_percent": round(approved / TOTAL_STAGES * 100, 2),
        "current_gate": gate.code if gate else None, "current_gate_status": gate.status if gate else None,
        "current_assignee": {"id": assignee_id, "name": assignee_name} if assignee_id else None,
        "next_action": action, "due_at": due, "sla_status": _sla_for_pilot(pilot, now),
        "overdue_days": max(0, (now - due).days) if due and due < now else 0,
        "open_incidents": len(incidents), "critical_incidents": sum(i.severity == "critical" for i in incidents),
        "last_activity_at": pilot.updated_at,
        "commercial_status": "proposal_sent" if pilot.commercial_proposal else None,
        "final_outcome": pilot.final_outcome.outcome if pilot.final_outcome else None,
    }


def report_pilots(db: Session, context, filters: ReportFilters) -> ReportResponse:
    now = _now(); pilots = _filter_pilots(db, context, filters); rows = [_pilot_row(p, now) for p in pilots]
    if filters.sort == "code": rows.sort(key=lambda x: x["pilot_code"])
    elif filters.sort == "stage": rows.sort(key=lambda x: (x["current_stage_number"], x["pilot_id"]))
    elif filters.sort == "progress": rows.sort(key=lambda x: (-x["progress_percent"], x["pilot_id"]))
    else: rows.sort(key=lambda x: (x["last_activity_at"], x["pilot_id"]), reverse=True)
    items, pagination = _paginate(rows, filters)
    return ReportResponse(generated_at=now.replace(tzinfo=UTC), filters=_filters_dict(filters), summary={"total": len(rows)}, items=items, pagination=pagination, state=_state(db, pilots))


def report_gates(db: Session, context, filters: ReportFilters) -> ReportResponse:
    pilots = _filter_pilots(db, context, filters); rows = []; summary = {}
    for code, label in (("G1", "پذیرش"), ("G2", "آمادگی فنی"), ("G3", "تکمیل عملیات"), ("G4", "تجربه موفق"), ("G5", "آمادگی تجاری")):
        gates = [(p, next(g for g in p.gates if g.code == code)) for p in pilots]
        summary[code] = {"label": label, "approved": sum(g.status in {"passed", "approved"} for _, g in gates), "pending": sum(g.status == "locked" for _, g in gates), "needs_revision": sum(next(s for s in p.stages if s.number == g.after_stage).status == "needs_revision" for p, g in gates), "rejected": 0, "stopped": sum(p.status == "stopped" for p, _ in gates)}
        for pilot, gate in gates:
            stage = next(s for s in pilot.stages if s.number == gate.after_stage); review = stage.submissions[-1].review if stage.submissions and stage.submissions[-1].review else None
            blockers = ([f"Stage {stage.number}: {stage.status}"] if gate.status not in {"passed", "approved"} else []) + (["رخداد بحرانی باز"] if any(i.severity == "critical" for i in _open_incidents(pilot)) else [])
            rows.append({"pilot_id": pilot.id, "pilot_code": pilot.code, "gate_code": code, "after_stage": gate.after_stage, "status": gate.status, "blocker_count": len(blockers), "blocker_labels": blockers, "reviewer": review.reviewer if review else None, "reviewed_at": review.reviewed_at if review else None})
    items, pagination = _paginate(rows, filters)
    return ReportResponse(generated_at=_now().replace(tzinfo=UTC), filters=_filters_dict(filters), summary=summary, items=items, pagination=pagination, state=_state(db, pilots))


def _priority(severity: str | None, due, now):
    if severity == "critical": return "critical"
    if due and due < now and (now - due).total_seconds() > 86400: return "high"
    if severity == "important" or (due and due <= now): return "high"
    if due and due.date() == now.date(): return "medium"
    return "low"


def _action_rows(pilots: list[Pilot], now: datetime) -> list[dict]:
    rows = []
    for pilot in pilots:
        stage = _current_stage(pilot); project = pilot.project.name if pilot.project else pilot.display_name
        assignee_id, assignee_name = _assignee(pilot)
        if stage and stage.status in {"open", "submitted", "needs_revision"}:
            title, reason = _next_action(pilot); due = _due_at(pilot)
            rows.append({"action_id": f"stage:{pilot.id}:{stage.number}", "pilot_id": pilot.id, "pilot_code": pilot.code, "project_name": project, "entity_type": "stage", "entity_id": stage.id, "stage_number": stage.number, "stage_title": stage.title, "title": title, "reason": stage.status, "assignee_id": assignee_id, "assignee_name": assignee_name, "due_at": due, "overdue_days": max(0, (now-due).days) if due and due < now else 0, "priority": _priority(None, due, now), "status": stage.status, "action_url": f"/pilots/{pilot.id}/stages/{stage.number}"})
        for incident in _open_incidents(pilot):
            rows.append({"action_id": f"incident:{incident.id}", "pilot_id": pilot.id, "pilot_code": pilot.code, "project_name": project, "entity_type": "incident", "entity_id": incident.id, "stage_number": incident.stage_number, "stage_title": None, "title": f"رسیدگی به رخداد {incident.code}", "reason": incident.incident_type, "assignee_id": incident.owner_user_id, "assignee_name": incident.owner.display_name if incident.owner else None, "due_at": incident.response_due_at, "overdue_days": max(0, (now-incident.response_due_at).days) if incident.response_due_at < now else 0, "priority": _priority(incident.severity, incident.response_due_at, now), "status": incident.status, "action_url": f"/pilots/{pilot.id}/incidents/{incident.id}"})
        for mission in pilot.missions:
            if mission.status not in {"completed", "cancelled"}:
                rows.append({"action_id": f"mission:{mission.id}", "pilot_id": pilot.id, "pilot_code": pilot.code, "project_name": project, "entity_type": "mission", "entity_id": mission.id, "stage_number": pilot.current_stage, "stage_title": stage.title if stage else None, "title": mission.display_name, "reason": mission.status, "assignee_id": mission.expert_user_id, "assignee_name": mission.expert.display_name if mission.expert else None, "due_at": mission.sla_due_at, "overdue_days": max(0, (now-mission.sla_due_at).days) if mission.sla_due_at < now else 0, "priority": _priority(None, mission.sla_due_at, now), "status": mission.status, "action_url": f"/missions/{mission.id}"})
        proposal = pilot.commercial_proposal
        if proposal and pilot.final_outcome is None:
            rows.append({"action_id": f"proposal:{proposal.id}", "pilot_id": pilot.id, "pilot_code": pilot.code, "project_name": project, "entity_type": "proposal", "entity_id": proposal.id, "stage_number": 17, "stage_title": "پیشنهاد تجاری", "title": "پیگیری پیشنهاد تجاری", "reason": "final_outcome_pending", "assignee_id": proposal.responsible_user_id, "assignee_name": proposal.responsible.display_name if proposal.responsible else None, "due_at": proposal.follow_up_at, "overdue_days": max(0, (now-proposal.follow_up_at).days) if proposal.follow_up_at < now else 0, "priority": _priority(None, proposal.follow_up_at, now), "status": "open", "action_url": f"/pilots/{pilot.id}/stages/17"})
    return rows


def report_actions(db: Session, context, filters: ReportFilters, *, due=None, priority=None, entity_type=None) -> ReportResponse:
    now = _now(); pilots = _filter_pilots(db, context, filters); rows = _action_rows(pilots, now)
    if due == "today": rows = [r for r in rows if r["due_at"] and r["due_at"].date() == now.date()]
    elif due == "overdue": rows = [r for r in rows if r["due_at"] and r["due_at"] < now]
    elif due == "upcoming": rows = [r for r in rows if r["due_at"] and r["due_at"] > now]
    elif due == "without_due_date": rows = [r for r in rows if r["due_at"] is None]
    if priority: rows = [r for r in rows if r["priority"] == priority]
    if entity_type: rows = [r for r in rows if r["entity_type"] == entity_type]
    rows.sort(key=lambda r: ({"critical": 0, "high": 1, "medium": 2, "low": 3}[r["priority"]], r["due_at"] or datetime.max))
    items, pagination = _paginate(rows, filters)
    return ReportResponse(generated_at=now.replace(tzinfo=UTC), filters=_filters_dict(filters) | {"due": due, "priority": priority, "entity_type": entity_type}, summary={"total": len(rows)}, items=items, pagination=pagination, state=_state(db, pilots))


def _sla_rows(pilots: list[Pilot], now: datetime):
    rows=[]
    for p in pilots:
        for m in p.missions:
            completed = m.form_f03.finished_at if m.form_f03 and m.form_f03.mission_completed else None
            rows.append({"entity_type":"mission","entity_id":m.id,"pilot_id":p.id,"stage_number":5,"assignee_id":m.expert_user_id,"sla_started_at":m.created_at,"sla_due_at":m.sla_due_at,"completed_at":completed})
        for i in p.incidents:
            rows.append({"entity_type":"incident","entity_id":i.id,"pilot_id":p.id,"stage_number":i.stage_number,"assignee_id":i.owner_user_id,"sla_started_at":i.reported_at,"sla_due_at":i.response_due_at,"completed_at":i.responded_at or i.closed_at})
    for r in rows:
        terminal = r["completed_at"] or now; duration=(r["sla_due_at"]-r["sla_started_at"]).total_seconds(); remaining=(r["sla_due_at"]-now).total_seconds()
        r["status"] = "overdue" if terminal > r["sla_due_at"] else "at_risk" if not r["completed_at"] and duration > 0 and remaining <= duration * .2 else "on_track"
        r["overdue_hours"] = round(max(0,(terminal-r["sla_due_at"]).total_seconds()/3600),2)
        r.update({"delay_reason":None,"corrective_action":None,"revised_due_at":None,"escalated_at":None})
    return rows


def report_sla(db: Session, context, filters: ReportFilters) -> ReportResponse:
    now=_now(); pilots=_filter_pilots(db,context,filters); rows=_sla_rows(pilots,now); delays=[r["overdue_hours"] for r in rows if r["overdue_hours"]]
    summary={"total_monitored":len(rows),"on_track":sum(r["status"]=="on_track" for r in rows),"at_risk":sum(r["status"]=="at_risk" for r in rows),"overdue":sum(r["status"]=="overdue" for r in rows),"not_applicable":0,"average_overdue_hours":round(mean(delays),2) if delays else 0,"maximum_overdue_hours":max(delays,default=0),"data_gaps":["revised_due_at","delay_reason","corrective_action","escalated_at"]}
    return ReportResponse(generated_at=now.replace(tzinfo=UTC),filters=_filters_dict(filters),summary=summary,items=rows,state="PARTIAL_DATA" if rows else _state(db,pilots))


def _metric(key,label,numerator,denominator,target,operator="\u003e="):
    if not denominator: return {"key":key,"label":label,"value":None,"unit":"percent","target":target,"target_operator":operator,"status":"insufficient_data","numerator":numerator,"denominator":denominator,"sample_size":denominator}
    value=max(0,min(100,round(numerator/denominator*100,2))); good=value>=target if operator=="\u003e=" else value<=target
    return {"key":key,"label":label,"value":value,"unit":"percent","target":target,"target_operator":operator,"status":"good" if good else "needs_attention","numerator":numerator,"denominator":denominator,"sample_size":denominator}


def report_kpis(db: Session, context, filters: ReportFilters) -> ReportResponse:
    pilots=_filter_pilots(db,context,filters); missions=[m for p in pilots for m in p.missions]; floors=[f for m in missions for f in m.floor_states]; forms=[p.form_f04 for p in pilots if p.form_f04]; notifications=[n for p in pilots for n in p.notifications]
    completed=sum(f.capture_state=="completed" for f in floors); uploads=sum(f.main_upload_completed for f in floors); recaptures=sum(f.capture_state=="needs_revision" for f in floors); linked=sum(f.correct_floor_link for f in floors)
    items=[_metric("floors_completed_on_plan_percent","طبقات طبق برنامه",completed,len(floors),95),_metric("successful_upload_percent","ثبت Upload موفق",uploads,len(floors),98),_metric("recapture_percent","برداشت مجدد",recaptures,len(floors),5,"\u003c="),_metric("correct_floor_assignment_percent","اتصال به Floor صحیح",linked,len(floors),99),_metric("successful_notification_percent","اعلان موفق",sum(n.status=="delivered" for n in notifications),len(notifications),95),_metric("successful_training_percent","آموزش موفق",sum(f.training_completed for f in forms),len(forms),90),_metric("continuation_interest_percent","تمایل ادامه",sum(f.continuation_interest is True for f in forms),sum(f.continuation_interest is not None for f in forms),70),_metric("proposal_ready_percent","آمادگی پیشنهاد",sum(f.proposal_ready is True for f in forms),sum(f.proposal_ready is not None for f in forms),60)]
    scores=[f.satisfaction_score for f in forms if f.satisfaction_score is not None]; items.append({"key":"average_satisfaction_score","label":"میانگین رضایت","value":round(mean(scores),2) if scores else None,"unit":"score","target":8,"target_operator":"\u003e=","status":"good" if scores and mean(scores)>=8 else "needs_attention" if scores else "insufficient_data","numerator":sum(scores),"denominator":len(scores),"sample_size":len(scores)})
    summary={"planned_floors":len(floors),"completed_floors":completed,"completed_missions":sum(m.status=="completed" for m in missions),"incomplete_floors":sum(f.capture_state in {"incomplete","not_done"} for f in floors),"proposals_sent":sum(p.commercial_proposal is not None for p in pilots),"contracts":sum(bool(p.final_outcome and p.final_outcome.outcome=="contract") for p in pilots)}
    return ReportResponse(generated_at=_now().replace(tzinfo=UTC),filters=_filters_dict(filters),summary=summary,items=items,state=_state(db,pilots))


def report_incidents(db: Session, context, filters: ReportFilters) -> ReportResponse:
    now=_now(); pilots=_filter_pilots(db,context,filters); incidents=[(p,i) for p in pilots for i in p.incidents]; open_rows=[i for _,i in incidents if i.status!="closed"]; closed=[i for _,i in incidents if i.closed_at]
    durations=[(i.closed_at-i.reported_at).total_seconds()/3600 for i in closed]
    summary={"total_open":len(open_rows),"critical_open":sum(i.severity=="critical" for i in open_rows),"important_open":sum(i.severity=="important" for i in open_rows),"normal_open":sum(i.severity=="normal" for i in open_rows),"overdue":sum(i.response_due_at<now and i.responded_at is None for i in open_rows),"closed_in_period":len(closed),"average_resolution_hours":round(mean(durations),2) if durations else None,"breakdown":dict(Counter(i.incident_type for _,i in incidents))}
    rows=[{"incident_code":i.code,"pilot_code":p.code,"project_name":p.project.name if p.project else p.display_name,"severity":i.severity,"type":i.incident_type,"stage_number":i.stage_number,"description_short":i.description[:160],"owner":i.owner.display_name if i.owner else None,"due_at":i.response_due_at,"overdue_days":max(0,(now-i.response_due_at).days) if i.response_due_at<now else 0,"status":i.status,"containment_status":"completed" if i.containment_action else "pending","corrective_action_status":"completed" if i.corrective_action else "pending","closed_at":i.closed_at} for p,i in incidents]
    items,pagination=_paginate(rows,filters); return ReportResponse(generated_at=now.replace(tzinfo=UTC),filters=_filters_dict(filters),summary=summary,items=items,pagination=pagination,state=_state(db,pilots))


def _visible_pilot(db, context, pilot_id):
    pilot=next((p for p in visible_pilots(db,context) if p.id==pilot_id),None)
    if not pilot: raise SecurityError("REPORT_PILOT_NOT_FOUND","گزارش پرونده پیدا نشد.",404,[])
    return pilot


def report_one_page(db: Session, context, pilot_id: int) -> ReportResponse:
    now=_now(); p=_visible_pilot(db,context,pilot_id); row=_pilot_row(p,now); floors=[f for m in p.missions for f in m.floor_states]; form=p.form_f04; outcome=p.final_outcome
    decision={"contract":"transfer_to_active_customer","rejected":"close","closed":"close","negotiation":"continue_pilot","ready_on_date":"send_proposal"}.get(outcome.outcome) if outcome else None
    issues=sorted(_open_incidents(p),key=lambda i:({"critical":0,"important":1,"normal":2}[i.severity],i.response_due_at))[:3]
    status="contracted" if outcome and outcome.outcome=="contract" else "closed_without_contract" if outcome and outcome.outcome in {"closed","rejected"} else "paused" if p.status=="stopped" else "needs_more_pilot_cycles" if p.current_stage<17 else "successful_ready_for_proposal"
    report={"header":{"pilot_code":p.code,"project_name":p.project.name if p.project else p.display_name,"owner_name":p.project.owner.name if p.project and p.project.owner else None,"pilot_manager":row["pilot_manager"],"generated_at":now.replace(tzinfo=UTC)},"overall_result":{"status":status,"label":status,"short_summary":p.evaluation.one_page_summary[:500] if p.evaluation else None},"process":{"approved_stages":row["approved_stages_count"],"total_stages":TOTAL_STAGES,"current_stage":p.current_stage,"current_gate":row["current_gate"],"overdue_days":row["overdue_days"],"next_action":row["next_action"],"next_action_owner":row["current_assignee"],"next_action_due_at":row["due_at"]},"operations":{"planned_floors":len(floors),"completed_floors":sum(f.capture_state=="completed" for f in floors),"upload_success":sum(f.main_upload_completed for f in floors),"recapture_count":sum(f.capture_state=="needs_revision" for f in floors),"important_errors":sum(i.severity in {"important","critical"} for i in _open_incidents(p))},"customer_experience":{"viewed_output":form.main_tour_viewed if form else None,"training_status":form.training_completed if form else None,"satisfaction_score":form.satisfaction_score if form else None,"most_useful_part":form.most_useful_part if form else None,"main_problem":form.issue_description if form else None,"continuation_interest":form.continuation_interest if form else None},"commercial":{"created_value":form.realized_value if form else None,"customer_need":form.customer_need_summary if form else None,"decision_maker":form.decision_maker if form else None,"purchase_barrier":form.purchase_blocker if form else None,"possible_projects_count":form.project_count if form else None,"requested_frequency":form.usage_frequency if form else None,"proposal_readiness":form.proposal_ready if form else None,"proposal_status":"sent" if p.commercial_proposal else None,"final_outcome":outcome.outcome if outcome else None},"open_issues":[{"code":i.code,"severity":i.severity,"label":i.description[:160],"due_at":i.response_due_at} for i in issues],"recommended_decision":decision,"decision_status":"recorded" if decision else "requires_manager_decision","next_action":{"action":row["next_action"],"responsible":row["current_assignee"],"due_at":row["due_at"]}}
    return ReportResponse(generated_at=now.replace(tzinfo=UTC),filters={"pilot_id":pilot_id},summary=report,state="SUCCESS")


def report_external_evidence(db: Session, context, pilot_id: int) -> ReportResponse:
    p=_visible_pilot(db,context,pilot_id); items=[{"evidence_key":e.capability,"evidence_label":EVIDENCE_LABELS.get(e.capability,e.capability),"checked":e.status=="checked","checked_by":e.checked_by.display_name if e.checked_by else None,"checked_at":e.checked_at,"short_result":e.result[:500] if e.result else None,"related_incident_id":None} for e in p.external_evidence_checks]
    return ReportResponse(generated_at=_now().replace(tzinfo=UTC),filters={"pilot_id":pilot_id},summary={"total":len(items)},items=items,state="SUCCESS" if items else "NO_DATA")
