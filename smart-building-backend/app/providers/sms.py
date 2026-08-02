"""Shared SMS transport adapter for OTP and operational notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from app.config import get_app_env


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


def get_sms_provider() -> SmsProvider:
    if get_app_env() in {"development", "test"}:
        return FakeSmsProvider()
    return UnconfiguredSmsProvider()
