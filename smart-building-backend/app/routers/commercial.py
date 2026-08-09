"""Commercial APIs for workflow stages 17 through 19."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.models import CommercialProposal, CustomerFollowUp, FinalOutcome
from app.schemas.commercial import (
    CommercialProposalRead,
    CommercialProposalUpdate,
    CustomerFollowUpRead,
    CustomerFollowUpUpdate,
    FinalOutcomeApprove,
    FinalOutcomeRead,
    FinalOutcomeUpdate,
    FollowUpSlot,
)
from app.services.commercial import (
    FOLLOW_UP_SLOT_ORDER,
    approve_final_outcome,
    get_pilot,
    update_commercial_proposal,
    update_customer_follow_up,
    update_final_outcome,
)
from app.services.security import AuthContext, require_permission
from app.services.access import enforce_path_pilot_access

router = APIRouter(tags=["commercial"], dependencies=[Depends(enforce_path_pilot_access)])


@router.get(
    "/pilots/{pilot_id}/commercial-proposal",
    response_model=CommercialProposalRead,
)
def get_commercial_proposal(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> CommercialProposal:
    proposal = get_pilot(db, pilot_id).commercial_proposal
    if proposal is None:
        raise SecurityError(
            "COMMERCIAL_PROPOSAL_NOT_FOUND",
            "پیشنهاد تجاری هنوز ثبت نشده است.",
            404,
            [],
        )
    return proposal


@router.put(
    "/pilots/{pilot_id}/commercial-proposal",
    response_model=CommercialProposalRead,
)
def put_commercial_proposal(
    pilot_id: int,
    payload: CommercialProposalUpdate,
    context: AuthContext = Depends(require_permission("commercial.manage")),
    db: Session = Depends(get_db),
) -> CommercialProposal:
    return update_commercial_proposal(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get(
    "/pilots/{pilot_id}/commercial-follow-ups",
    response_model=list[CustomerFollowUpRead],
)
def list_commercial_follow_ups(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[CustomerFollowUp]:
    follow_ups = get_pilot(db, pilot_id).customer_follow_ups
    slot_position = {
        slot: position for position, slot in enumerate(FOLLOW_UP_SLOT_ORDER)
    }
    return sorted(
        follow_ups,
        key=lambda item: slot_position[item.schedule_slot],
    )


@router.put(
    "/pilots/{pilot_id}/commercial-follow-ups/{schedule_slot}",
    response_model=CustomerFollowUpRead,
)
def put_commercial_follow_up(
    pilot_id: int,
    schedule_slot: FollowUpSlot,
    payload: CustomerFollowUpUpdate,
    context: AuthContext = Depends(require_permission("commercial.manage")),
    db: Session = Depends(get_db),
) -> CustomerFollowUp:
    return update_customer_follow_up(
        db,
        pilot_id,
        schedule_slot,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get(
    "/pilots/{pilot_id}/final-outcome",
    response_model=FinalOutcomeRead,
)
def get_final_outcome(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> FinalOutcome:
    outcome = get_pilot(db, pilot_id).final_outcome
    if outcome is None:
        raise SecurityError(
            "FINAL_OUTCOME_NOT_FOUND",
            "نتیجه نهایی هنوز ثبت نشده است.",
            404,
            [],
        )
    return outcome


@router.put(
    "/pilots/{pilot_id}/final-outcome",
    response_model=FinalOutcomeRead,
)
def put_final_outcome(
    pilot_id: int,
    payload: FinalOutcomeUpdate,
    context: AuthContext = Depends(require_permission("commercial.manage")),
    db: Session = Depends(get_db),
) -> FinalOutcome:
    return update_final_outcome(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.post(
    "/pilots/{pilot_id}/final-outcome/approve",
    response_model=FinalOutcomeRead,
)
def post_final_outcome_approval(
    pilot_id: int,
    _: FinalOutcomeApprove,
    context: AuthContext = Depends(
        require_permission("gate_approval.approve"),
    ),
    db: Session = Depends(get_db),
) -> FinalOutcome:
    return approve_final_outcome(
        db,
        pilot_id,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )
