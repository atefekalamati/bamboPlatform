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
        trace_id = str(uuid4())
        return {
            "code": self.code,
            "message": self.message,
            "stage": self.stage,
            "errors": self.errors,
            "trace_id": trace_id,
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "stage": self.stage,
                "details": self.errors,
                "request_id": trace_id,
            },
        }


@dataclass
class SecurityError(Exception):
    code: str
    message: str
    status_code: int
    errors: list[dict[str, Any]]
    retry_after: int | None = None

    def response_body(self) -> dict[str, Any]:
        trace_id = str(uuid4())
        body = {
            "code": self.code,
            "message": self.message,
            "errors": self.errors,
            "trace_id": trace_id,
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.errors,
                "request_id": trace_id,
            },
        }
        if self.retry_after is not None:
            body["retry_after"] = self.retry_after
        return body
