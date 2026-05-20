import re
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.templating import Jinja2Templates

from app.core.auth import CurrentUser, require_roles
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.core.session import verify_csrf
from app.models.report import Report
from app.models.tenant import Tenant
from app.models.user import User
from app.routes.empresa import STATUS_LABELS
from app.routes.public import CATEGORIES
from app.services.audit import audit_event
from app.services.credentials import generate_password
from app.services.ip_policy import get_client_ip

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORY_LABELS = dict(CATEGORIES)


def _csrf_or_400(request: Request, csrf_token: str) -> None:
    if not verify_csrf(request, csrf_token):
        raise HTTPException(status_code=400, detail="CSRF inválido.")


@router.get("")
@limiter.limit("30/minute")
def dashboard(
    request: Request,
    current: CurrentUser = Depends(require_roles("admin_triton")),
    db: Session = Depends(get_db),
):
    total_tenants = db.scalar(select(func.count(Tenant.id))) or 0
    total_reports = db.scalar(select(func.count(Report.id))) or 0
    status_rows = db.execute(select(Report.status, func.count(Report.id)).group_by(Report.status)).all()
    latest_tenants = db.scalars(select(Tenant).order_by(Tenant.created_at.desc()).limit(5)).all()
    audit_event(db, "admin_panel_access", user_id=current.user.id, ip_address=get_client_ip(request), user_agent=request.headers.get("user-agent"))
    db.commit()
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "current": current,
            "total_tenants": total_tenants,
            "total_reports": total_reports,
            "status_rows": status_rows,
            "latest_tenants": latest_tenants,
            "statuses": STATUS_LABELS,
        },
    )


@router.get("/tenants")
@limiter.limit("30/minute")
def tenants_list(
    request: Request,
    current: CurrentUser = Depends(require_roles("admin_triton")),
    db: Session = Depends(get_db),
):
    tenants = db.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()
    return templates.TemplateResponse("admin_tenants.html", {"request": request, "current": current, "tenants": tenants})


@router.get("/tenants/novo")
@limiter.limit("30/minute")
def new_tenant_form(request: Request, current: CurrentUser = Depends(require_roles("admin_triton"))):
    return templates.TemplateResponse(
        "admin_tenant_novo.html",
        {"request": request, "current": current, "csrf_token": current.session.csrf_token, "errors": [], "created": None},
    )


@router.post("/tenants")
@limiter.limit("30/minute")
def create_tenant(
    request: Request,
    name: str = Form(...),
    document: str = Form(...),
    slug: str = Form(...),
    admin_name: str = Form(...),
    admin_email: str = Form(...),
    csrf_token: str = Form(...),
    current: CurrentUser = Depends(require_roles("admin_triton")),
    db: Session = Depends(get_db),
):
    _csrf_or_400(request, csrf_token)
    errors = _validate_tenant_form(name, document, slug, admin_name, admin_email)
    if db.scalar(select(Tenant.id).where(Tenant.slug == slug.strip())):
        errors.append("Slug já cadastrado.")
    if db.scalar(select(Tenant.id).where(Tenant.document == document.strip())):
        errors.append("Documento já cadastrado.")
    if errors:
        return templates.TemplateResponse(
            "admin_tenant_novo.html",
            {"request": request, "current": current, "csrf_token": current.session.csrf_token, "errors": errors, "created": None},
            status_code=400,
        )

    temp_password = generate_password()
    tenant = Tenant(name=name.strip(), document=document.strip(), slug=slug.strip(), status="active")
    db.add(tenant)
    db.flush()
    admin = User(
        tenant_id=tenant.id,
        name=admin_name.strip(),
        email=admin_email.strip().lower(),
        password_hash=hash_password(temp_password),
        role="tenant_admin",
        status="active",
    )
    db.add(admin)
    db.flush()
    audit_event(db, "tenant_created", tenant_id=tenant.id, user_id=current.user.id, ip_address=get_client_ip(request), user_agent=request.headers.get("user-agent"), metadata={"slug": tenant.slug})
    audit_event(db, "tenant_admin_created", tenant_id=tenant.id, user_id=current.user.id, ip_address=get_client_ip(request), user_agent=request.headers.get("user-agent"), metadata={"admin_email": admin.email})
    db.commit()
    return templates.TemplateResponse(
        "admin_tenant_novo.html",
        {
            "request": request,
            "current": current,
            "csrf_token": current.session.csrf_token,
            "errors": [],
            "created": {"tenant": tenant, "email": admin.email, "password": temp_password},
        },
    )


@router.get("/tenants/{tenant_id}")
@limiter.limit("30/minute")
def tenant_detail(
    request: Request,
    tenant_id: UUID,
    current: CurrentUser = Depends(require_roles("admin_triton")),
    db: Session = Depends(get_db),
):
    tenant = db.scalar(select(Tenant).options(selectinload(Tenant.users)).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Não encontrado.")
    total_reports = db.scalar(select(func.count(Report.id)).where(Report.tenant_id == tenant.id)) or 0
    return templates.TemplateResponse(
        "admin_tenant_detalhe.html",
        {"request": request, "current": current, "tenant": tenant, "total_reports": total_reports, "csrf_token": current.session.csrf_token},
    )


@router.post("/tenants/{tenant_id}/status")
@limiter.limit("30/minute")
def change_tenant_status(
    request: Request,
    tenant_id: UUID,
    status: str = Form(...),
    csrf_token: str = Form(...),
    current: CurrentUser = Depends(require_roles("admin_triton")),
    db: Session = Depends(get_db),
):
    _csrf_or_400(request, csrf_token)
    if status not in {"active", "inactive"}:
        return Response("Status inválido.", status_code=400)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Não encontrado.")
    old_status = tenant.status
    tenant.status = status
    audit_event(
        db,
        "tenant_status_changed",
        tenant_id=tenant.id,
        user_id=current.user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"old_status": old_status, "new_status": status},
    )
    db.commit()
    return RedirectResponse(f"/admin/tenants/{tenant.id}", status_code=303)


@router.get("/denuncias")
@limiter.limit("30/minute")
def global_reports(
    request: Request,
    tenant: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    protocol: str | None = Query(default=None),
    current: CurrentUser = Depends(require_roles("admin_triton")),
    db: Session = Depends(get_db),
):
    stmt = select(Report, Tenant).join(Tenant, Report.tenant_id == Tenant.id)
    if tenant:
        stmt = stmt.where(Report.tenant_id == tenant)
    if status:
        stmt = stmt.where(Report.status == status)
    if category:
        stmt = stmt.where(Report.category == category)
    if protocol:
        stmt = stmt.where(Report.protocol.ilike(f"%{protocol.strip()}%"))
    rows = db.execute(stmt.order_by(Report.created_at.desc()).limit(100)).all()
    tenants = db.scalars(select(Tenant).order_by(Tenant.name.asc())).all()
    audit_event(db, "admin_global_reports_view", user_id=current.user.id, ip_address=get_client_ip(request), user_agent=request.headers.get("user-agent"))
    db.commit()
    return templates.TemplateResponse(
        "admin_denuncias.html",
        {
            "request": request,
            "current": current,
            "rows": rows,
            "tenants": tenants,
            "statuses": STATUS_LABELS,
            "categories": CATEGORY_LABELS,
            "filters": {"tenant": str(tenant) if tenant else "", "status": status or "", "category": category or "", "protocol": protocol or ""},
        },
    )


def _validate_tenant_form(name: str, document: str, slug: str, admin_name: str, admin_email: str) -> list[str]:
    errors: list[str] = []
    slug = slug.strip()
    if not name.strip():
        errors.append("Nome obrigatório.")
    if not document.strip():
        errors.append("Documento obrigatório.")
    if not SLUG_RE.fullmatch(slug):
        errors.append("Slug inválido. Use apenas letras minúsculas, números e hifens.")
    if not admin_name.strip():
        errors.append("Nome do admin obrigatório.")
    if "@" not in admin_email.strip():
        errors.append("E-mail do admin inválido.")
    return errors
