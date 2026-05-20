from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.templating import Jinja2Templates

from app.core.auth import CurrentUser, require_roles
from app.core.database import get_db
from app.core.session import verify_csrf
from app.models.attachment import Attachment
from app.models.report import Report
from app.models.report_message import ReportMessage
from app.models.tenant import Tenant
from app.routes.public import CATEGORIES
from app.services.audit import audit_event
from app.services.ip_policy import get_client_ip

router = APIRouter(prefix="/empresa")
templates = Jinja2Templates(directory="app/templates")

ALLOWED_STATUSES = {"recebida", "em_triagem", "em_apuracao", "aguardando_resposta", "concluida", "arquivada"}
CATEGORY_LABELS = dict(CATEGORIES)
STATUS_LABELS = {
    "recebida": "Recebida",
    "em_triagem": "Em triagem",
    "em_apuracao": "Em apuração",
    "aguardando_resposta": "Aguardando resposta",
    "concluida": "Concluída",
    "arquivada": "Arquivada",
}


def _tenant(db: Session, current: CurrentUser) -> Tenant:
    if current.user.role not in {"tenant_admin", "tenant_user"} or not current.user.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    tenant = db.get(Tenant, current.user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    return tenant


def _csrf_or_400(request: Request, csrf_token: str) -> None:
    if not verify_csrf(request, csrf_token):
        raise HTTPException(status_code=400, detail="CSRF inválido.")


def _report_or_404(db: Session, current: CurrentUser, report_id: UUID, request: Request) -> Report:
    report = db.scalar(
        select(Report)
        .options(selectinload(Report.attachments), selectinload(Report.messages))
        .where(Report.id == report_id, Report.tenant_id == current.user.tenant_id)
    )
    if not report:
        audit_event(
            db,
            "unauthorized_access_attempt",
            tenant_id=current.user.tenant_id,
            user_id=current.user.id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            metadata={"resource": "report", "resource_id": str(report_id)},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Não encontrado.")
    return report


@router.get("")
def dashboard(
    request: Request,
    current: CurrentUser = Depends(require_roles("tenant_admin", "tenant_user")),
    db: Session = Depends(get_db),
):
    tenant = _tenant(db, current)
    total = db.scalar(select(func.count(Report.id)).where(Report.tenant_id == tenant.id)) or 0
    open_total = db.scalar(select(func.count(Report.id)).where(Report.tenant_id == tenant.id, Report.status.notin_(["concluida", "arquivada"]))) or 0
    return templates.TemplateResponse(
        "empresa_dashboard.html",
        {"request": request, "tenant": tenant, "current": current, "total": total, "open_total": open_total},
    )


@router.get("/denuncias")
def reports_list(
    request: Request,
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    protocol: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(require_roles("tenant_admin", "tenant_user")),
    db: Session = Depends(get_db),
):
    tenant = _tenant(db, current)
    stmt = select(Report).where(Report.tenant_id == tenant.id)
    if status:
        stmt = stmt.where(Report.status == status)
    if category:
        stmt = stmt.where(Report.category == category)
    if protocol:
        stmt = stmt.where(Report.protocol.ilike(f"%{protocol.strip()}%"))
    reports = db.scalars(stmt.order_by(Report.created_at.desc()).limit(limit).offset(offset)).all()
    return templates.TemplateResponse(
        "empresa_denuncias.html",
        {
            "request": request,
            "tenant": tenant,
            "current": current,
            "reports": reports,
            "statuses": STATUS_LABELS,
            "categories": CATEGORY_LABELS,
            "filters": {"status": status or "", "category": category or "", "protocol": protocol or "", "limit": limit, "offset": offset},
        },
    )


@router.get("/denuncias/{report_id}")
def report_detail(
    request: Request,
    report_id: UUID,
    current: CurrentUser = Depends(require_roles("tenant_admin", "tenant_user")),
    db: Session = Depends(get_db),
):
    tenant = _tenant(db, current)
    report = _report_or_404(db, current, report_id, request)
    audit_event(db, "report_viewed", tenant_id=tenant.id, user_id=current.user.id, report_id=report.id, ip_address=get_client_ip(request), user_agent=request.headers.get("user-agent"))
    db.commit()
    return templates.TemplateResponse(
        "empresa_denuncia_detalhe.html",
        {
            "request": request,
            "tenant": tenant,
            "current": current,
            "report": report,
            "statuses": STATUS_LABELS,
            "categories": CATEGORY_LABELS,
            "csrf_token": current.session.csrf_token,
        },
    )


@router.post("/denuncias/{report_id}/status")
def change_status(
    request: Request,
    report_id: UUID,
    status: str = Form(...),
    csrf_token: str = Form(...),
    current: CurrentUser = Depends(require_roles("tenant_admin", "tenant_user")),
    db: Session = Depends(get_db),
):
    _csrf_or_400(request, csrf_token)
    report = _report_or_404(db, current, report_id, request)
    if status not in ALLOWED_STATUSES or not _valid_transition(report.status, status):
        return Response("Transição de status inválida.", status_code=400)
    old_status = report.status
    report.status = status
    audit_event(
        db,
        "report_status_changed",
        tenant_id=current.user.tenant_id,
        user_id=current.user.id,
        report_id=report.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"old_status": old_status, "new_status": status},
    )
    db.commit()
    return RedirectResponse(f"/empresa/denuncias/{report.id}", status_code=303)


@router.post("/denuncias/{report_id}/responder")
def respond_report(
    request: Request,
    report_id: UUID,
    message: str = Form(...),
    csrf_token: str = Form(...),
    current: CurrentUser = Depends(require_roles("tenant_admin", "tenant_user")),
    db: Session = Depends(get_db),
):
    _csrf_or_400(request, csrf_token)
    report = _report_or_404(db, current, report_id, request)
    message = message.strip()
    if not message:
        return Response("Mensagem obrigatória.", status_code=400)
    if len(message) > 5000:
        return Response("Mensagem muito longa.", status_code=400)
    db.add(ReportMessage(tenant_id=report.tenant_id, report_id=report.id, sender_type="empresa", sender_user_id=current.user.id, message=message))
    audit_event(
        db,
        "report_response_created",
        tenant_id=current.user.tenant_id,
        user_id=current.user.id,
        report_id=report.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return RedirectResponse(f"/empresa/denuncias/{report.id}", status_code=303)


@router.get("/anexos/{attachment_id}")
def download_attachment(
    request: Request,
    attachment_id: UUID,
    current: CurrentUser = Depends(require_roles("tenant_admin", "tenant_user")),
    db: Session = Depends(get_db),
):
    attachment = db.scalar(
        select(Attachment)
        .join(Report, Attachment.report_id == Report.id)
        .where(Attachment.id == attachment_id, Attachment.tenant_id == current.user.tenant_id, Report.tenant_id == current.user.tenant_id, Attachment.deleted_at.is_(None))
    )
    if not attachment:
        audit_event(
            db,
            "unauthorized_access_attempt",
            tenant_id=current.user.tenant_id,
            user_id=current.user.id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            metadata={"resource": "attachment", "resource_id": str(attachment_id)},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Não encontrado.")
    path = Path(attachment.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Não encontrado.")
    audit_event(
        db,
        "attachment_downloaded",
        tenant_id=current.user.tenant_id,
        user_id=current.user.id,
        report_id=attachment.report_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"attachment_id": str(attachment.id)},
    )
    db.commit()
    return FileResponse(path, media_type=attachment.mime_type, filename=attachment.original_filename)


def _valid_transition(current_status: str, new_status: str) -> bool:
    if current_status == new_status:
        return True
    if current_status == "recebida" and new_status == "arquivada":
        return False
    if current_status == "concluida" and new_status != "arquivada":
        return False
    if current_status == "arquivada":
        return False
    return True
