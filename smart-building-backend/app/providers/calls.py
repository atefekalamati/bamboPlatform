"""Call provider boundary. Astel stays disabled until its private contract is supplied."""

from dataclasses import dataclass
import os
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class CallProviderResult:
    accepted: bool
    provider: str
    status: str
    provider_call_id: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    retryable: bool = False


class CallProvider(Protocol):
    name: str

    def initiate(self, *, destination: str, callback_url: str | None, recording: bool) -> CallProviderResult: ...


class MockCallProvider:
    name = "mock"

    def initiate(self, *, destination: str, callback_url: str | None, recording: bool) -> CallProviderResult:
        return CallProviderResult(True, self.name, "initiating", f"mock-{uuid4()}")


class AstelProvider:
    """Fail-closed adapter placeholder; no undocumented Astel request is emitted."""

    name = "astel"

    def initiate(self, *, destination: str, callback_url: str | None, recording: bool) -> CallProviderResult:
        return CallProviderResult(
            False,
            self.name,
            "failed",
            failure_code="ASTEL_CONTRACT_NOT_CONFIGURED",
            failure_reason="Official Astel API contract is not installed",
            retryable=False,
        )


def get_call_provider() -> CallProvider:
    provider = os.getenv("CALL_PROVIDER", "mock").strip().lower()
    if provider == "mock" and os.getenv("APP_ENV", "development").lower() != "production":
        return MockCallProvider()
    if provider == "astel":
        return AstelProvider()
    return AstelProvider()
