from conftest import sample_pilot_payload, save_valid_f01
from app.config import get_dwg_storage_root
from app.main import app


def create_pilot(client, headers, total_floors=2):
    response = client.post(
        "/pilots",
        json=sample_pilot_payload(total_floors=total_floors),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def submit_and_approve(client, pilot_id, stage_number, headers):
    submitted = client.post(
        f"/pilots/{pilot_id}/stages/{stage_number}/submit",
        json={},
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.json()
    approved = client.post(
        f"/pilots/{pilot_id}/stages/{stage_number}/approve",
        json={},
        headers=headers,
    )
    assert approved.status_code == 200, approved.json()
    return approved.json()


def test_project_and_dwg_openapi_contract():
    schema = app.openapi()
    for path in (
        "/pilots/{pilot_id}/forms/f01",
        "/pilots/{pilot_id}/forms/f02",
        "/pilots/{pilot_id}/floors",
        "/floors/{floor_id}",
        "/floors/{floor_id}/dwg-reference",
        "/floors/{floor_id}/dwg",
        "/floors/{floor_id}/dwg/versions",
        "/dwg/versions/{version_id}/download",
    ):
        assert path in schema["paths"]
    upload_content = schema["paths"]["/floors/{floor_id}/dwg"]["post"][
        "requestBody"
    ]["content"]
    assert "multipart/form-data" in upload_content
    assert {"owner", "project"} <= set(
        schema["components"]["schemas"]["PilotCreate"]["required"]
    )


def test_project_and_f01_are_canonical_stage_data(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers, total_floors=1)
    assert pilot["project"]["system_name"] == "project-1"
    assert pilot["project"]["owner"]["name"] == "شرکت نمونه"
    assert pilot["display_name"].endswith("PIL-1405-001")

    invalid_f01 = {
        "project_active": True,
        "imaging_value": False,
        "remote_viewing_need": True,
        "access_possible": True,
        "dwg_available": True,
        "continued_capacity": True,
        "not_demo_only": True,
        "introduction_completed": True,
        "imaging_accepted": True,
        "dwg_accepted": True,
        "feedback_accepted": True,
        "coordinator_name": "هماهنگ‌کننده",
        "coordinator_mobile": "09152222222",
        "result": "approved",
    }
    assert (
        client.put(
            f"/pilots/{pilot['id']}/forms/f01",
            json=invalid_f01,
            headers=super_admin_headers,
        ).status_code
        == 200
    )
    rejected = client.post(
        f"/pilots/{pilot['id']}/stages/1/submit",
        json={
            "form_data": {"owner_name": "داده جعلی"},
            "checklist": {"imaging_value": True},
        },
        headers=super_admin_headers,
    )
    assert rejected.status_code == 422
    assert any(
        error["field"] == "checklist.imaging_value" for error in rejected.json()["errors"]
    )


def test_stage_three_accepts_audited_dwg_reference_without_upload(
    client, super_admin_headers
):
    pilot = create_pilot(client, super_admin_headers, total_floors=2)
    pilot_id = pilot["id"]
    save_valid_f01(client, pilot_id, super_admin_headers)
    submit_and_approve(client, pilot_id, 1, super_admin_headers)
    submit_and_approve(client, pilot_id, 2, super_admin_headers)

    floors = []
    for index in range(2):
        floor = client.post(
            f"/pilots/{pilot_id}/floors",
            json={
                "code": f"F{index + 1:02d}",
                "name": f"طبقه {index + 1}",
                "level_order": index,
                "floor_type": "non_typical",
            },
            headers=super_admin_headers,
        ).json()
        floors.append(floor)
        confirmed = client.put(
            f"/floors/{floor['id']}/dwg-reference",
            json={"confirmed": True},
            headers=super_admin_headers,
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["has_dwg"] is False
        assert confirmed.json()["has_valid_dwg"] is True
        assert confirmed.json()["dwg_reference_confirmed"] is True
        assert confirmed.json()["dwg_reference_confirmed_at"]
        assert confirmed.json()["dwg_reference_confirmed_by_user_id"]

    stage_3 = submit_and_approve(client, pilot_id, 3, super_admin_headers)
    snapshot_floors = stage_3["snapshot"]["content"]["submission"]["form_data"][
        "floors"
    ]
    assert all(item["has_valid_dwg"] for item in snapshot_floors)
    assert all(
        item["dwg_source"] == "main_platform_or_unavailable"
        for item in snapshot_floors
    )

    audit = client.get("/audit", headers=super_admin_headers).json()
    assert sum(
        item["action"] == "floors.dwg_reference_updated"
        for item in audit
    ) == 2


def test_dwg_security_versioning_g2_and_snapshot_preservation(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers)
    pilot_id = pilot["id"]
    save_valid_f01(client, pilot_id, super_admin_headers)
    submit_and_approve(client, pilot_id, 1, super_admin_headers)
    save_valid_f01(client, pilot_id, super_admin_headers)
    assert (
        client.get(f"/pilots/{pilot_id}", headers=super_admin_headers).json()[
            "current_stage"
        ]
        == 2
    )
    submit_and_approve(client, pilot_id, 2, super_admin_headers)

    floors = []
    for code, name, order in [("F01", "همکف", 0), ("F02", "طبقه اول", 1)]:
        response = client.post(
            f"/pilots/{pilot_id}/floors",
            json={
                "code": code,
                "name": name,
                "level_order": order,
                "floor_type": "non_typical",
            },
            headers=super_admin_headers,
        )
        assert response.status_code == 201
        floors.append(response.json())

    pdf = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={"file": ("plan.pdf", b"%PDF-1.7", "application/pdf")},
        headers=super_admin_headers,
    )
    assert pdf.status_code == 422
    assert pdf.json()["code"] == "DWG_INVALID_EXTENSION"

    wrong_mime = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={"file": ("plan.dwg", b"AC1032-data", "application/pdf")},
        headers=super_admin_headers,
    )
    assert wrong_mime.status_code == 422
    assert wrong_mime.json()["code"] == "DWG_INVALID_MIME"

    fake_dwg = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={"file": ("plan.dwg", b"not-a-real-dwg", "application/octet-stream")},
        headers=super_admin_headers,
    )
    assert fake_dwg.status_code == 422
    assert fake_dwg.json()["code"] == "DWG_INVALID_SIGNATURE"

    traversal = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={
            "file": (
                "../escape.dwg",
                b"AC1032-path-traversal",
                "application/octet-stream",
            )
        },
        headers=super_admin_headers,
    )
    assert traversal.status_code == 422
    assert traversal.json()["code"] == "DWG_INVALID_EXTENSION"

    first_content = b"AC1032" + b"-floor-one-v1"
    first_version = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={"file": ("floor-one.dwg", first_content, "application/octet-stream")},
        headers=super_admin_headers,
    )
    assert first_version.status_code == 201
    assert first_version.json()["version"] == 1
    assert first_version.json()["standardized_filename"].startswith(
        "PIL-1405-001_F01_V01_"
    )


    duplicate = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={"file": ("duplicate.dwg", first_content, "application/octet-stream")},
        headers=super_admin_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DWG_DUPLICATE"
    assert not (get_dwg_storage_root() / ".tmp").exists()

    second_floor_version = client.post(
        f"/floors/{floors[1]['id']}/dwg",
        files={
            "file": (
                "floor-two.dwg",
                b"AC1032-floor-two-v1",
                "image/vnd.dwg",
            )
        },
        headers=super_admin_headers,
    )
    assert second_floor_version.status_code == 201

    download = client.get(
        f"/dwg/versions/{first_version.json()['id']}/download",
        headers=super_admin_headers,
    )
    assert download.status_code == 200
    assert download.content == first_content

    stage_3 = submit_and_approve(client, pilot_id, 3, super_admin_headers)
    assert stage_3["snapshot"]["content"]["submission"]["form_data"]["floors"][0][
        "has_valid_dwg"
    ]

    f02 = client.put(
        f"/pilots/{pilot_id}/forms/f02",
        json={
            "information_package": "بسته اطلاعاتی کامل",
            "contacts_summary": "مالک و هماهنگ‌کننده",
            "progress_status": "آماده برداشت",
            "main_project_registered": True,
            "floor_order_confirmed": True,
            "typical_floors_identified": True,
            "plan_connections_registered": True,
            "start_point_registered": True,
            "expert_access_tested": True,
            "main_app_display_tested": True,
            "ready_for_capture": True,
        },
        headers=super_admin_headers,
    )
    assert f02.status_code == 200
    submit_and_approve(client, pilot_id, 4, super_admin_headers)

    after_g2 = client.get(f"/pilots/{pilot_id}", headers=super_admin_headers).json()
    assert after_g2["current_stage"] == 5
    assert next(gate for gate in after_g2["gates"] if gate["code"] == "G2")[
        "status"
    ] == "passed"

    revised_dwg = client.post(
        f"/floors/{floors[0]['id']}/dwg",
        files={
            "file": (
                "floor-one-revised.dwg",
                b"AC1032-floor-one-v2",
                "application/octet-stream",
            )
        },
        headers=super_admin_headers,
    )
    assert revised_dwg.status_code == 201
    assert revised_dwg.json()["version"] == 2
    original_download = client.get(
        f"/dwg/versions/{first_version.json()['id']}/download",
        headers=super_admin_headers,
    )
    assert original_download.status_code == 200
    assert original_download.content == first_content

    reopened = client.get(f"/pilots/{pilot_id}", headers=super_admin_headers).json()
    assert reopened["current_stage"] == 3
    assert reopened["stages"][2]["status"] == "needs_revision"
    assert next(gate for gate in reopened["gates"] if gate["code"] == "G2")[
        "status"
    ] == "locked"
    assert len(
        client.get(
            f"/pilots/{pilot_id}/stages/3/snapshots",
            headers=super_admin_headers,
        ).json()
    ) == 1


def test_floor_delete_removes_dwg(client, super_admin_headers):
    pilot = create_pilot(client, super_admin_headers, total_floors=2)
    floor = client.post(
        f"/pilots/{pilot['id']}/floors",
        json={
            "code": "F01",
            "name": "طبقه قابل حذف",
            "level_order": 0,
            "floor_type": "non_typical",
        },
        headers=super_admin_headers,
    ).json()
    version = client.post(
        f"/floors/{floor['id']}/dwg",
        files={
            "file": (
                "delete-me.dwg",
                b"AC1032-delete-me",
                "application/octet-stream",
            )
        },
        headers=super_admin_headers,
    )
    assert version.status_code == 201
    deleted = client.delete(
        f"/floors/{floor['id']}",
        headers=super_admin_headers,
    )
    assert deleted.status_code == 204
    assert client.get(
        f"/floors/{floor['id']}/dwg/versions",
        headers=super_admin_headers,
    ).status_code == 404
    assert list(get_dwg_storage_root().rglob("*.dwg")) == []
    audit = client.get("/audit", headers=super_admin_headers).json()
    assert any(
        item["action"] == "floors.deleted"
        and item["old_data"]["code"] == "F01"
        for item in audit
    )


def test_dwg_size_limit_cleans_temporary_file(client, super_admin_headers, monkeypatch):
    pilot = create_pilot(client, super_admin_headers, total_floors=1)
    floor = client.post(
        f"/pilots/{pilot['id']}/floors",
        json={
            "code": "F01",
            "name": "همکف",
            "level_order": 0,
            "floor_type": "typical",
        },
        headers=super_admin_headers,
    ).json()
    monkeypatch.setenv("DWG_MAX_BYTES", "8")
    response = client.post(
        f"/floors/{floor['id']}/dwg",
        files={
            "file": (
                "oversized.dwg",
                b"AC1032-this-is-over-eight-bytes",
                "application/octet-stream",
            )
        },
        headers=super_admin_headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "DWG_TOO_LARGE"
    assert list(get_dwg_storage_root().rglob("*.tmp")) == []
