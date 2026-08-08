"""External platform, F04, evidence, notification, and F05 incident APIs."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from fastapi import Query
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
    IncidentList,
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
    list_incidents as list_incidents_service,
    patch_f04,
    patch_incident,
    update_external_platform_reference,
    upsert_external_evidence,
)
from app.services.security import AuthContext, effective_permissions, require_permission
from app.services.access import enforce_path_pilot_access

router = APIRouter(tags=["customer-experience"], dependencies=[Depends(enforce_path_pilot_access)])


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


@router.get("/pilots/{pilot_id}/incidents", response_model=IncidentList)
def list_incidents(
    pilot_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    search: str | None = Query(default=None, min_length=1, max_length=160),
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    incident_type: str | None = Query(default=None),
    stage_number: int | None = Query(default=None, ge=1, le=19),
    mission_id: int | None = Query(default=None, ge=1),
    owner_user_id: int | None = Query(default=None, ge=1),
    reported_by_user_id: int | None = Query(default=None, ge=1),
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    response_overdue: bool | None = Query(default=None),
    correction_overdue: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at", max_length=80),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _: AuthContext = Depends(require_permission("incidents.read")),
    db: Session = Depends(get_db),
) -> IncidentList:
    return list_incidents_service(
        db,
        pilot_id,
        page=page,
        page_size=page_size,
        search=search,
        status=status_filter,
        severity=severity,
        incident_type=incident_type,
        stage_number=stage_number,
        mission_id=mission_id,
        owner_user_id=owner_user_id,
        reported_by_user_id=reported_by_user_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        response_overdue=response_overdue,
        correction_overdue=correction_overdue,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "/pilots/{pilot_id}/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def post_incident(
    pilot_id: int,
    payload: IncidentCreate,
    context: AuthContext = Depends(require_permission("incidents.create")),
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
    _: AuthContext = Depends(require_permission("incidents.read")),
    db: Session = Depends(get_db),
) -> Incident:
    return get_incident(db, incident_id)


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
def patch_incident_endpoint(
    incident_id: int,
    payload: IncidentPatch,
    context: AuthContext = Depends(require_permission("incidents.update")),
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
    context: AuthContext = Depends(require_permission("incidents.close")),
    db: Session = Depends(get_db),
) -> Incident:
    return close_incident(
        db,
        incident_id,
        payload,
        actor_user_id=context.user.id,
        session_id=context.session.id,
        actor_permissions=effective_permissions(context.user),
    )
