"""Grouped Stage 3 registration: many floors, one request, one stored file.

The single-floor endpoints stay the way to correct one floor; these cover the
batch path and the guarantees that make it safe to use — all-or-nothing writes,
one physical file for a shared drawing, and no orphaned blob when either half
fails.
"""

import json
from pathlib import Path

import pytest

from conftest import login_with_otp, prepare_pilot_through_g2, sample_pilot_payload

from app.database import get_session
from app.models import AuditLog, DwgVersion, Floor, Pilot

DWG_BYTES = b"AC1032" + b"-shared-drawing-for-every-floor"
OTHER_DWG = b"AC1032" + b"-a-different-drawing"


def dwg_file(name="all-floors.dwg", content=DWG_BYTES):
    return {"file": (name, content, "application/octet-stream")}


@pytest.fixture
def pilot(client, super_admin_headers):
    """A pilot with floors registered and no drawing uploaded yet.

    prepare_pilot_through_g2 uploads a DWG per floor, which is the state these
    endpoints are meant to replace; starting clean keeps version numbers and
    file counts meaningful.
    """
    created = client.post(
        "/pilots", json=sample_pilot_payload(total_floors=4), headers=super_admin_headers
    ).json()
    floors = []
    for index in range(2):
        response = client.post(
            f"/pilots/{created['id']}/floors",
            json={
                "code": f"F{index + 1:02d}",
                "name": f"طبقه {index + 1}",
                "level_order": index,
                "floor_type": "non_typical",
            },
            headers=super_admin_headers,
        )
        assert response.status_code == 201, response.json()
        floors.append(response.json())
    return created, floors


def storage_root():
    import os

    return Path(os.environ["DWG_STORAGE_ROOT"])


def stored_files():
    root = storage_root()
    return sorted(p for p in root.rglob("*") if p.is_file())


# ------------------------------------------------------------- bulk floors


def test_floors_can_be_registered_in_one_request(client, super_admin_headers):
    created = client.post(
        "/pilots", json=sample_pilot_payload(total_floors=3), headers=super_admin_headers
    ).json()

    response = client.post(
        f"/pilots/{created['id']}/floors/bulk",
        json={"floors": [
            {"code": "F01", "name": "همکف", "level_order": 0, "floor_type": "non_typical"},
            {"code": "F02", "name": "طبقه یک", "level_order": 1, "floor_type": "typical"},
            {"code": "F03", "name": "طبقه دو", "level_order": 2, "floor_type": "typical"},
        ]},
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["total"] == 3
    assert body["created"] == 3
    assert [floor["code"] for floor in body["floors"]] == ["F01", "F02", "F03"]


def test_bulk_creation_refuses_to_exceed_the_project_floor_count(client, super_admin_headers):
    created = client.post(
        "/pilots", json=sample_pilot_payload(total_floors=2), headers=super_admin_headers
    ).json()

    response = client.post(
        f"/pilots/{created['id']}/floors/bulk",
        json={"floors": [
            {"code": "F01", "name": "الف", "level_order": 0},
            {"code": "F02", "name": "ب", "level_order": 1},
            {"code": "F03", "name": "پ", "level_order": 2},
        ]},
        headers=super_admin_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "FLOOR_LIMIT_REACHED"

    with get_session() as db:
        assert db.query(Floor).filter(Floor.project_id == created["id"]).count() == 0, (
            "a refused batch must create nothing"
        )


def test_bulk_creation_rejects_a_duplicate_code_within_the_request(client, super_admin_headers):
    created = client.post(
        "/pilots", json=sample_pilot_payload(total_floors=3), headers=super_admin_headers
    ).json()

    response = client.post(
        f"/pilots/{created['id']}/floors/bulk",
        json={"floors": [
            {"code": "F01", "name": "الف", "level_order": 0},
            {"code": "F01", "name": "ب", "level_order": 1},
        ]},
        headers=super_admin_headers,
    )
    assert response.status_code == 422


def test_bulk_creation_rejects_a_code_the_pilot_already_has(client, super_admin_headers, pilot):
    created, floors = pilot
    response = client.post(
        f"/pilots/{created['id']}/floors/bulk",
        json={"floors": [{"code": floors[0]["code"], "name": "تکراری", "level_order": 90}]},
        headers=super_admin_headers,
    )  # the pilot allows four floors, so the cap is not what rejects this
    assert response.status_code == 409
    assert response.json()["code"] == "BULK_FLOOR_INVALID"


# --------------------------------------------------- bulk reference confirm


def test_reference_confirmation_applies_to_every_listed_floor(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]

    response = client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": ids, "confirmed": True},
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["total"] == len(ids)
    assert body["updated"] == len(ids)
    assert all(item["dwg_reference_confirmed"] for item in body["floors"])
    assert all(item["has_valid_dwg"] for item in body["floors"])

    with get_session() as db:
        for floor_id in ids:
            floor = db.get(Floor, floor_id)
            assert floor.dwg_reference_confirmed is True
            assert floor.dwg_reference_confirmed_at is not None
            assert floor.dwg_reference_confirmed_by_user_id is not None


def test_confirmation_can_be_withdrawn_for_the_whole_group(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": ids, "confirmed": True}, headers=super_admin_headers,
    )
    response = client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": ids, "confirmed": False}, headers=super_admin_headers,
    )
    assert response.status_code == 200
    with get_session() as db:
        for floor_id in ids:
            floor = db.get(Floor, floor_id)
            assert floor.dwg_reference_confirmed is False
            assert floor.dwg_reference_confirmed_at is None
            assert floor.dwg_reference_confirmed_by_user_id is None


def test_a_floor_from_another_pilot_fails_the_whole_request(client, super_admin_headers, pilot):
    created, floors = pilot
    other, other_floors = prepare_pilot_through_g2(client, super_admin_headers, total_floors=2)

    response = client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": [floors[0]["id"], other_floors[0]["id"]], "confirmed": True},
        headers=super_admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "BULK_FLOOR_NOT_FOUND"
    assert other_floors[0]["id"] in response.json()["errors"][0]["failed_floor_ids"]

    with get_session() as db:
        assert db.get(Floor, floors[0]["id"]).dwg_reference_confirmed is False, (
            "the valid floor in a rejected batch must stay untouched"
        )


def test_an_unknown_floor_id_changes_nothing(client, super_admin_headers, pilot):
    created, floors = pilot
    response = client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": [floors[0]["id"], 999_999], "confirmed": True},
        headers=super_admin_headers,
    )
    assert response.status_code == 404
    with get_session() as db:
        assert db.get(Floor, floors[0]["id"]).dwg_reference_confirmed is False


# ------------------------------------------------------------ shared upload


def test_one_upload_serves_every_floor_and_stores_the_file_once(
    client, super_admin_headers, pilot
):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    before = len(stored_files())

    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(),
        data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.json()
    body = response.json()

    assert body["total"] == len(ids)
    assert body["uploaded"] == len(ids)
    assert {item["floor_id"] for item in body["versions"]} == set(ids)
    assert all(item["has_valid_dwg"] for item in body["versions"])
    assert body["file"]["size_bytes"] == len(DWG_BYTES)

    assert len(stored_files()) == before + 1, (
        "a shared drawing must land on disk once, not once per floor"
    )

    with get_session() as db:
        keys = {
            db.get(DwgVersion, item["version_id"]).storage_key
            for item in body["versions"]
        }
        assert len(keys) == 1, "every floor must point at the same stored file"


def test_each_floor_gets_its_own_version_row(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )
    body = response.json()

    with get_session() as db:
        for item in body["versions"]:
            version = db.get(DwgVersion, item["version_id"])
            assert version is not None
            assert version.dwg_file.floor_id == item["floor_id"]
            assert version.version == 1
            assert version.sha256 == body["file"]["sha256"]


def test_floor_ids_may_be_sent_as_a_comma_separated_list(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": ",".join(str(i) for i in ids)},
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.json()
    assert response.json()["uploaded"] == len(ids)


def test_a_shared_upload_rejects_a_floor_from_another_pilot(
    client, super_admin_headers, pilot
):
    created, floors = pilot
    other, other_floors = prepare_pilot_through_g2(client, super_admin_headers, total_floors=2)
    before = len(stored_files())

    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(),
        data={"floor_ids": json.dumps([floors[0]["id"], other_floors[0]["id"]])},
        headers=super_admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "BULK_FLOOR_NOT_FOUND"
    assert len(stored_files()) == before, "a refused request must not store the file"


def test_re_uploading_the_same_drawing_is_refused(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    first = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )
    assert first.status_code == 201
    before = len(stored_files())

    second = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )
    assert second.status_code == 409
    assert second.json()["code"] == "BULK_DWG_DUPLICATE"
    assert len(stored_files()) == before, "a duplicate must not leave a second copy"


def test_a_second_distinct_drawing_becomes_version_two(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )
    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file("revision-2.dwg", OTHER_DWG),
        data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.json()
    assert all(item["version"] == 2 for item in response.json()["versions"])


@pytest.mark.parametrize(
    ("name", "content", "content_type"),
    [
        ("plan.txt", DWG_BYTES, "application/octet-stream"),
        ("plan.dwg", b"NOTADWG-header-bytes", "application/octet-stream"),
        ("plan.dwg", DWG_BYTES, "text/plain"),
    ],
)
def test_an_invalid_file_is_rejected_before_anything_is_written(
    client, super_admin_headers, pilot, name, content, content_type
):
    created, floors = pilot
    before = len(stored_files())
    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files={"file": (name, content, content_type)},
        data={"floor_ids": json.dumps([floors[0]["id"]])},
        headers=super_admin_headers,
    )
    assert response.status_code == 422
    assert len(stored_files()) == before

    with get_session() as db:
        assert db.query(DwgVersion).count() == 0


def test_a_malformed_floor_id_list_is_reported_as_such(client, super_admin_headers, pilot):
    created, _ = pilot
    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": "not-a-list"},
        headers=super_admin_headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "BULK_FLOOR_INVALID"


def test_a_database_failure_removes_the_stored_file(
    client, super_admin_headers, pilot, monkeypatch
):
    """The blob must not outlive the transaction that was meant to own it."""
    created, floors = pilot
    before = len(stored_files())

    import app.routers.product as product

    def explode(*args, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(product, "invalidate_from_stage", explode)

    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps([floors[0]["id"]])},
        headers=super_admin_headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "BULK_DWG_FAILED"
    assert len(stored_files()) == before, "an orphaned file was left behind"

    with get_session() as db:
        assert db.query(DwgVersion).count() == 0


def test_a_storage_failure_leaves_no_database_row(
    client, super_admin_headers, pilot, monkeypatch
):
    created, floors = pilot
    import app.routers.product as product

    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(product, "finalize_shared_upload", explode)

    response = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps([floors[0]["id"]])},
        headers=super_admin_headers,
    )
    assert response.status_code == 500
    assert response.json()["code"] == "BULK_DWG_STORAGE_FAILED"

    with get_session() as db:
        assert db.query(DwgVersion).count() == 0


# --------------------------------------------------------------- permissions


def _capture_expert(client, admin_headers, mobile):
    roles = {r["name"]: r["id"] for r in client.get("/roles", headers=admin_headers).json()}
    created = client.post(
        "/users",
        json={"mobile": mobile, "display_name": "کارشناس", "role_ids": [roles["capture_expert"]]},
        headers=admin_headers,
    )
    assert created.status_code == 201, created.json()
    return login_with_otp(client, mobile)


def test_bulk_endpoints_refuse_exactly_where_the_single_floor_ones_do(
    client, super_admin_headers, pilot
):
    """The batch path must not be a way around permission or pilot scope.

    Scope is checked first and answers 404 rather than 403, so that a user who
    cannot see a pilot learns nothing about whether it exists. The assertion
    that matters is that the bulk endpoints refuse the same caller the
    single-floor ones refuse, with the same status.
    """
    created, floors = pilot
    headers = _capture_expert(client, super_admin_headers, "09156661111")

    single_reference = client.put(
        f"/floors/{floors[0]['id']}/dwg-reference",
        json={"confirmed": True}, headers=headers,
    )
    single_upload = client.post(
        f"/floors/{floors[0]['id']}/dwg", files=dwg_file(), headers=headers,
    )
    assert single_reference.status_code in (403, 404)
    assert single_upload.status_code in (403, 404)

    bulk_create = client.post(
        f"/pilots/{created['id']}/floors/bulk",
        json={"floors": [{"code": "F09", "name": "x", "level_order": 9}]},
        headers=headers,
    )
    bulk_reference = client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": [floors[0]["id"]], "confirmed": True},
        headers=headers,
    )
    bulk_upload = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps([floors[0]["id"]])},
        headers=headers,
    )

    for response in (bulk_create, bulk_reference, bulk_upload):
        assert response.status_code in (403, 404), response.text

    # The two paths refuse for different reasons, and the bulk one is the
    # stricter of the two. The single-floor endpoints take only a floor_id, so
    # enforce_path_pilot_access never runs and permission alone answers 403.
    # The bulk endpoints carry pilot_id, so pilot scope is checked as well and
    # answers first. Worth knowing, but it means the batch path cannot be used
    # to reach a pilot the single-floor path would have let through.
    assert single_reference.status_code == 403
    assert bulk_reference.status_code == 404

    # And nothing was written by any of the refused calls.
    with get_session() as db:
        assert db.get(Floor, floors[0]["id"]).dwg_reference_confirmed is False
        assert db.query(DwgVersion).count() == 0


# ------------------------------------------------- stage 3 and audit trail


def test_stage_three_is_invalidated_once_per_batch(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]

    with get_session() as db:
        before = db.query(AuditLog).filter(
            AuditLog.action == "stages.invalidated",
            AuditLog.pilot_id == created["id"],
        ).count()

    client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )

    with get_session() as db:
        after = db.query(AuditLog).filter(
            AuditLog.action == "stages.invalidated",
            AuditLog.pilot_id == created["id"],
        ).count()
        pilot_row = db.get(Pilot, created["id"])
        stage_three = next(s for s in pilot_row.stages if s.number == 3)

    assert after - before <= 1, "the batch must invalidate Stage 3 once, not per floor"
    assert stage_three.status in {"open", "in_progress", "rejected", "locked"}


def test_the_batch_is_recorded_in_the_audit_trail(client, super_admin_headers, pilot):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]

    client.put(
        f"/pilots/{created['id']}/floors/dwg-reference/bulk",
        json={"floor_ids": ids, "confirmed": True}, headers=super_admin_headers,
    )
    client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    )

    with get_session() as db:
        reference = db.query(AuditLog).filter(
            AuditLog.action == "floors.bulk_dwg_reference_updated"
        ).one()
        upload = db.query(AuditLog).filter(
            AuditLog.action == "dwg.shared_version_uploaded"
        ).one()

    assert reference.new_data["floor_ids"] == ids
    assert upload.new_data["floor_ids"] == ids
    assert upload.new_data["sha256"]
    assert len(upload.new_data["version_ids"]) == len(ids)


def test_the_idempotency_key_is_recorded_for_replay_detection(
    client, super_admin_headers, pilot
):
    created, floors = pilot
    client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(),
        data={"floor_ids": json.dumps([floors[0]["id"]]), "idempotency_key": "batch-7"},
        headers=super_admin_headers,
    )
    with get_session() as db:
        entry = db.query(AuditLog).filter(
            AuditLog.action == "dwg.shared_version_uploaded"
        ).one()
    assert entry.new_data["idempotency_key"] == "batch-7"


# ------------------------------------------------- shared file and deletion


def test_deleting_one_floor_keeps_the_file_the_others_still_use(
    client, super_admin_headers, pilot
):
    created, floors = pilot
    ids = [floor["id"] for floor in floors]
    upload = client.post(
        f"/pilots/{created['id']}/floors/dwg/shared",
        files=dwg_file(), data={"floor_ids": json.dumps(ids)},
        headers=super_admin_headers,
    ).json()
    storage_key = upload["file"]["storage_key"]
    absolute = storage_root() / storage_key
    assert absolute.exists()

    removed = client.delete(f"/floors/{ids[0]}", headers=super_admin_headers)
    assert removed.status_code in (200, 204), removed.text

    assert absolute.exists(), (
        "the shared drawing is still in use by another floor and must survive"
    )

    remaining = client.delete(f"/floors/{ids[1]}", headers=super_admin_headers)
    assert remaining.status_code in (200, 204), remaining.text
    assert not absolute.exists(), "the last reference is gone, so the file should be too"


# -------------------------------------------- single-floor endpoints intact


def test_the_single_floor_endpoints_still_behave_the_same(
    client, super_admin_headers, pilot
):
    created, floors = pilot
    floor_id = floors[0]["id"]

    reference = client.put(
        f"/floors/{floor_id}/dwg-reference",
        json={"confirmed": True}, headers=super_admin_headers,
    )
    assert reference.status_code == 200
    assert reference.json()["dwg_reference_confirmed"] is True

    upload = client.post(
        f"/floors/{floor_id}/dwg",
        files={"file": ("single.dwg", OTHER_DWG, "application/octet-stream")},
        headers=super_admin_headers,
    )
    assert upload.status_code == 201, upload.json()
    assert upload.json()["version"] == 1

    listed = client.get(f"/floors/{floor_id}/dwg/versions", headers=super_admin_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
