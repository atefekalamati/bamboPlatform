from conftest import BOOTSTRAP_MOBILE, login_with_otp, prepare_pilot_through_g2
from app.database import get_session
from app.models import User
from app.services.notifications import (
    PLATFORM_CONTRACT_REVIEW_TEMPLATE,
    build_in_app_action_required_sms,
    build_platform_contract_review_sms,
    create_notification,
)


def test_ippanel_provider_sends_pattern_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return (
                b'{"meta":{"status":true,"message_code":"200"},'
                b'"data":{"message_outbox_ids":["ippanel-message-1"]}}'
            )

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        import json

        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setenv("SMS_PROVIDER", "ippanel")
    monkeypatch.setenv("SMS_BASE_URL", "https://edge.ippanel.com/v1")
    monkeypatch.setenv("SMS_API_KEY", "secret-token")
    monkeypatch.setenv("SMS_SENDER", "+983000505")
    monkeypatch.setenv("SMS_TEMPLATE_ID", "spuueljew7dxi3z")
    monkeypatch.setenv("SMS_TIMEOUT_SECONDS", "7")
    monkeypatch.setattr("app.providers.sms.urlopen", fake_urlopen)

    from app.providers.sms import get_sms_provider

    result = get_sms_provider().send_notification(
        mobile="+989120000000",
        template_code="mission_created",
        body="ignored by IPPanel pattern adapter",
    )

    assert result.accepted is True
    assert result.provider == "ippanel"
    assert result.provider_message_id == "ippanel-message-1"
    assert captured["url"] == "https://edge.ippanel.com/v1/api/send"
    assert captured["timeout"] == 7
    assert captured["headers"]["Authorization"] == "secret-token"
    assert captured["payload"] == {
        "sending_type": "pattern",
        "from_number": "+983000505",
        "code": "spuueljew7dxi3z",
        "recipients": ["+989120000000"],
        "params": {"message": "ignored by IPPanel pattern adapter"},
    }


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


def test_in_app_action_required_sms_text_is_uniform_and_uses_env_link(
    client,
    monkeypatch,
):
    monkeypatch.setenv("PLATFORM_LOGIN_URL", "https://pilot.example.invalid/login")
    message = build_in_app_action_required_sms()

    assert message == (
        "یادآوری بامبو:\n"
        "لطفاً اعلان جدید سامانه را بررسی کرده و اقدام الزامی خود را انجام دهید.\n"
        "https://pilot.example.invalid/login"
    )
    assert "0915" not in message
    assert "PIL-" not in message
    assert "توکن" not in message


def test_contract_review_sms_uses_normalized_user_mobile_and_template(
    client,
    monkeypatch,
):
    sent = {}

    class RecordingProvider:
        def send_notification(self, *, mobile, template_code, body):
            sent.update(mobile=mobile, template_code=template_code, body=body)
            from app.providers.sms import SmsSendResult

            return SmsSendResult(
                accepted=True,
                provider="recording",
                provider_status="accepted",
                provider_message_id="sms-1",
            )

    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setenv("PLATFORM_LOGIN_URL", "https://pilot.example.invalid/login")
    monkeypatch.setattr("app.services.notifications.get_sms_provider", lambda: RecordingProvider())

    db = get_session()
    try:
        user = User(mobile="09157778888", display_name="Contract Reviewer")
        db.add(user)
        db.flush()
        notification = create_notification(
            db,
            recipient_user=user,
            notification_type="commercial.followup_due",
            category="COMMERCIAL",
            priority="NORMAL",
            title="یادآوری بررسی قرارداد پلتفرم",
            body="پیگیری پیشنهاد تجاری پرونده PIL-1405-001 باید انجام شود.",
            short_body=build_platform_contract_review_sms(),
            template_code=PLATFORM_CONTRACT_REVIEW_TEMPLATE,
            deduplication_key="contract-review:test",
        )
        db.commit()

        assert sent["mobile"] == "+989157778888"
        assert sent["template_code"] == PLATFORM_CONTRACT_REVIEW_TEMPLATE
        assert sent["body"] == build_in_app_action_required_sms()
        assert "Contract Reviewer" not in sent["body"]
        assert "PIL-1405-001" not in sent["body"]
        sms_delivery = next(item for item in notification.deliveries if item.channel == "SMS")
        assert sms_delivery.status == "DELIVERED"
        assert sms_delivery.provider_message_id == "sms-1"
    finally:
        db.close()


def test_invalid_contract_review_mobile_is_not_sent_to_provider(client, monkeypatch):
    calls = {"count": 0}

    class RecordingProvider:
        def send_notification(self, *, mobile, template_code, body):
            calls["count"] += 1
            raise AssertionError("provider must not be called for invalid mobile")

    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setattr("app.services.notifications.get_sms_provider", lambda: RecordingProvider())

    db = get_session()
    try:
        user = User(mobile="invalid-mobile", display_name="Invalid Mobile")
        db.add(user)
        db.flush()
        notification = create_notification(
            db,
            recipient_user=user,
            notification_type="commercial.followup_due",
            category="COMMERCIAL",
            priority="NORMAL",
            title="یادآوری بررسی قرارداد پلتفرم",
            body="In-app body",
            short_body=build_platform_contract_review_sms(),
            template_code=PLATFORM_CONTRACT_REVIEW_TEMPLATE,
        )
        db.commit()

        assert calls["count"] == 0
        sms_delivery = next(item for item in notification.deliveries if item.channel == "SMS")
        assert sms_delivery.status == "FAILED"
        assert sms_delivery.failure_code == "SMS_RECIPIENT_INVALID"
    finally:
        db.close()


def test_sms_enabled_false_skips_provider_without_leaking_api_key(
    client,
    super_admin_headers,
    monkeypatch,
):
    monkeypatch.setenv("SMS_ENABLED", "false")
    monkeypatch.setenv("SMS_API_KEY", "super-secret-api-key")

    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    expert = create_capture_expert(client, super_admin_headers, "09156660001")
    mission = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201, mission.json()

    logs = client.get("/notifications/delivery-logs", headers=super_admin_headers)
    assert logs.status_code == 200, logs.json()
    sms_log = next(item for item in logs.json() if item["channel"] == "SMS")
    assert sms_log["status"] == "SKIPPED"
    assert sms_log["failure_code"] == "SMS_PROVIDER_DISABLED"
    assert "super-secret-api-key" not in str(logs.json())


def test_mission_in_app_notification_sends_generic_action_required_sms(
    client,
    super_admin_headers,
    monkeypatch,
):
    sent = {}

    class RecordingProvider:
        def send_notification(self, *, mobile, template_code, body):
            sent.update(mobile=mobile, template_code=template_code, body=body)
            from app.providers.sms import SmsSendResult

            return SmsSendResult(
                accepted=True,
                provider="recording",
                provider_status="accepted",
                provider_message_id="sms-mission-1",
            )

    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setenv("PLATFORM_LOGIN_URL", "https://pilot.example.invalid/login")
    monkeypatch.setattr("app.services.notifications.get_sms_provider", lambda: RecordingProvider())

    pilot, floors = prepare_pilot_through_g2(client, super_admin_headers)
    expert = create_capture_expert(client, super_admin_headers, "09156660002")
    mission = client.post(
        f"/pilots/{pilot['id']}/missions",
        json=mission_payload(expert["id"], [floor["id"] for floor in floors]),
        headers=super_admin_headers,
    )
    assert mission.status_code == 201, mission.json()

    assert sent["mobile"] == "+989156660002"
    assert sent["template_code"] == "mission_created"
    assert sent["body"] == build_in_app_action_required_sms()
    assert "مأموریت" not in sent["body"]
    assert "PIL-" not in sent["body"]
