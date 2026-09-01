"""F01/F02, Floor, and secure DWG APIs."""

import json

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.models import (
    Contact,
    DwgFile,
    DwgVersion,
    Floor,
    FormF01,
    FormF02,
    Pilot,
    User,
)
from app.schemas.product import (
    DwgVersionRead,
    FloorBulkCreate,
    FloorBulkCreateResult,
    FloorCreate,
    FloorDwgReferenceBulkItem,
    FloorDwgReferenceBulkResult,
    FloorDwgReferenceBulkUpdate,
    FloorDwgReferenceUpdate,
    FloorRead,
    SharedDwgFileSummary,
    SharedDwgUploadResult,
    SharedDwgVersionItem,
    FormF01Read,
    FormF01Update,
    FormF02Read,
    FormF02Update,
)
from app.models.product import utc_now as product_utc_now
from app.services.security import AuthContext, add_audit_log, require_permission
from app.services.access import enforce_path_pilot_access
from app.services.workflow import invalidate_from_stage
from app.storage.dwg import (
    delete_storage_key,
    discard_staged_upload,
    finalize_shared_upload,
    finalize_upload,
    resolve_storage_key,
    stage_upload,
)

router = APIRouter(tags=["project-data"], dependencies=[Depends(enforce_path_pilot_access)])

F01_STAGE_1_FIELDS = {
    "project_active",
    "imaging_value",
    "remote_viewing_need",
    "access_possible",
    "dwg_available",
    "continued_capacity",
    "not_demo_only",
    "result",
}


def get_pilot(db: Session, pilot_id: int) -> Pilot:
    pilot = db.get(Pilot, pilot_id)
    if not pilot:
        raise SecurityError("PILOT_NOT_FOUND", "پرونده پایلوت پیدا نشد.", 404, [])
    return pilot


def validate_user_references(db: Session, user_ids: list[int | None]) -> None:
    ids = {user_id for user_id in user_ids if user_id is not None}
    if not ids:
        return
    existing = {user.id for user in db.query(User).filter(User.id.in_(ids)).all()}
    if existing != ids:
        raise SecurityError("USER_NOT_FOUND", "یک یا چند کاربر مرجع پیدا نشد.", 422, [])


@router.get("/pilots/{pilot_id}/forms/f01", response_model=FormF01Read)
def get_f01(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> FormF01:
    pilot = get_pilot(db, pilot_id)
    if not pilot.form_f01:
        raise SecurityError("F01_NOT_FOUND", "فرم F01 هنوز ثبت نشده است.", 404, [])
    return pilot.form_f01


@router.put("/pilots/{pilot_id}/forms/f01", response_model=FormF01Read)
def upsert_f01(
    pilot_id: int,
    payload: FormF01Update,
    context: AuthContext = Depends(require_permission("forms.manage")),
    db: Session = Depends(get_db),
) -> FormF01:
    pilot = get_pilot(db, pilot_id)
    validate_user_references(
        db,
        [payload.sales_user_id, payload.pilot_manager_user_id],
    )
    form = pilot.form_f01
    was_existing = form is not None
    values = payload.model_dump()
    changed_fields = (
        set(values)
        if form is None
        else {
            field for field, value in values.items() if getattr(form, field) != value
        }
    )
    if form is None:
        form = FormF01(pilot=pilot, case_owner_user_id=context.user.id, **values)
        db.add(form)
    else:
        for field, value in values.items():
            setattr(form, field, value)

    coordinator = next(
        (contact for contact in pilot.project.owner.contacts if contact.is_site_coordinator),
        None,
    )
    if payload.coordinator_name and payload.coordinator_mobile:
        if coordinator is None:
            coordinator = Contact(
                owner=pilot.project.owner,
                name=payload.coordinator_name,
                mobile=payload.coordinator_mobile,
                is_site_coordinator=True,
            )
            db.add(coordinator)
        else:
            coordinator.name = payload.coordinator_name
            coordinator.mobile = payload.coordinator_mobile

    if was_existing and changed_fields:
        invalidation_stage = 1 if changed_fields & F01_STAGE_1_FIELDS else 2
        invalidate_from_stage(
            db,
            pilot,
            invalidation_stage,
            actor_user_id=context.user.id,
            reason="F01 updated",
        )
    add_audit_log(
        db,
        action="forms.f01_saved",
        entity_type="Pilot",
        entity_id=pilot.id,
        actor_user_id=context.user.id,
        new_data={
            "result": payload.result,
            "changed_fields": sorted(changed_fields),
        },
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(form)
    return form


@router.get("/pilots/{pilot_id}/forms/f02", response_model=FormF02Read)
def get_f02(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> FormF02:
    pilot = get_pilot(db, pilot_id)
    if not pilot.form_f02:
        raise SecurityError("F02_NOT_FOUND", "فرم F02 هنوز ثبت نشده است.", 404, [])
    return pilot.form_f02


@router.put("/pilots/{pilot_id}/forms/f02", response_model=FormF02Read)
def upsert_f02(
    pilot_id: int,
    payload: FormF02Update,
    context: AuthContext = Depends(require_permission("forms.manage")),
    db: Session = Depends(get_db),
) -> FormF02:
    pilot = get_pilot(db, pilot_id)
    validate_user_references(
        db,
        [
            payload.configured_by_user_id,
            payload.controlled_by_user_id,
        ],
    )
    form = pilot.form_f02
    was_existing = form is not None
    values = payload.model_dump()
    changed = form is None or any(
        getattr(form, field) != value for field, value in values.items()
    )
    if form is None:
        form = FormF02(
            pilot=pilot,
            responsible_user_id=context.user.id,
            **values,
        )
        db.add(form)
    else:
        for field, value in values.items():
            setattr(form, field, value)
    if was_existing and changed:
        invalidate_from_stage(
            db,
            pilot,
            4,
            actor_user_id=context.user.id,
            reason="F02 updated",
        )
    add_audit_log(
        db,
        action="forms.f02_saved",
        entity_type="Pilot",
        entity_id=pilot.id,
        actor_user_id=context.user.id,
        new_data={"ready_for_capture": payload.ready_for_capture},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(form)
    return form


def floor_read(floor: Floor) -> FloorRead:
    versions = floor.dwg_file.versions if floor.dwg_file else []
    has_readable_dwg = bool(versions and versions[-1].is_readable)
    return FloorRead(
        id=floor.id,
        project_id=floor.project_id,
        code=floor.code,
        name=floor.name,
        level_order=floor.level_order,
        floor_type=floor.floor_type,
        has_dwg=bool(versions),
        has_valid_dwg=has_readable_dwg or floor.dwg_reference_confirmed,
        latest_dwg_version=versions[-1].version if versions else None,
        dwg_reference_confirmed=floor.dwg_reference_confirmed,
        dwg_reference_confirmed_at=floor.dwg_reference_confirmed_at,
        dwg_reference_confirmed_by_user_id=(
            floor.dwg_reference_confirmed_by_user_id
        ),
    )


@router.post(
    "/pilots/{pilot_id}/floors",
    response_model=FloorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_floor(
    pilot_id: int,
    payload: FloorCreate,
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> FloorRead:
    pilot = get_pilot(db, pilot_id)
    if len(pilot.project.floors) >= pilot.project.total_floors:
        raise SecurityError(
            "FLOOR_LIMIT_REACHED",
            "تعداد Floor از مقدار ثبت‌شده پروژه بیشتر می‌شود.",
            409,
            [],
        )
    floor = Floor(project=pilot.project, **payload.model_dump())
    db.add(floor)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecurityError(
            "FLOOR_ALREADY_EXISTS",
            "کد یا ترتیب Floor تکراری است.",
            409,
            [],
        ) from exc
    invalidate_from_stage(
        db,
        pilot,
        3,
        actor_user_id=context.user.id,
        reason="Floor added",
    )
    add_audit_log(
        db,
        action="floors.created",
        entity_type="Floor",
        entity_id=floor.id,
        actor_user_id=context.user.id,
        new_data={"code": floor.code, "level_order": floor.level_order},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(floor)
    return floor_read(floor)


@router.get("/pilots/{pilot_id}/floors", response_model=list[FloorRead])
def list_floors(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[FloorRead]:
    pilot = get_pilot(db, pilot_id)
    return [floor_read(floor) for floor in pilot.project.floors]


@router.put("/floors/{floor_id}/dwg-reference", response_model=FloorRead)
def update_floor_dwg_reference(
    floor_id: int,
    payload: FloorDwgReferenceUpdate,
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> FloorRead:
    floor = db.get(Floor, floor_id)
    if not floor:
        raise SecurityError("FLOOR_NOT_FOUND", "طبقه پیدا نشد.", 404, [])

    previous = floor.dwg_reference_confirmed
    floor.dwg_reference_confirmed = payload.confirmed
    floor.dwg_reference_confirmed_at = (
        product_utc_now() if payload.confirmed else None
    )
    floor.dwg_reference_confirmed_by_user_id = (
        context.user.id if payload.confirmed else None
    )
    invalidate_from_stage(
        db,
        floor.project.pilot,
        3,
        actor_user_id=context.user.id,
        reason=f"DWG reference confirmation changed for {floor.code}",
    )
    add_audit_log(
        db,
        action="floors.dwg_reference_updated",
        entity_type="Floor",
        entity_id=floor.id,
        actor_user_id=context.user.id,
        old_data={"confirmed": previous},
        new_data={"confirmed": payload.confirmed},
        session_id=context.session.id,
    )
    db.commit()
    db.refresh(floor)
    return floor_read(floor)


@router.delete("/floors/{floor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_floor(
    floor_id: int,
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> None:
    floor = db.get(Floor, floor_id)
    if not floor:
        raise SecurityError("FLOOR_NOT_FOUND", "طبقه پیدا نشد.", 404, [])
    if floor.mission_states:
        raise SecurityError(
            "FLOOR_HAS_MISSIONS",
            "این طبقه در یک یا چند مأموریت استفاده شده و قابل حذف نیست.",
            409,
            [{"mission_id": item.mission_id} for item in floor.mission_states],
        )

    pilot = floor.project.pilot
    storage_keys = [
        version.storage_key
        for version in (floor.dwg_file.versions if floor.dwg_file else [])
    ]
    floor_data = {
        "code": floor.code,
        "name": floor.name,
        "level_order": floor.level_order,
        "dwg_versions": len(storage_keys),
    }
    invalidate_from_stage(
        db,
        pilot,
        3,
        actor_user_id=context.user.id,
        reason=f"Floor {floor.code} deleted",
    )
    add_audit_log(
        db,
        action="floors.deleted",
        entity_type="Floor",
        entity_id=floor.id,
        actor_user_id=context.user.id,
        old_data=floor_data,
        session_id=context.session.id,
    )
    db.delete(floor)
    db.commit()
    # A shared upload gives several floors one stored file, so a key may still
    # belong to a surviving floor. Only unlink what nothing references any more.
    for storage_key in storage_keys:
        still_referenced = (
            db.query(DwgVersion.id)
            .filter(DwgVersion.storage_key == storage_key)
            .first()
            is not None
        )
        if not still_referenced:
            delete_storage_key(storage_key)


@router.post(
    "/floors/{floor_id}/dwg",
    response_model=DwgVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dwg(
    floor_id: int,
    file: UploadFile = File(...),
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> DwgVersion:
    floor = db.get(Floor, floor_id)
    if not floor:
        raise SecurityError("FLOOR_NOT_FOUND", "Floor پیدا نشد.", 404, [])
    staged = await stage_upload(file)
    aggregate = floor.dwg_file
    if aggregate and any(version.sha256 == staged.sha256 for version in aggregate.versions):
        discard_staged_upload(staged)
        raise SecurityError(
            "DWG_DUPLICATE",
            "این نسخه DWG قبلاً برای Floor ثبت شده است.",
            409,
            [],
        )
    if aggregate is None:
        aggregate = DwgFile(floor=floor)
        db.add(aggregate)
        db.flush()
    version_number = len(aggregate.versions) + 1
    stored = finalize_upload(
        staged,
        pilot_code=floor.project.pilot.code,
        floor_code=floor.code,
        version=version_number,
    )
    version = DwgVersion(
        dwg_file=aggregate,
        version=version_number,
        original_filename=staged.original_filename,
        standardized_filename=stored.standardized_filename,
        storage_key=stored.storage_key,
        mime_type=staged.mime_type,
        size_bytes=staged.size_bytes,
        sha256=staged.sha256,
        dwg_signature=staged.signature,
        uploaded_by_user_id=context.user.id,
    )
    db.add(version)
    invalidate_from_stage(
        db,
        floor.project.pilot,
        3,
        actor_user_id=context.user.id,
        reason=f"DWG version {version_number} uploaded for {floor.code}",
    )
    try:
        db.flush()
        add_audit_log(
            db,
            action="dwg.version_uploaded",
            entity_type="DwgVersion",
            entity_id=version.id,
            actor_user_id=context.user.id,
            new_data={
                "floor_id": floor.id,
                "version": version_number,
                "sha256": staged.sha256,
                "size_bytes": staged.size_bytes,
            },
            session_id=context.session.id,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        delete_storage_key(stored.storage_key)
        raise SecurityError(
            "DWG_VERSION_CONFLICT",
            "ثبت هم‌زمان نسخه DWG با تعارض روبه‌رو شد؛ دوباره تلاش کنید.",
            409,
            [],
        ) from exc
    except Exception:
        db.rollback()
        delete_storage_key(stored.storage_key)
        raise
    db.refresh(version)
    return version


@router.get("/floors/{floor_id}/dwg/versions", response_model=list[DwgVersionRead])
def list_dwg_versions(
    floor_id: int,
    _: AuthContext = Depends(require_permission("pilots.read")),
    db: Session = Depends(get_db),
) -> list[DwgVersion]:
    floor = db.get(Floor, floor_id)
    if not floor:
        raise SecurityError("FLOOR_NOT_FOUND", "Floor پیدا نشد.", 404, [])
    return floor.dwg_file.versions if floor.dwg_file else []


@router.get("/dwg/versions/{version_id}/download")
def download_dwg(
    version_id: int,
    _: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> FileResponse:
    version = db.get(DwgVersion, version_id)
    if not version:
        raise SecurityError("DWG_NOT_FOUND", "نسخه DWG پیدا نشد.", 404, [])
    return FileResponse(
        resolve_storage_key(version.storage_key),
        media_type=version.mime_type,
        filename=version.standardized_filename,
    )


# --------------------------------------------------------------- bulk stage 3
#
# Stage 3 registers a building's floors and their drawings. One floor at a time
# meant a request per floor, the same file stored once per floor, and a run that
# could stop halfway leaving Stage 3 half-recorded. These endpoints do the same
# work in one transaction. The single-floor endpoints above are unchanged and
# remain the way to correct one floor.


def _parse_floor_ids(raw: str) -> list[int]:
    """Accept a JSON array or a comma-separated list, since multipart is text."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty")
    if text.startswith("["):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("not_a_list")
        values = parsed
    else:
        values = [part for part in text.split(",") if part.strip()]
    try:
        ids = [int(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("not_integers") from exc
    if not ids:
        raise ValueError("empty")
    if len(set(ids)) != len(ids):
        raise ValueError("repeated_ids")
    if len(ids) > 200:
        raise ValueError("too_many")
    return ids


def _resolve_pilot_floors(db: Session, pilot: Pilot, floor_ids: list[int]) -> list[Floor]:
    """Every id must name a floor of this pilot, or nothing is touched.

    Reports every id that failed rather than only the first, so the caller can
    fix the whole request in one pass. A floor belonging to another pilot and a
    floor that does not exist give the same answer on purpose: saying which is
    which would describe a pilot the caller may not be allowed to see.
    """
    floors_by_id = {floor.id: floor for floor in pilot.project.floors}
    missing = [floor_id for floor_id in floor_ids if floor_id not in floors_by_id]
    if missing:
        raise SecurityError(
            "BULK_FLOOR_NOT_FOUND",
            "برخی از طبقات انتخاب‌شده متعلق به این پرونده نیستند.",
            404,
            [{"field": "floor_ids", "reason": "not_in_pilot", "failed_floor_ids": missing}],
        )
    return [floors_by_id[floor_id] for floor_id in floor_ids]


@router.post(
    "/pilots/{pilot_id}/floors/bulk",
    response_model=FloorBulkCreateResult,
    status_code=status.HTTP_201_CREATED,
)
def create_floors_bulk(
    pilot_id: int,
    payload: FloorBulkCreate,
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> FloorBulkCreateResult:
    pilot = get_pilot(db, pilot_id)
    existing = pilot.project.floors
    if len(existing) + len(payload.floors) > pilot.project.total_floors:
        raise SecurityError(
            "FLOOR_LIMIT_REACHED",
            "تعداد Floor از مقدار ثبت‌شده پروژه بیشتر می‌شود.",
            409,
            [{
                "field": "floors",
                "reason": "exceeds_total_floors",
                "total_floors": pilot.project.total_floors,
                "existing": len(existing),
                "requested": len(payload.floors),
            }],
        )

    taken_codes = {floor.code for floor in existing}
    taken_orders = {floor.level_order for floor in existing}
    clashes = [
        item.code for item in payload.floors
        if item.code in taken_codes or item.level_order in taken_orders
    ]
    if clashes:
        raise SecurityError(
            "BULK_FLOOR_INVALID",
            "کد یا ترتیب برخی طبقات از قبل ثبت شده است.",
            409,
            [{"field": "floors", "reason": "already_exists", "failed_floor_codes": clashes}],
        )

    created = [Floor(project=pilot.project, **item.model_dump()) for item in payload.floors]
    db.add_all(created)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SecurityError(
            "BULK_FLOOR_INVALID",
            "کد یا ترتیب Floor تکراری است.",
            409,
            [{"field": "floors", "reason": "duplicate"}],
        ) from exc

    # One invalidation for the whole batch, not one per floor.
    invalidate_from_stage(
        db, pilot, 3,
        actor_user_id=context.user.id,
        reason=f"{len(created)} floors added in bulk",
    )
    add_audit_log(
        db,
        action="floors.bulk_created",
        entity_type="Project",
        entity_id=pilot.project.id,
        actor_user_id=context.user.id,
        pilot_id=pilot.id,
        new_data={
            "count": len(created),
            "floor_ids": [floor.id for floor in created],
            "codes": [floor.code for floor in created],
        },
        session_id=context.session.id,
    )
    db.commit()
    for floor in created:
        db.refresh(floor)
    return FloorBulkCreateResult(
        pilot_id=pilot.id,
        total=len(payload.floors),
        created=len(created),
        floors=[floor_read(floor) for floor in created],
    )


@router.put(
    "/pilots/{pilot_id}/floors/dwg-reference/bulk",
    response_model=FloorDwgReferenceBulkResult,
)
def update_floors_dwg_reference_bulk(
    pilot_id: int,
    payload: FloorDwgReferenceBulkUpdate,
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> FloorDwgReferenceBulkResult:
    pilot = get_pilot(db, pilot_id)
    floors = _resolve_pilot_floors(db, pilot, payload.floor_ids)

    confirmed_at = product_utc_now() if payload.confirmed else None
    confirmed_by = context.user.id if payload.confirmed else None
    previous = {floor.id: floor.dwg_reference_confirmed for floor in floors}
    for floor in floors:
        floor.dwg_reference_confirmed = payload.confirmed
        floor.dwg_reference_confirmed_at = confirmed_at
        floor.dwg_reference_confirmed_by_user_id = confirmed_by

    invalidate_from_stage(
        db, pilot, 3,
        actor_user_id=context.user.id,
        reason=f"DWG reference confirmation changed for {len(floors)} floors",
    )
    add_audit_log(
        db,
        action="floors.bulk_dwg_reference_updated",
        entity_type="Project",
        entity_id=pilot.project.id,
        actor_user_id=context.user.id,
        pilot_id=pilot.id,
        old_data={"confirmed": previous},
        new_data={
            "confirmed": payload.confirmed,
            "floor_ids": [floor.id for floor in floors],
        },
        session_id=context.session.id,
    )
    db.commit()
    for floor in floors:
        db.refresh(floor)
    return FloorDwgReferenceBulkResult(
        pilot_id=pilot.id,
        total=len(payload.floor_ids),
        updated=len(floors),
        floors=[
            FloorDwgReferenceBulkItem(
                id=floor.id,
                dwg_reference_confirmed=floor.dwg_reference_confirmed,
                has_valid_dwg=floor_read(floor).has_valid_dwg,
            )
            for floor in floors
        ],
    )


@router.post(
    "/pilots/{pilot_id}/floors/dwg/shared",
    response_model=SharedDwgUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_shared_dwg(
    pilot_id: int,
    file: UploadFile = File(...),
    floor_ids: str = Form(...),
    idempotency_key: str | None = Form(default=None),
    context: AuthContext = Depends(require_permission("dwg.manage")),
    db: Session = Depends(get_db),
) -> SharedDwgUploadResult:
    pilot = get_pilot(db, pilot_id)
    try:
        requested_ids = _parse_floor_ids(floor_ids)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SecurityError(
            "BULK_FLOOR_INVALID",
            "فهرست طبقات معتبر نیست.",
            422,
            [{"field": "floor_ids", "reason": str(exc)}],
        ) from exc

    floors = _resolve_pilot_floors(db, pilot, requested_ids)

    # Validate the file before creating anything: stage_upload checks extension,
    # MIME, signature and size, and writes to a temp path it owns, so a rejected
    # upload leaves nothing behind.
    staged = await stage_upload(file)

    already_holding = [
        floor.code
        for floor in floors
        if floor.dwg_file
        and any(version.sha256 == staged.sha256 for version in floor.dwg_file.versions)
    ]
    if already_holding:
        discard_staged_upload(staged)
        raise SecurityError(
            "BULK_DWG_DUPLICATE",
            "این نسخه DWG قبلاً برای برخی از این طبقات ثبت شده است.",
            409,
            [{
                "field": "file",
                "reason": "duplicate_sha256",
                "sha256": staged.sha256,
                "failed_floor_codes": already_holding,
            }],
        )

    # The bytes land once; every floor points at this one key.
    try:
        stored = finalize_shared_upload(staged, pilot_code=pilot.code)
    except SecurityError:
        raise
    except OSError as exc:
        discard_staged_upload(staged)
        raise SecurityError(
            "BULK_DWG_STORAGE_FAILED",
            "ذخیره فایل DWG انجام نشد.",
            500,
            [{"field": "file", "reason": "storage_error"}],
        ) from exc

    versions: list[DwgVersion] = []
    try:
        for floor in floors:
            aggregate = floor.dwg_file
            if aggregate is None:
                aggregate = DwgFile(floor=floor)
                db.add(aggregate)
                db.flush()
            version_number = len(aggregate.versions) + 1
            version = DwgVersion(
                dwg_file=aggregate,
                version=version_number,
                original_filename=staged.original_filename,
                standardized_filename=stored.standardized_filename,
                storage_key=stored.storage_key,
                mime_type=staged.mime_type,
                size_bytes=staged.size_bytes,
                sha256=staged.sha256,
                dwg_signature=staged.signature,
                uploaded_by_user_id=context.user.id,
            )
            db.add(version)
            versions.append(version)

        # One invalidation for the batch, not one per floor.
        invalidate_from_stage(
            db, pilot, 3,
            actor_user_id=context.user.id,
            reason=f"Shared DWG uploaded for {len(floors)} floors",
        )
        db.flush()
        add_audit_log(
            db,
            action="dwg.shared_version_uploaded",
            entity_type="Project",
            entity_id=pilot.project.id,
            actor_user_id=context.user.id,
            pilot_id=pilot.id,
            new_data={
                "sha256": staged.sha256,
                "size_bytes": staged.size_bytes,
                "storage_key": stored.storage_key,
                "idempotency_key": idempotency_key,
                "floor_ids": [floor.id for floor in floors],
                "version_ids": [version.id for version in versions],
            },
            session_id=context.session.id,
        )
        db.commit()
    except Exception as exc:
        # Nothing was committed, so the stored file has no owner. Remove it
        # rather than leave an unreferenced blob on disk.
        db.rollback()
        delete_storage_key(stored.storage_key)
        if isinstance(exc, SecurityError):
            raise
        raise SecurityError(
            "BULK_DWG_FAILED",
            "ثبت گروهی نقشه انجام نشد.",
            409,
            [{"field": "floor_ids", "reason": "persistence_failed"}],
        ) from exc

    for version in versions:
        db.refresh(version)
    return SharedDwgUploadResult(
        pilot_id=pilot.id,
        file=SharedDwgFileSummary(
            original_filename=staged.original_filename,
            standardized_filename=stored.standardized_filename,
            storage_key=stored.storage_key,
            mime_type=staged.mime_type,
            size_bytes=staged.size_bytes,
            sha256=staged.sha256,
        ),
        total=len(requested_ids),
        uploaded=len(versions),
        versions=[
            SharedDwgVersionItem(
                floor_id=version.dwg_file.floor_id,
                floor_code=version.dwg_file.floor.code,
                version_id=version.id,
                version=version.version,
                has_valid_dwg=floor_read(version.dwg_file.floor).has_valid_dwg,
            )
            for version in versions
        ],
    )
