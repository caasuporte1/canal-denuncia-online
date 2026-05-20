from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from starlette.templating import Jinja2Templates

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.session import (
    create_complainant_session,
    destroy_complainant_session,
    get_complainant_session,
    verify_complainant_csrf,
)
from app.models.report import Report
from app.models.report_message import ReportMessage
from app.services.audit import audit_event
from app.services.credential_check import verify_credentials_constant_time
from app.services.ip_policy import get_client_ip

router = APIRouter(prefix="/acompanhar")
templates = Jinja2Templates(directory="app/templates")

STATUS_LABELS = {
    "recebida": "Recebida",
    "em_triagem": "Em triagem",
    "em_apuracao": "Em apuracao",
    "aguardando_resposta": "Aguardando resposta",
    "concluida": "Concluida",
    "arquivada": "Arquivada",
}

CATEGORY_LABELS = {
    "assedio_moral": "Assedio moral",
    "assedio_sexual": "Assedio sexual",
    "discriminacao": "Discriminacao",
    "seguranca_do_trabalho": "Seguranca do trabalho",
    "conduta_etica": "Conduta etica",
    "outros": "Outros",
}


@router.get("", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("acompanhar_login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    protocol: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    protocol_value = protocol.strip().upper()
    login_value = login.strip().upper()
    valid = verify_credentials_constant_time(db, protocol_value, login_value, password)
    if not valid:
        audit_event(
            db,
            "complainant_login_failed",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return templates.TemplateResponse(
            "acompanhar_login.html",
            {"request": request, "error": "Credenciais invalidas"},
            status_code=401,
        )

    report = db.scalar(select(Report).where(Report.protocol == protocol_value, Report.access_login == login_value))
    if not report:
        return templates.TemplateResponse(
            "acompanhar_login.html",
            {"request": request, "error": "Credenciais invalidas"},
            status_code=401,
        )
    response = RedirectResponse("/acompanhar/painel", status_code=303)
    create_complainant_session(response, report_id=report.id, tenant_id=report.tenant_id)
    audit_event(
        db,
        "complainant_login_success",
        tenant_id=report.tenant_id,
        report_id=report.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return response


@router.get("/painel", response_class=HTMLResponse)
def panel(request: Request, db: Session = Depends(get_db)):
    session = get_complainant_session(request)
    if not session:
        return RedirectResponse("/acompanhar", status_code=303)
    report = db.scalar(
        select(Report)
        .options(selectinload(Report.messages))
        .where(Report.id == session.report_id, Report.tenant_id == session.tenant_id)
    )
    if not report:
        return RedirectResponse("/acompanhar", status_code=303)
    messages = [
        message
        for message in sorted(report.messages, key=lambda item: item.created_at)
        if message.sender_type in {"empresa", "sistema"}
    ]
    audit_event(
        db,
        "complainant_report_viewed",
        tenant_id=report.tenant_id,
        report_id=report.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return templates.TemplateResponse(
        "acompanhar_painel.html",
        {
            "request": request,
            "report": report,
            "messages": messages,
            "statuses": STATUS_LABELS,
            "categories": CATEGORY_LABELS,
            "csrf_token": session.csrf_token,
        },
    )


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    session = get_complainant_session(request)
    if not session:
        return RedirectResponse("/acompanhar", status_code=303)
    if not verify_complainant_csrf(request, csrf_token):
        return Response("CSRF invalido.", status_code=400)
    response = RedirectResponse("/acompanhar", status_code=303)
    destroy_complainant_session(request, response)
    audit_event(
        db,
        "complainant_logout",
        tenant_id=session.tenant_id,
        report_id=session.report_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return response
