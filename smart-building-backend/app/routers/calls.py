"""Authenticated call APIs and isolated provider webhook."""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.calls import CallCreate, CallOutcomeUpdate, CallOverride, CallRead, MockWebhookPayload, RecordingReferenceRead
from app.services.calls import (
    get_call, initiate_call, list_stage_calls, override_call_requirement,
    process_mock_webhook, record_outcome, retry_call,
)
from app.services.security import AuthContext, require_permission

router = APIRouter(prefix="/api/v1", tags=["calls"])


@router.post("/pilots/{pilot_id}/stages/{stage_number}/calls", response_model=CallRead, status_code=201)
def create_call(pilot_id: int, stage_number: int, payload: CallCreate,
                context: AuthContext = Depends(require_permission("calls.initiate")),
                db: Session = Depends(get_db)):
    return initiate_call(db, context, pilot_id, stage_number, payload)


@router.get("/pilots/{pilot_id}/stages/{stage_number}/calls", response_model=list[CallRead])
def stage_calls(pilot_id: int, stage_number: int,
                context: AuthContext = Depends(require_permission("calls.read")),
                db: Session = Depends(get_db)):
    return list_stage_calls(db, context, pilot_id, stage_number)


@router.get("/calls/{call_id}", response_model=CallRead)
def call_detail(call_id: str, context: AuthContext = Depends(require_permission("calls.read")),
                db: Session = Depends(get_db)):
    return get_call(db, context, call_id)


@router.patch("/calls/{call_id}/outcome", response_model=CallRead)
def update_call_outcome(call_id: str, payload: CallOutcomeUpdate,
                        context: AuthContext = Depends(require_permission("calls.record_outcome")),
                        db: Session = Depends(get_db)):
    return record_outcome(db, context, call_id, payload)


@router.post("/calls/{call_id}/retry", response_model=CallRead)
def retry(call_id: str, context: AuthContext = Depends(require_permission("calls.retry")),
          db: Session = Depends(get_db)):
    return retry_call(db, context, call_id)


@router.post("/calls/{call_id}/override", response_model=CallRead)
def override(call_id: str, payload: CallOverride,
             context: AuthContext = Depends(require_permission("calls.override")),
             db: Session = Depends(get_db)):
    return override_call_requirement(db, context, call_id, payload)


@router.get("/calls/{call_id}/recording-reference", response_model=RecordingReferenceRead)
def recording_reference(call_id: str,
                        context: AuthContext = Depends(require_permission("calls.recording.read")),
                        db: Session = Depends(get_db)):
    call = get_call(db, context, call_id)
    if not call.recording_reference:
        from app.exceptions import SecurityError
        raise SecurityError("CALL_RECORDING_NOT_FOUND", "مرجع ضبط تماس موجود نیست.", 404, [])
    return RecordingReferenceRead(reference=call.recording_reference)


@router.post("/integrations/astel/webhooks")
async def astel_webhook(request: Request, payload: MockWebhookPayload,
                        x_call_signature: str | None = Header(default=None),
                        db: Session = Depends(get_db)):
    raw_body = await request.body()
    call, duplicate = process_mock_webhook(db, raw_body, x_call_signature, payload)
    return {"accepted": True, "duplicate": duplicate, "call_id": call.public_id}
