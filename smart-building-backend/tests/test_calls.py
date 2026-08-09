import hashlib
import hmac
import json

from app.database import get_session
from app.models import Call, CallWebhookEvent
from app.services.calls import map_provider_status, mask_phone, stage_call_policy
from conftest import login_with_otp, sample_pilot_payload, save_valid_f01, submit_and_approve_stage


def prepare_stage_two(client, headers):
    pilot = client.post("/pilots", json=sample_pilot_payload(), headers=headers).json()
    save_valid_f01(client, pilot["id"], headers)
    submit_and_approve_stage(client, pilot["id"], 1, headers)
    return pilot


def sign(body: bytes, secret: str = "test-call-webhook-secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_phone_mask_and_stage_policy():
    assert mask_phone("+989151111111") == "+989***1111"
    assert stage_call_policy(18).required is True
    assert stage_call_policy(1).enabled is False
    assert map_provider_status("mock", "RINGING") == "ringing"


def test_mock_call_idempotency_webhook_outcome_and_audit(client, super_admin_headers):
    pilot = prepare_stage_two(client, super_admin_headers)
    payload = {"idempotency_key": "stage2-call-0001"}
    created = client.post(f"/api/v1/pilots/{pilot['id']}/stages/2/calls", json=payload, headers=super_admin_headers)
    assert created.status_code == 201, created.text
    call = created.json()
    assert call["destination_masked"] == "+989***1111"
    assert "destination_phone" not in call
    assert call["technical_status"] == "initiating"

    repeated = client.post(f"/api/v1/pilots/{pilot['id']}/stages/2/calls", json=payload, headers=super_admin_headers)
    assert repeated.status_code == 201
    assert repeated.json()["public_id"] == call["public_id"]
    with get_session() as db:
        stored = db.query(Call).filter(Call.public_id == call["public_id"]).one()
        provider_call_id = stored.attempts[0].provider_call_id

    webhook_payload = {
        "event_id": "event-answered-1", "provider_call_id": provider_call_id,
        "event_type": "call.status", "status": "answered", "duration_seconds": 12,
    }
    body = json.dumps(webhook_payload, separators=(",", ":")).encode()
    webhook = client.post("/api/v1/integrations/astel/webhooks", content=body,
                          headers={"Content-Type": "application/json", "X-Call-Signature": sign(body)})
    assert webhook.status_code == 200, webhook.text
    duplicate = client.post("/api/v1/integrations/astel/webhooks", content=body,
                            headers={"Content-Type": "application/json", "X-Call-Signature": sign(body)})
    assert duplicate.json()["duplicate"] is True
    with get_session() as db:
        assert db.query(CallWebhookEvent).count() == 1

    outcome = client.patch(f"/api/v1/calls/{call['public_id']}/outcome",
                           json={"outcome": "customer_confirmed", "summary": "Customer confirmed the next step."},
                           headers=super_admin_headers)
    assert outcome.status_code == 200, outcome.text
    assert outcome.json()["business_outcome"] == "customer_confirmed"
    details = client.get(f"/api/v1/calls/{call['public_id']}", headers=super_admin_headers)
    assert details.status_code == 200
    assert "destination_phone" not in details.json()


def test_invalid_webhook_and_outcome_rules(client, super_admin_headers):
    pilot = prepare_stage_two(client, super_admin_headers)
    call = client.post(f"/api/v1/pilots/{pilot['id']}/stages/2/calls",
                       json={"idempotency_key": "stage2-call-0002"}, headers=super_admin_headers).json()
    premature = client.patch(f"/api/v1/calls/{call['public_id']}/outcome",
                             json={"outcome": "customer_confirmed", "summary": "Confirmed."}, headers=super_admin_headers)
    assert premature.status_code == 409
    invalid_override = client.post(
        f"/api/v1/calls/{call['public_id']}/override",
        json={"reason": "short"},
        headers=super_admin_headers,
    )
    assert invalid_override.status_code == 422
    invalid = client.post("/api/v1/integrations/astel/webhooks",
                          json={"event_id": "bad", "provider_call_id": "none", "event_type": "x", "status": "failed"},
                          headers={"X-Call-Signature": "invalid"})
    assert invalid.status_code == 401
    missing_next_action = client.patch(f"/api/v1/calls/{call['public_id']}/outcome",
                                       json={"outcome": "callback_requested", "summary": "Call back later."},
                                       headers=super_admin_headers)
    assert missing_next_action.status_code == 422


def test_role_without_call_permission_is_denied(client, super_admin_headers):
    pilot = prepare_stage_two(client, super_admin_headers)
    role = next(item for item in client.get("/roles", headers=super_admin_headers).json() if item["name"] == "capture_expert")
    assert client.post("/users", json={"mobile": "09158889999", "display_name": "Field", "role_ids": [role["id"]]}, headers=super_admin_headers).status_code == 201
    headers = login_with_otp(client, "09158889999")
    response = client.post(f"/api/v1/pilots/{pilot['id']}/stages/2/calls",
                           json={"idempotency_key": "stage2-call-0003"}, headers=headers)
    assert response.status_code == 403


def test_no_answer_retry_and_out_of_order_webhook(client, super_admin_headers):
    pilot = prepare_stage_two(client, super_admin_headers)
    call = client.post(f"/api/v1/pilots/{pilot['id']}/stages/2/calls",
                       json={"idempotency_key": "stage2-call-retry"}, headers=super_admin_headers).json()
    with get_session() as db:
        provider_call_id = db.query(Call).filter(Call.public_id == call["public_id"]).one().attempts[0].provider_call_id
    first = {"event_id": "event-no-answer", "provider_call_id": provider_call_id,
             "event_type": "call.status", "status": "no_answer"}
    body = json.dumps(first, separators=(",", ":")).encode()
    assert client.post("/api/v1/integrations/astel/webhooks", content=body,
                       headers={"Content-Type": "application/json", "X-Call-Signature": sign(body)}).status_code == 200
    stale = first | {"event_id": "event-stale-ringing", "status": "ringing"}
    stale_body = json.dumps(stale, separators=(",", ":")).encode()
    assert client.post("/api/v1/integrations/astel/webhooks", content=stale_body,
                       headers={"Content-Type": "application/json", "X-Call-Signature": sign(stale_body)}).status_code == 200
    assert client.get(f"/api/v1/calls/{call['public_id']}", headers=super_admin_headers).json()["technical_status"] == "no_answer"
    retried = client.post(f"/api/v1/calls/{call['public_id']}/retry", headers=super_admin_headers)
    assert retried.status_code == 200
    assert len(retried.json()["attempts"]) == 2


def test_astel_without_official_contract_fails_closed(client, super_admin_headers, monkeypatch):
    pilot = prepare_stage_two(client, super_admin_headers)
    monkeypatch.setenv("CALL_PROVIDER", "astel")
    response = client.post(f"/api/v1/pilots/{pilot['id']}/stages/2/calls",
                           json={"idempotency_key": "stage2-astel-unconfigured"}, headers=super_admin_headers)
    assert response.status_code == 503
    assert response.json()["code"] == "CALL_PROVIDER_UNAVAILABLE"
    assert "ASTEL_API_KEY" not in response.text
