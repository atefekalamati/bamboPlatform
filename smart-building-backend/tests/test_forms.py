from conftest import prepare_pilot_through_g2

from app.database import get_session
from app.models import Incident, Mission, Pilot, StageSubmission


def create_capture_expert(client, headers, mobile="09153334444"):
    roles = client.get("/roles", headers=headers).json()
    role_id = next(role["id"] for role in roles if role["name"] == "capture_expert")
    response = client.post(
        "/users",
        json={
            "mobile": mobile,
            "display_name": "کارشناس برداشت",
            "role_ids": [role_id],
            "confirmed": True,
        },
        headers=headers,
    )
    if response.status_code == 422:
        response = client.post(
            "/users",
            json={
                "mobile": mobile,
                "display_name": "کارشناس برداشت",
                "role_ids": [role_id],
            },
            headers=headers,
        )
    assert response.status_code == 201, response.json()
    return response.json()


def mission_payload(expert_id, floor_ids):
    return {
        "expert_user_id": expert_id,
        "scheduled_start": "2027-01-10T08:00:00+00:00",
        "scheduled_end": "2027-01-10T10:00:00+00:00",
        "floor_ids": floor_ids,
        "location": "مشهد، محل پروژه",
        "site_contact_name": "هماهنگ‌کننده نمونه",
        "site_contact_mobile": "09152222222",
        "limitation": "ورود فقط با هماهنگی",
    }


def record_counts():
    with get_session() as db:
        return {
            "pilots": db.query(Pilot).count(),
            "missions": db.query(Mission).count(),
            "incidents": db.query(Incident).count(),
            "submissions": db.query(StageSubmission).count(),
        }


def test_official_forms_are_aggregated_and_read_only(client, super_admin_headers):
    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    expert = create_capture_expert(client, super_admin_headers)
    mission = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201, mission.json()
    mission_id = mission.json()["id"]

    before = record_counts()
    forms = client.get(f"/pilots/{pilot['id']}/forms", headers=super_admin_headers)
    assert forms.status_code == 200, forms.json()
    assert {item["form_code"] for item in forms.json()} == {"F01", "F02", "F03", "F04", "F05"}
    assert next(item for item in forms.json() if item["form_code"] == "F03")[
        "printable_count"
    ] == 1

    f01 = client.get(f"/pilots/{pilot['id']}/forms/f01/preview", headers=super_admin_headers)
    assert f01.status_code == 200, f01.json()
    assert f01.json()["document_code"] == "BAMBO-PILOT-F01"
    assert f01.json()["data"]["اطلاعات عمومی"]["کد پرونده"] == pilot["code"]

    f03 = client.get(
        f"/pilots/{pilot['id']}/forms/f03/{mission_id}",
        headers=super_admin_headers,
    )
    assert f03.status_code == 200, f03.json()
    assert f03.json()["data"]["بخش ج: گزارش طبقات"]

    printable = client.get(
        f"/pilots/{pilot['id']}/forms/f03/{mission_id}/print",
        headers=super_admin_headers,
    )
    assert printable.status_code == 200
    assert "text/html" in printable.headers["content-type"]
    assert "مأموریت، برداشت و بارگذاری" in printable.text
    assert "@media print" in printable.text

    assert record_counts() == before


def test_f02_print_includes_referral_date_time(client, super_admin_headers):
    pilot, _ = prepare_pilot_through_g2(client, super_admin_headers)

    update = client.put(
        f"/pilots/{pilot['id']}/forms/f02",
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
            "referred_at": "2026-03-21T00:00:00+00:00",
        },
        headers=super_admin_headers,
    )
    assert update.status_code == 200, update.json()
    assert update.json()["referred_at"] is not None

    preview = client.get(
        f"/pilots/{pilot['id']}/forms/f02/preview",
        headers=super_admin_headers,
    )
    assert preview.status_code == 200, preview.json()
    control_section = preview.json()["data"]["بخش ج: کنترل راه‌اندازی در سامانه"]
    assert control_section["تاریخ و ساعت ارجاع"]
    assert "ارجاع به هماهنگ‌کننده عملیات" not in control_section

    printable = client.get(
        f"/pilots/{pilot['id']}/forms/f02/print",
        headers=super_admin_headers,
    )
    assert printable.status_code == 200
    assert "تاریخ و ساعت ارجاع" in printable.text


def test_form_endpoints_require_permissions(client):
    response = client.get("/pilots/1/forms")
    assert response.status_code in {401, 403}
