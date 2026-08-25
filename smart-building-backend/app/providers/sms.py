"""Shared SMS transport adapter for OTP and operational notifications."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import (
    get_app_env,
    get_bool_setting,
    get_sms_notification_param_name,
    get_sms_notification_template_id,
    get_sms_otp_param_name,
    get_sms_otp_template_id,
    get_sms_retry_count,
    get_sms_retry_backoff_seconds,
    get_sms_timeout_seconds,
)

OTP_MESSAGE_TEMPLATE = "کد ورود BAMBO: {code}"


def build_otp_message(otp_code: str) -> str:
    """Free-text body used by text-mode providers; pattern providers use params."""
    return OTP_MESSAGE_TEMPLATE.format(code=otp_code)


@dataclass(frozen=True)
class SmsSendResult:
    accepted: bool
    provider: str
    provider_status: str
    provider_message_id: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    retryable: bool = False


class SmsProvider(Protocol):
    def send_otp(
        self,
        *,
        mobile: str,
        otp_code: str,
        template_id: str | None = None,
    ) -> SmsSendResult:
        ...

    def send_notification(
        self,
        *,
        mobile: str,
        template_code: str,
        body: str,
    ) -> SmsSendResult:
        ...

    def get_delivery_status(self, *, provider_message_id: str) -> SmsSendResult:
        ...


class FakeSmsProvider:
    """Development/test transport. Never selected when APP_ENV is production."""

    provider = "console"

    def send_otp(
        self,
        *,
        mobile: str,
        otp_code: str,
        template_id: str | None = None,
    ) -> SmsSendResult:
        return SmsSendResult(
            accepted=True,
            provider=self.provider,
            provider_status="accepted:console",
            provider_message_id=f"otp-{uuid4()}",
        )

    def send_notification(
        self,
        *,
        mobile: str,
        template_code: str,
        body: str,
    ) -> SmsSendResult:
        return SmsSendResult(
            accepted=True,
            provider=self.provider,
            provider_status="accepted:console",
            provider_message_id=f"notification-{uuid4()}",
        )

    def get_delivery_status(self, *, provider_message_id: str) -> SmsSendResult:
        return SmsSendResult(
            accepted=True,
            provider=self.provider,
            provider_status="delivered:console",
            provider_message_id=provider_message_id,
        )


class UnconfiguredSmsProvider:
    provider = "unconfigured"

    def send_otp(
        self,
        *,
        mobile: str,
        otp_code: str,
        template_id: str | None = None,
    ) -> SmsSendResult:
        return self._failed()

    def send_notification(
        self,
        *,
        mobile: str,
        template_code: str,
        body: str,
    ) -> SmsSendResult:
        return self._failed()

    def get_delivery_status(self, *, provider_message_id: str) -> SmsSendResult:
        return self._failed()

    def _failed(self) -> SmsSendResult:
        return SmsSendResult(
            accepted=False,
            provider=self.provider,
            provider_status="unconfigured",
            failure_code="SMS_PROVIDER_UNAVAILABLE",
            failure_reason="SMS provider is not configured",
            retryable=True,
        )


class HttpJsonSmsProvider:
    """Provider-neutral HTTPS JSON adapter; credentials never leave the backend."""

    provider = "http_json"

    def __init__(self) -> None:
        self.url = os.environ["SMS_API_URL"]
        self.api_key = os.environ["SMS_API_KEY"]
        self.sender = os.environ["SMS_SENDER"]
        self.timeout = get_sms_timeout_seconds()

    def _send(self, *, mobile: str, body: str, kind: str, reference: str) -> SmsSendResult:
        payload = json.dumps({
            "to": mobile,
            "from": self.sender,
            "message": body,
            "type": kind,
            "reference": reference,
        }).encode("utf-8")
        request = Request(
            self.url,
            data=payload,
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - HTTPS validated by readiness
                data = json.loads(response.read().decode("utf-8") or "{}")
            message_id = data.get("message_id") or data.get("id")
            accepted = data.get("accepted", True) is not False and bool(message_id)
            return SmsSendResult(
                accepted=accepted,
                provider=self.provider,
                provider_status=str(data.get("status") or ("accepted" if accepted else "rejected"))[:80],
                provider_message_id=str(message_id) if message_id else None,
                failure_code=None if accepted else "SMS_REJECTED",
                retryable=False,
            )
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            return SmsSendResult(
                accepted=False,
                provider=self.provider,
                provider_status="transport_error",
                failure_code="SMS_TRANSPORT_ERROR",
                failure_reason="SMS transport request failed",
                retryable=True,
            )

    def send_otp(
        self,
        *,
        mobile: str,
        otp_code: str,
        template_id: str | None = None,
    ) -> SmsSendResult:
        return self._send(
            mobile=mobile,
            body=build_otp_message(otp_code),
            kind="otp",
            reference="auth",
        )

    def send_notification(self, *, mobile: str, template_code: str, body: str) -> SmsSendResult:
        return self._send(mobile=mobile, body=body, kind="notification", reference=template_code)

    def get_delivery_status(self, *, provider_message_id: str) -> SmsSendResult:
        return SmsSendResult(False, self.provider, "status_not_supported", provider_message_id)


class IpPanelSmsProvider:
    """IPPanel Edge pattern adapter.

    Contract: POST {base}/api/send with sending_type=pattern. The pattern id goes
    in the root ``code`` field and the pattern's own variables go in ``params``.
    Success is ``meta.status is true``; the outbox id lives in
    ``data.message_outbox_ids[0]``. A 2xx alone is NOT success — IPPanel returns
    200 with ``meta.status: false`` for an exhausted balance or a disabled
    pattern, so acceptance is always read from the body.

    Reference: https://ippanelcom.github.io/Edge-Document/docs/send/pattern
    """

    provider = "ippanel"

    def __init__(self) -> None:
        base_url = os.getenv("SMS_BASE_URL", "https://edge.ippanel.com/v1").rstrip("/")
        self.url = os.getenv("SMS_API_URL", f"{base_url}/api/send")
        self.api_token = os.environ["SMS_API_KEY"]
        self.sender = os.environ["SMS_SENDER"]
        self.otp_pattern_code = get_sms_otp_template_id()
        self.notification_pattern_code = get_sms_notification_template_id()
        self.otp_param_name = get_sms_otp_param_name()
        self.notification_param_name = get_sms_notification_param_name()
        self.timeout = get_sms_timeout_seconds()
        self.retry_count = get_sms_retry_count()
        self.retry_backoff = get_sms_retry_backoff_seconds()
        if not self.otp_pattern_code:
            raise KeyError("SMS_OTP_TEMPLATE_ID")
        if not self.notification_pattern_code:
            raise KeyError("SMS_NOTIFICATION_TEMPLATE_ID")

    # ---------------------------------------------------------------- helpers

    def _build_payload(self, *, mobile: str, pattern_code: str, params: dict[str, str]) -> bytes:
        return json.dumps(
            {
                "sending_type": "pattern",
                "from_number": self.sender,
                "code": pattern_code,
                "recipients": [mobile],
                "params": params,
            },
            ensure_ascii=False,
        ).encode("utf-8")

    @staticmethod
    def _extract_outbox_id(data: Any) -> str | None:
        if not isinstance(data, dict):
            return None
        ids = data.get("message_outbox_ids")
        if isinstance(ids, list) and ids:
            return str(ids[0])
        # Tolerate documented singular variants without inventing new ones.
        for key in ("message_id", "bulk_id"):
            value = data.get(key)
            if value not in (None, ""):
                return str(value)
        return None

    def _interpret(self, *, http_status: int, raw_body: str) -> SmsSendResult:
        try:
            body = json.loads(raw_body or "{}")
        except ValueError:
            return SmsSendResult(
                accepted=False,
                provider=self.provider,
                provider_status=f"unparsable_response:http_{http_status}",
                failure_code="SMS_PROVIDER_ERROR",
                failure_reason="SMS provider returned a non-JSON response",
                retryable=True,
            )

        meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
        message_code = str(meta.get("message_code") or f"http_{http_status}")[:80]
        outbox_id = self._extract_outbox_id(body.get("data"))

        # Acceptance requires BOTH an explicit meta.status of true and an id.
        accepted = meta.get("status") is True and outbox_id is not None
        if accepted:
            return SmsSendResult(
                accepted=True,
                provider=self.provider,
                provider_status=f"accepted:{message_code}",
                provider_message_id=outbox_id,
            )

        if meta.get("status") is True and outbox_id is None:
            return SmsSendResult(
                accepted=False,
                provider=self.provider,
                provider_status=f"missing_outbox_id:{message_code}",
                failure_code="SMS_PROVIDER_ERROR",
                failure_reason="SMS provider accepted the request without an outbox id",
                retryable=True,
            )

        retryable = http_status >= 500
        return SmsSendResult(
            accepted=False,
            provider=self.provider,
            provider_status=f"rejected:{message_code}",
            failure_code="SMS_PROVIDER_ERROR" if retryable else "SMS_REJECTED",
            # meta.message is provider-authored Persian text; safe to surface.
            failure_reason=str(meta.get("message") or "SMS provider rejected the request")[:200],
            retryable=retryable,
        )

    def _post_once(self, payload: bytes) -> SmsSendResult:
        request = Request(
            self.url,
            data=payload,
            method="POST",
            headers={
                "Authorization": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - HTTPS validated by readiness
                return self._interpret(
                    http_status=response.status,
                    raw_body=response.read().decode("utf-8", errors="replace"),
                )
        except HTTPError as exc:
            # IPPanel returns a structured body on 4xx/5xx too; read it.
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - body is best-effort diagnostics
                raw = ""
            return self._interpret(http_status=exc.code, raw_body=raw)
        except (URLError, TimeoutError, OSError):
            return SmsSendResult(
                accepted=False,
                provider=self.provider,
                provider_status="transport_error",
                failure_code="SMS_TRANSPORT_ERROR",
                failure_reason="SMS transport request failed",
                retryable=True,
            )

    def _send_pattern(self, *, mobile: str, pattern_code: str, params: dict[str, str]) -> SmsSendResult:
        payload = self._build_payload(mobile=mobile, pattern_code=pattern_code, params=params)
        result = self._post_once(payload)
        for attempt in range(self.retry_count):
            if result.accepted or not result.retryable:
                return result
            if self.retry_backoff:
                time.sleep(self.retry_backoff * (2**attempt))
            result = self._post_once(payload)
        return result

    # ------------------------------------------------------------------- API

    def send_otp(
        self,
        *,
        mobile: str,
        otp_code: str,
        template_id: str | None = None,
    ) -> SmsSendResult:
        if not otp_code:
            raise ValueError("otp_code is required to send an OTP pattern message")
        return self._send_pattern(
            mobile=mobile,
            pattern_code=template_id or self.otp_pattern_code,
            params={self.otp_param_name: otp_code},
        )

    def send_notification(self, *, mobile: str, template_code: str, body: str) -> SmsSendResult:
        return self._send_pattern(
            mobile=mobile,
            pattern_code=self.notification_pattern_code,
            params={self.notification_param_name: body},
        )

    def get_delivery_status(self, *, provider_message_id: str) -> SmsSendResult:
        # The Edge status endpoint contract is not installed; never fake a status.
        return SmsSendResult(False, self.provider, "status_not_supported", provider_message_id)


def get_sms_provider() -> SmsProvider:
    if not get_bool_setting("SMS_ENABLED", True):
        return UnconfiguredSmsProvider()
    if get_app_env() in {"development", "test"}:
        return FakeSmsProvider()
    sms_provider = os.getenv("SMS_PROVIDER", "").strip().lower()
    if sms_provider == "http_json":
        try:
            return HttpJsonSmsProvider()
        except KeyError:
            return UnconfiguredSmsProvider()
    if sms_provider == "ippanel":
        try:
            return IpPanelSmsProvider()
        except KeyError:
            return UnconfiguredSmsProvider()
    return UnconfiguredSmsProvider()
