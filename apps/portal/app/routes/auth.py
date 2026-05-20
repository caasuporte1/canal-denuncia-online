from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.core.auth import require_auth
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import verify_password
from app.core.session import create_session, destroy_session, verify_csrf
from app.models.user import User
from app.services.audit import audit_event
from app.services.ip_policy import get_client_ip

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    user = db.scalar(select(User).where(User.email == email.strip().lower(), User.status == "active"))
    valid = bool(user and user.role in {"tenant_admin", "tenant_user"} and verify_password(password, user.password_hash))
    if not valid:
        audit_event(
            db,
            "login_failed",
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"email": email.strip().lower()[:255]},
        )
        db.commit()
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario ou senha invalidos"},
            status_code=401,
        )

    redirect = RedirectResponse("/empresa", status_code=303)
    create_session(redirect, user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    audit_event(db, "login_success", tenant_id=user.tenant_id, user_id=user.id, ip_address=client_ip, user_agent=user_agent)
    db.commit()
    return redirect


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form(...),
    current=Depends(require_auth),
    db: Session = Depends(get_db),
):
    if not verify_csrf(request, csrf_token):
        return Response("CSRF invalido.", status_code=400)
    response = RedirectResponse("/auth/login", status_code=303)
    destroy_session(request, response)
    audit_event(
        db,
        "logout",
        tenant_id=current.user.tenant_id,
        user_id=current.user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return response
