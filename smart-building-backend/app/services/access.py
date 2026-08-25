"""Central pilot scope and IDOR protection shared by business routers."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.policies import active_role_names
from app.auth.role_matrix import ROLE_DEFINITIONS, STAGE_MATRIX
from app.database import get_db
from app.exceptions import SecurityError
from app.models import (
    CommercialProposal,
    CustomerFollowUp,
    FinalOutcome,
    FormF01,
    FormF02,
    FormF04,
    Incident,
    Mission,
    Pilot,
    PilotEvaluation,
)
from app.services.security import AuthContext, effective_permissions, get_auth_context


def scoped_pilot_query(db: Session, context: AuthContext):
    query = db.query(Pilot)
    roles = active_role_names(context.user)
    permissions = effective_permissions(context.user)
    scopes = {
        ROLE_DEFINITIONS[name].data_scope
        for name in roles
        if name in ROLE_DEFINITIONS
    }
    if "ALL" in scopes or "pilots.read_all" in permissions:
        return query

    user_id = context.user.id
    actionable_stages = {
        stage_number
        for stage_number, rules in STAGE_MATRIX.items()
        if any(roles.intersection(allowed) for allowed in rules.values())
    }
    assigned = or_(
        Pilot.created_by_user_id == user_id,
        Pilot.form_f01.has(
            or_(
                FormF01.case_owner_user_id == user_id,
                FormF01.sales_user_id == user_id,
                FormF01.pilot_manager_user_id == user_id,
            )
        ),
        Pilot.form_f02.has(
            or_(
                FormF02.responsible_user_id == user_id,
                FormF02.configured_by_user_id == user_id,
                FormF02.controlled_by_user_id == user_id,
            )
        ),
        Pilot.missions.any(
            or_(Mission.expert_user_id == user_id, Mission.created_by_user_id == user_id)
        ),
        Pilot.incidents.any(Incident.owner_user_id == user_id),
        Pilot.form_f04.has(
            or_(
                FormF04.responsible_user_id == user_id,
                FormF04.issue_owner_user_id == user_id,
                FormF04.customer_success_user_id == user_id,
                FormF04.sales_user_id == user_id,
                FormF04.pilot_manager_user_id == user_id,
            )
        ),
        Pilot.evaluation.has(PilotEvaluation.responsible_user_id == user_id),
        Pilot.commercial_proposal.has(CommercialProposal.responsible_user_id == user_id),
        Pilot.customer_follow_ups.any(CustomerFollowUp.owner_user_id == user_id),
        Pilot.final_outcome.has(
            or_(
                FinalOutcome.responsible_user_id == user_id,
                FinalOutcome.success_owner_user_id == user_id,
                FinalOutcome.approved_by_user_id == user_id,
            )
        ),
    )
    if "ROLE_RELATED" in scopes or "PILOT_MEMBER" in scopes:
        return query.filter(or_(assigned, Pilot.current_stage.in_(actionable_stages or {-1})))
    return query.filter(assigned)


def scoped_incident_pilot_query(db: Session, context: AuthContext):
    """Return the pilot scope used by the global incident list.

    The field expert and pilot manager rules are intentionally narrower than
    the generic role-related workflow scope: listing incidents must not reveal
    pilots merely because their current stage is actionable by that role.
    """
    query = db.query(Pilot)
    roles = active_role_names(context.user)
    permissions = effective_permissions(context.user)
    scopes = {
        ROLE_DEFINITIONS[name].data_scope
        for name in roles
        if name in ROLE_DEFINITIONS
    }
    if "ALL" in scopes or "incidents.read_all" in permissions:
        return query

    user_id = context.user.id
    role_filters = []
    if "capture_expert" in roles:
        role_filters.extend(
            (
                Pilot.missions.any(Mission.expert_user_id == user_id),
                Pilot.incidents.any(Incident.owner_user_id == user_id),
            )
        )
    if "pilot_manager" in roles:
        role_filters.extend(
            (
                Pilot.form_f01.has(FormF01.pilot_manager_user_id == user_id),
                Pilot.form_f04.has(FormF04.pilot_manager_user_id == user_id),
            )
        )
    if roles and roles.issubset({"capture_expert", "pilot_manager"}):
        return query.filter(or_(*role_filters)) if role_filters else query.filter(Pilot.id == -1)

    return scoped_pilot_query(db, context)


def require_pilot_access(db: Session, context: AuthContext, pilot_id: int) -> Pilot:
    pilot = scoped_pilot_query(db, context).filter(Pilot.id == pilot_id).first()
    if pilot is None:
        raise SecurityError(
            code="PILOT_NOT_FOUND",
            message="پرونده پایلوت پیدا نشد یا دسترسی به آن مجاز نیست.",
            status_code=404,
            errors=[],
        )
    return pilot


def enforce_path_pilot_access(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> None:
    raw_pilot_id = request.path_params.get("pilot_id")
    if raw_pilot_id is not None:
        require_pilot_access(db, context, int(raw_pilot_id))
