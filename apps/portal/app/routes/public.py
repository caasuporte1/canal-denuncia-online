import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.attachment import Attachment
from app.models.report import Report
from app.models.tenant import Tenant
from app.services.audit import audit_event
from app.services.credentials import generate_login, generate_password, hash_access_password
from app.services.email import notify_tenant_admins
from app.services.ip_policy import anonymous_ip_hash, get_client_ip
from app.services.protocol import generate_protocol
from app.services.upload import MAX_TOTAL_UPLOAD_BYTES, UploadValidationError, validate_and_store_upload

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CATEGORIES = [
    ("assedio_moral", "Assédio moral"),
    ("assedio_sexual", "Assédio sexual"),
    ("discriminacao", "Discriminação"),
    ("seguranca_do_trabalho", "Segurança do trabalho"),
    ("conduta_etica", "Conduta ética"),
    ("outros", "Outros"),
]


def _active_tenant(db: Session, slug: str) -> Tenant | None:
    return db.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.status == "active"))


@router.get("/{tenant_slug}", response_class=HTMLResponse)
@limiter.limit("30/minute")
def public_form(request: Request, tenant_slug: str, db: Session = Depends(get_db)):
    tenant = _active_tenant(db, tenant_slug)
    if not tenant:
        audit_event(
            db,
            "tenant_not_found",
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            metadata={"slug": tenant_slug[:120]},
        )
        db.commit()
        return templates.TemplateResponse("tenant_not_found.html", {"request": request, "tenant_slug": tenant_slug}, status_code=404)
    return templates.TemplateResponse("public_report_form.html", {"request": request, "tenant": tenant, "categories": CATEGORIES, "errors": []})


@router.post("/{tenant_slug}/denuncias", response_class=HTMLResponse)
@limiter.limit("5/minute")
def create_report(
    request: Request,
    tenant_slug: str,
    report_type: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    reporter_name: str = Form(""),
    reporter_email: str = Form(""),
    reporter_phone: str = Form(""),
    website: str = Form(""),
    attachments: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
):
    tenant = _active_tenant(db, tenant_slug)
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    if not tenant:
        return templates.TemplateResponse("tenant_not_found.html", {"request": request, "tenant_slug": tenant_slug}, status_code=404)

    if website.strip():
        audit_event(db, "spam_detected", tenant_id=tenant.id, ip_address=client_ip, user_agent=user_agent)
        db.commit()
        return templates.TemplateResponse("report_success.html", {"request": request, "tenant": tenant, "fake_success": True})

    errors = _validate_form(report_type, category, description, reporter_name, reporter_email)
    if errors:
        return templates.TemplateResponse(
            "public_report_form.html",
            {"request": request, "tenant": tenant, "categories": CATEGORIES, "errors": errors},
            status_code=400,
        )

    is_anonymous = report_type == "anonima"
    password = generate_password()
    report = Report(
        tenant_id=tenant.id,
        protocol=generate_protocol(db),
        access_login=generate_login(db),
        access_password_hash=hash_access_password(password),
        is_anonymous=is_anonymous,
        reporter_name=None if is_anonymous else reporter_name.strip(),
        reporter_email=None if is_anonymous else reporter_email.strip(),
        reporter_phone=None if is_anonymous else reporter_phone.strip() or None,
        reporter_ip_hash=anonymous_ip_hash(client_ip) if is_anonymous else None,
        reporter_ip_clear=None if is_anonymous else client_ip,
        category=category,
        description=description.strip(),
        status="recebida",
        version=1,
    )

    try:
        db.add(report)
        db.flush()
        total_upload_bytes = 0
        for upload in attachments or []:
            if not upload.filename:
                continue
            stored = validate_and_store_upload(upload, tenant.id, report.id)
            total_upload_bytes += stored["size_bytes"]
            if total_upload_bytes > MAX_TOTAL_UPLOAD_BYTES:
                raise UploadValidationError("Tamanho total dos anexos excede o limite permitido.")
            db.add(Attachment(tenant_id=tenant.id, report_id=report.id, uploaded_by_type="denunciante", **stored))
            audit_event(
                db,
                "attachment_uploaded",
                tenant_id=tenant.id,
                report_id=report.id,
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={"filename": stored["original_filename"], "size_bytes": stored["size_bytes"]},
            )
        audit_event(db, "report_created", tenant_id=tenant.id, report_id=report.id, ip_address=client_ip, user_agent=user_agent)
        notify_tenant_admins(db, tenant, report, client_ip, user_agent)
        db.commit()
    except UploadValidationError as exc:
        db.rollback()
        return templates.TemplateResponse(
            "public_report_form.html",
            {"request": request, "tenant": tenant, "categories": CATEGORIES, "errors": [str(exc)]},
            status_code=400,
        )

    return templates.TemplateResponse(
        "report_success.html",
        {
            "request": request,
            "tenant": tenant,
            "protocol": report.protocol,
            "login": report.access_login,
            "password": password,
            "fake_success": False,
        },
    )


@router.post("/{tenant_slug}/denuncias/credenciais-pdf")
@limiter.limit("10/minute")
def credentials_pdf(
    request: Request,
    tenant_slug: str,
    protocol: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    tenant = _active_tenant(db, tenant_slug)
    if not tenant:
        return templates.TemplateResponse("tenant_not_found.html", {"request": request, "tenant_slug": tenant_slug}, status_code=404)
    pdf = _credentials_pdf(protocol, login, password)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="credenciais-denuncia.pdf"'},
    )


def _validate_form(report_type: str, category: str, description: str, reporter_name: str, reporter_email: str) -> list[str]:
    errors: list[str] = []
    if report_type not in {"anonima", "identificada"}:
        errors.append("Tipo de denúncia inválido.")
    if category not in {key for key, _ in CATEGORIES}:
        errors.append("Categoria obrigatória.")
    if not description.strip():
        errors.append("Descrição obrigatória.")
    if report_type == "identificada":
        if not reporter_name.strip():
            errors.append("Nome obrigatório para denúncia identificada.")
        if not reporter_email.strip():
            errors.append("E-mail obrigatório para denúncia identificada.")
    return errors


def _credentials_pdf(protocol: str, login: str, password: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("Credenciais da denúncia")
    pdf.drawString(72, 780, "Credenciais da denúncia")
    pdf.drawString(72, 740, f"Protocolo: {protocol}")
    pdf.drawString(72, 720, f"Login: {login}")
    pdf.drawString(72, 700, f"Senha: {password}")
    pdf.drawString(72, 660, "Guarde estas informações. Não será possível recuperar este acesso.")
    pdf.save()
    return buffer.getvalue()
