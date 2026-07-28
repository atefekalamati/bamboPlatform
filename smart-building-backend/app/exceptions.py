"""Domain error contracts returned by the BAMBO API."""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass
class WorkflowError(Exception):
    code: str
    message: str
    stage: int | None
    status_code: int
    errors: list[dict[str, Any]]

    def response_body(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "stage": self.stage,
            "errors": self.errors,
            "trace_id": str(uuid4()),
        }


@dataclass
class SecurityError(Exception):
    code: str
    message: str
    status_code: int
    errors: list[dict[str, Any]]
    retry_after: int | None = None

    def response_body(self) -> dict[str, Any]:
        body = {
            "code": self.code,
            "message": self.message,
            "errors": self.errors,
            "trace_id": str(uuid4()),
        }
        if self.retry_after is not None:
            body["retry_after"] = self.retry_after
        return body
