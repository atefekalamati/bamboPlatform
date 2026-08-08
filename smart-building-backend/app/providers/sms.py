"""Shared SMS transport adapter for OTP and operational notifications."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import get_app_env, get_bool_setting


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
    def send_otp(self, *, mobile: str, purpose: str, body: str) -> SmsSendResult:
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
    provider = "console"

    def send_otp(self, *, mobile: str, purpose: str, body: str) -> SmsSendResult:
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

    def send_otp(self, *, mobile: str, purpose: str, body: str) -> SmsSendResult:
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
        self.timeout = float(os.getenv("SMS_TIMEOUT_SECONDS", "10"))

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

    def send_otp(self, *, mobile: str, purpose: str, body: str) -> SmsSendResult:
        return self._send(mobile=mobile, body=body, kind="otp", reference=purpose)

    def send_notification(self, *, mobile: str, template_code: str, body: str) -> SmsSendResult:
        return self._send(mobile=mobile, body=body, kind="notification", reference=template_code)

    def get_delivery_status(self, *, provider_message_id: str) -> SmsSendResult:
        return SmsSendResult(False, self.provider, "status_not_supported", provider_message_id)


def get_sms_provider() -> SmsProvider:
    if not get_bool_setting("SMS_ENABLED", True):
        return UnconfiguredSmsProvider()
    if get_app_env() in {"development", "test"}:
        return FakeSmsProvider()
    if os.getenv("SMS_PROVIDER", "").strip().lower() == "http_json":
        try:
            return HttpJsonSmsProvider()
        except KeyError:
            return UnconfiguredSmsProvider()
    return UnconfiguredSmsProvider()
