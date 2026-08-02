from conftest import BOOTSTRAP_MOBILE, login_with_otp, prepare_pilot_through_g2


def create_capture_expert(client, headers, mobile="09156667777"):
    roles = client.get("/roles", headers=headers).json()
    role_id = next(role["id"] for role in roles if role["name"] == "capture_expert")
    response = client.post(
        "/users",
        json={
            "mobile": mobile,
            "display_name": "کارشناس اعلان",
            "role_ids": [role_id],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return response.json()


def mission_payload(expert_id, floor_ids):
    return {
        "expert_user_id": expert_id,
        "scheduled_start": "2027-02-10T08:00:00+00:00",
        "scheduled_end": "2027-02-10T10:00:00+00:00",
        "floor_ids": floor_ids,
        "location": "مشهد، محل پروژه",
        "site_contact_name": "هماهنگ‌کننده نمونه",
        "site_contact_mobile": "09152222222",
        "limitation": "ورود فقط با هماهنگی",
    }


def test_mission_notification_inbox_delivery_and_mark_read(client, super_admin_headers):
    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    expert = create_capture_expert(client, super_admin_headers)
    expert_headers = login_with_otp(client, "09156667777")

    mission = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201, mission.json()
    legacy_notification = mission.json()["notifications"][0]
    assert legacy_notification["status"] == "delivered"

    inbox = client.get("/notifications", headers=expert_headers)
    assert inbox.status_code == 200, inbox.json()
    assert inbox.json()["total"] == 1
    assert inbox.json()["unread_count"] == 1
    item = inbox.json()["items"][0]
    assert item["type"] == "mission.assigned"
    assert item["category"] == "MISSION"
    assert item["action_url"] == f"/pilots/{pilot['id']}/stages/5"

    create_capture_expert(client, super_admin_headers, "09159990000")
    other_headers = login_with_otp(client, "09159990000")
    other_inbox = client.get("/notifications", headers=other_headers)
    assert other_inbox.status_code == 200
    assert other_inbox.json()["total"] == 0

    count = client.get("/notifications/unread-count", headers=expert_headers)
    assert count.status_code == 200
    assert count.json()["unread_count"] == 1

    read = client.patch(f"/notifications/{item['id']}/read", headers=expert_headers)
    assert read.status_code == 200, read.json()
    assert read.json()["is_read"] is True
    assert client.get("/notifications/unread-count", headers=expert_headers).json()[
        "unread_count"
    ] == 0

    logs = client.get("/notifications/delivery-logs", headers=super_admin_headers)
    assert logs.status_code == 200, logs.json()
    channels = {item["channel"] for item in logs.json()}
    assert {"IN_APP", "SMS"} <= channels
    sms_log = next(item for item in logs.json() if item["channel"] == "SMS")
    assert "***" in sms_log["recipient_address"]


def test_notification_preferences_can_skip_sms_without_losing_in_app(
    client,
    super_admin_headers,
):
    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    expert = create_capture_expert(client, super_admin_headers, "09156668888")
    expert_headers = login_with_otp(client, "09156668888")

    prefs = client.put(
        "/notification-preferences",
        json={
            "in_app_enabled": True,
            "sms_enabled": False,
            "sms_categories": {"MISSION": True},
            "critical_sms_enabled": True,
        },
        headers=expert_headers,
    )
    assert prefs.status_code == 200, prefs.json()
    assert prefs.json()["sms_enabled"] is False

    mission = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201, mission.json()

    inbox = client.get("/notifications", headers=expert_headers)
    assert inbox.status_code == 200
    assert inbox.json()["total"] == 1

    logs = client.get("/notifications/delivery-logs", headers=super_admin_headers)
    sms_log = next(item for item in logs.json() if item["channel"] == "SMS")
    assert sms_log["status"] == "SKIPPED"
    assert sms_log["failure_code"] == "SMS_PREFERENCE_DISABLED"


def test_otp_login_still_uses_separate_flow(client):
    headers = login_with_otp(client, BOOTSTRAP_MOBILE)
    assert client.get("/auth/me", headers=headers).status_code == 200
    notifications = client.get("/notifications", headers=headers)
    assert notifications.status_code == 200
    assert notifications.json()["total"] == 0
