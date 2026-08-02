"""Read-only official BAMBO form document contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


FormCode = Literal["F01", "F02", "F03", "F04", "F05"]


class FormMissingField(BaseModel):
    field: str
    label: str


class FormFieldMapping(BaseModel):
    form: FormCode
    section: str
    field: str
    source_model: str
    source_field: str
    source_stage: str | None = None
    transformation: str
    missing_data_policy: str


class FormInstanceSummary(BaseModel):
    id: int | None = None
    code: str | None = None
    title: str
    is_complete: bool
    last_changed: datetime | None = None
    href: str | None = None
    print_href: str | None = None
    pdf_href: str | None = None


class FormSummary(BaseModel):
    form_code: FormCode
    document_code: str
    title: str
    version: str = "1.0"
    status_label: str
    is_complete: bool
    printable_count: int
    last_changed: datetime | None = None
    instances: list[FormInstanceSummary] = Field(default_factory=list)
    missing_fields: list[FormMissingField] = Field(default_factory=list)


class FormDocument(BaseModel):
    form_code: FormCode
    document_code: str
    version: str = "1.0"
    title: str
    pilot_id: int
    pilot_code: str
    is_complete: bool
    missing_fields: list[FormMissingField] = Field(default_factory=list)
    mapping: list[FormFieldMapping] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
