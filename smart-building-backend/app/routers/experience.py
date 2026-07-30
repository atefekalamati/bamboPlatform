"""External platform, F04, evidence, notification, and F05 incident APIs."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.models import (
    ExternalEvidenceCheck,
    ExternalPlatformReference,
    FormF04,
    Incident,
    Notification,
)
from app.schemas.experience import (
    ExternalEvidenceRead,
    ExternalEvidenceUpdate,
    ExternalPlatformRead,
    ExternalPlatformUpdate,
    FormF04Patch,
    FormF04Read,
    IncidentClose,
    IncidentCreate,
    IncidentPatch,
    IncidentRead,
    OutputNotificationCreate,
)
from app.schemas.operations import NotificationRead
from app.services.experience import (
    close_incident,
    create_incident,
    create_main_output_notification,
    get_incident,
    get_pilot,
    patch_f04,
    patch_incident,
    update_external_platform_reference,
    upsert_external_evidence,
)
from app.services.security import AuthContext, require_permission

router = APIRouter(tags=["customer-experience"])


@router.get(
    "/pilots/{pilot_id}/external-platform",
    response_model=ExternalPlatformRead,
)
def get_external_platform(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> ExternalPlatformReference:
    reference = get_pilot(db, pilot_id).external_platform_reference
    if reference is None:
        raise SecurityError(
            "EXTERNAL_STATUS_NOT_FOUND",
            "وضعیت پلتفرم اصلی هنوز ثبت نشده است.",
            404,
            [],
        )
    return reference


@router.put(
    "/pilots/{pilot_id}/external-platform",
    response_model=ExternalPlatformRead,
)
def put_external_platform(
    pilot_id: int,
    payload: ExternalPlatformUpdate,
    context: AuthContext = Depends(require_permission("external_status.manage")),
    db: Session = Depends(get_db),
) -> ExternalPlatformReference:
    return update_external_platform_reference(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get("/pilots/{pilot_id}/forms/f04", response_model=FormF04Read)
def get_f04(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> FormF04:
    form = get_pilot(db, pilot_id).form_f04
    if form is None:
        raise SecurityError("F04_NOT_FOUND", "فرم F04 هنوز ثبت نشده است.", 404, [])
    return form


@router.patch("/pilots/{pilot_id}/forms/f04", response_model=FormF04Read)
def patch_f04_endpoint(
    pilot_id: int,
    payload: FormF04Patch,
    context: AuthContext = Depends(require_permission("customer_success.manage")),
    db: Session = Depends(get_db),
) -> FormF04:
    return patch_f04(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get(
    "/pilots/{pilot_id}/external-evidence",
    response_model=list[ExternalEvidenceRead],
)
def list_external_evidence(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[ExternalEvidenceCheck]:
    return get_pilot(db, pilot_id).external_evidence_checks


@router.put(
    "/pilots/{pilot_id}/external-evidence/{capability}",
    response_model=ExternalEvidenceRead,
)
def put_external_evidence(
    pilot_id: int,
    capability: str,
    payload: ExternalEvidenceUpdate,
    context: AuthContext = Depends(require_permission("customer_success.manage")),
    db: Session = Depends(get_db),
) -> ExternalEvidenceCheck:
    return upsert_external_evidence(
        db,
        pilot_id,
        capability,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.post(
    "/pilots/{pilot_id}/notifications/main-output",
    response_model=NotificationRead,
    status_code=status.HTTP_201_CREATED,
)
def post_main_output_notification(
    pilot_id: int,
    payload: OutputNotificationCreate,
    context: AuthContext = Depends(require_permission("notifications.manage")),
    db: Session = Depends(get_db),
) -> Notification:
    return create_main_output_notification(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get("/pilots/{pilot_id}/incidents", response_model=list[IncidentRead])
def list_incidents(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[Incident]:
    return get_pilot(db, pilot_id).incidents


@router.post(
    "/pilots/{pilot_id}/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def post_incident(
    pilot_id: int,
    payload: IncidentCreate,
    context: AuthContext = Depends(require_permission("incidents.manage")),
    db: Session = Depends(get_db),
) -> Incident:
    return create_incident(
        db,
        pilot_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident_endpoint(
    incident_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> Incident:
    return get_incident(db, incident_id)


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
def patch_incident_endpoint(
    incident_id: int,
    payload: IncidentPatch,
    context: AuthContext = Depends(require_permission("incidents.manage")),
    db: Session = Depends(get_db),
) -> Incident:
    return patch_incident(
        db,
        incident_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )


@router.post("/incidents/{incident_id}/close", response_model=IncidentRead)
def close_incident_endpoint(
    incident_id: int,
    payload: IncidentClose,
    context: AuthContext = Depends(require_permission("incidents.manage")),
    db: Session = Depends(get_db),
) -> Incident:
    return close_incident(
        db,
        incident_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
    )
