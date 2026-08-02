"""Read-only official form preview, print, and export APIs."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import SecurityError
from app.schemas.forms import FormDocument, FormSummary
from app.services.form_documents import (
    form_filename,
    get_document,
    list_forms,
    render_form_html,
)
from app.services.security import AuthContext, require_permission

router = APIRouter(tags=["official-forms"])


@router.get("/pilots/{pilot_id}/forms", response_model=list[FormSummary])
def list_pilot_forms(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.read")),
    db: Session = Depends(get_db),
) -> list[FormSummary]:
    return list_forms(db, pilot_id)


@router.get("/pilots/{pilot_id}/forms/f01/preview", response_model=FormDocument)
def preview_f01(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.f01.read")),
    db: Session = Depends(get_db),
) -> FormDocument:
    return get_document(db, pilot_id, "F01")


@router.get("/pilots/{pilot_id}/forms/f02/preview", response_model=FormDocument)
def preview_f02(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.f02.read")),
    db: Session = Depends(get_db),
) -> FormDocument:
    return get_document(db, pilot_id, "F02")


@router.get("/pilots/{pilot_id}/forms/f03/{mission_id}", response_model=FormDocument)
def preview_f03(
    pilot_id: int,
    mission_id: int,
    _: AuthContext = Depends(require_permission("forms.f03.read")),
    db: Session = Depends(get_db),
) -> FormDocument:
    return get_document(db, pilot_id, "F03", mission_id)


@router.get("/pilots/{pilot_id}/forms/f04/preview", response_model=FormDocument)
def preview_f04(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.f04.read")),
    db: Session = Depends(get_db),
) -> FormDocument:
    return get_document(db, pilot_id, "F04")


@router.get("/pilots/{pilot_id}/forms/f05", response_model=list[FormDocument])
def preview_f05_list(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.f05.read")),
    db: Session = Depends(get_db),
) -> list[FormDocument]:
    return [
        get_document(db, pilot_id, "F05", summary.id)
        for summary in list_forms(db, pilot_id)[-1].instances
        if summary.id is not None
    ]


@router.get("/pilots/{pilot_id}/forms/f05/{incident_id}", response_model=FormDocument)
def preview_f05(
    pilot_id: int,
    incident_id: int,
    _: AuthContext = Depends(require_permission("forms.f05.read")),
    db: Session = Depends(get_db),
) -> FormDocument:
    return get_document(db, pilot_id, "F05", incident_id)


@router.get("/pilots/{pilot_id}/forms/f01/print", response_class=HTMLResponse)
def print_f01(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.print")),
    db: Session = Depends(get_db),
) -> str:
    return render_form_html(get_document(db, pilot_id, "F01"), print_mode=True)


@router.get("/pilots/{pilot_id}/forms/f02/print", response_class=HTMLResponse)
def print_f02(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.print")),
    db: Session = Depends(get_db),
) -> str:
    return render_form_html(get_document(db, pilot_id, "F02"), print_mode=True)


@router.get("/pilots/{pilot_id}/forms/f03/{mission_id}/print", response_class=HTMLResponse)
def print_f03(
    pilot_id: int,
    mission_id: int,
    _: AuthContext = Depends(require_permission("forms.print")),
    db: Session = Depends(get_db),
) -> str:
    return render_form_html(get_document(db, pilot_id, "F03", mission_id), print_mode=True)


@router.get("/pilots/{pilot_id}/forms/f04/print", response_class=HTMLResponse)
def print_f04(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.print")),
    db: Session = Depends(get_db),
) -> str:
    return render_form_html(get_document(db, pilot_id, "F04"), print_mode=True)


@router.get("/pilots/{pilot_id}/forms/f05/{incident_id}/print", response_class=HTMLResponse)
def print_f05(
    pilot_id: int,
    incident_id: int,
    _: AuthContext = Depends(require_permission("forms.print")),
    db: Session = Depends(get_db),
) -> str:
    return render_form_html(get_document(db, pilot_id, "F05", incident_id), print_mode=True)


def _pdf_response(document: FormDocument) -> Response:
    try:
        from weasyprint import HTML
    except ModuleNotFoundError as exc:
        raise SecurityError(
            "PDF_RENDERER_UNAVAILABLE",
            "تولید PDF نیازمند نصب WeasyPrint در محیط اجرا است.",
            503,
            [],
        ) from exc
    html = render_form_html(document, print_mode=True)
    pdf_bytes = HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{form_filename(document, ".pdf")}"'},
    )


@router.get("/pilots/{pilot_id}/forms/f01/pdf")
def pdf_f01(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.export_pdf")),
    db: Session = Depends(get_db),
) -> Response:
    return _pdf_response(get_document(db, pilot_id, "F01"))


@router.get("/pilots/{pilot_id}/forms/f02/pdf")
def pdf_f02(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.export_pdf")),
    db: Session = Depends(get_db),
) -> Response:
    return _pdf_response(get_document(db, pilot_id, "F02"))


@router.get("/pilots/{pilot_id}/forms/f03/{mission_id}/pdf")
def pdf_f03(
    pilot_id: int,
    mission_id: int,
    _: AuthContext = Depends(require_permission("forms.export_pdf")),
    db: Session = Depends(get_db),
) -> Response:
    return _pdf_response(get_document(db, pilot_id, "F03", mission_id))


@router.get("/pilots/{pilot_id}/forms/f04/pdf")
def pdf_f04(
    pilot_id: int,
    _: AuthContext = Depends(require_permission("forms.export_pdf")),
    db: Session = Depends(get_db),
) -> Response:
    return _pdf_response(get_document(db, pilot_id, "F04"))


@router.get("/pilots/{pilot_id}/forms/f05/{incident_id}/pdf")
def pdf_f05(
    pilot_id: int,
    incident_id: int,
    _: AuthContext = Depends(require_permission("forms.export_pdf")),
    db: Session = Depends(get_db),
) -> Response:
    return _pdf_response(get_document(db, pilot_id, "F05", incident_id))
