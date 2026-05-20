import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.report import Report
from app.models.report_message import ReportMessage
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture()
def client():
    return TestClient(app, base_url="https://testserver")


@pytest.fixture()
def admin_data():
    marker = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        root = User(
            tenant_id=None,
            name="Root Teste",
            email=f"root-{marker}@triton.local",
            password_hash=hash_password("Root123!"),
            role="admin_triton",
            status="active",
        )
        tenant = Tenant(name=f"Tenant Admin {marker}", document=f"TA{marker}", slug=f"tenant-admin-{marker}", status="active")
        db.add_all([root, tenant])
        db.flush()
        tenant_admin = User(
            tenant_id=tenant.id,
            name="Tenant Admin",
            email=f"tenant-admin-{marker}@example.invalid",
            password_hash=hash_password("Admin123!"),
            role="tenant_admin",
            status="active",
        )
        report = Report(
            tenant_id=tenant.id,
            protocol=f"CDO-C{marker[:9].upper()}",
            access_login=f"USR-C{marker[:7].upper()}",
            access_password_hash=hash_password("Senha123!"),
            is_anonymous=True,
            reporter_ip_hash="hash",
            category="outros",
            description="Denuncia admin global",
            status="recebida",
        )
        db.add_all([tenant_admin, report])
        db.flush()
        db.add(ReportMessage(tenant_id=tenant.id, report_id=report.id, sender_type="empresa", message="Resposta preservada"))
        db.commit()
        return {
            "root_email": root.email,
            "tenant_admin_email": tenant_admin.email,
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "report_protocol": report.protocol,
            "report_login": report.access_login,
            "report_password": "Senha123!",
        }
    finally:
        db.close()


def login_admin(client, email: str, ip: str = "10.100.0.1") -> str:
    response = client.post(
        "/auth/login",
        data={"email": email, "password": "Root123!"},
        headers={"x-forwarded-for": ip},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    page = client.get("/admin", headers={"x-forwarded-for": ip})
    assert page.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert match
    return match.group(1)


def login_tenant(client, email: str, ip: str = "10.100.0.2"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": "Admin123!"},
        headers={"x-forwarded-for": ip},
        follow_redirects=False,
    )


def test_admin_login(client, admin_data):
    response = client.post(
        "/auth/login",
        data={"email": admin_data["root_email"], "password": "Root123!"},
        headers={"x-forwarded-for": "10.100.0.3"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"


def test_tenant_admin_nao_acessa_admin(client, admin_data):
    assert login_tenant(client, admin_data["tenant_admin_email"], "10.100.0.4").status_code == 303
    response = client.get("/admin", headers={"x-forwarded-for": "10.100.0.4"})
    assert response.status_code == 403


def test_sem_login_nao_acessa_admin(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_criacao_tenant(client, admin_data):
    csrf = login_admin(client, admin_data["root_email"], "10.100.0.5")
    slug = f"empresa-alpha-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/admin/tenants",
        data={
            "csrf_token": csrf,
            "name": "Empresa Alpha",
            "document": f"DOC{uuid.uuid4().hex[:10]}",
            "slug": slug,
            "admin_name": "Admin Empresa Alpha",
            "admin_email": f"admin-{slug}@example.invalid",
        },
        headers={"x-forwarded-for": "10.100.0.5"},
    )
    assert response.status_code == 200
    assert "Senha temporaria" in response.text
    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
        assert tenant is not None
        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.role == "tenant_admin"))
        assert admin is not None
    finally:
        db.close()


def test_slug_invalido_e_duplicado_recusados(client, admin_data):
    csrf = login_admin(client, admin_data["root_email"], "10.100.0.6")
    invalid = client.post(
        "/admin/tenants",
        data={
            "csrf_token": csrf,
            "name": "Empresa Invalida",
            "document": f"DOC{uuid.uuid4().hex[:10]}",
            "slug": "Empresa Alpha",
            "admin_name": "Admin",
            "admin_email": "admin-invalid@example.invalid",
        },
        headers={"x-forwarded-for": "10.100.0.6"},
    )
    assert invalid.status_code == 400
    assert "Slug invalido" in invalid.text
    duplicate = client.post(
        "/admin/tenants",
        data={
            "csrf_token": csrf,
            "name": "Empresa Duplicada",
            "document": f"DOC{uuid.uuid4().hex[:10]}",
            "slug": admin_data["tenant_slug"],
            "admin_name": "Admin",
            "admin_email": "admin-dup@example.invalid",
        },
        headers={"x-forwarded-for": "10.100.0.6"},
    )
    assert duplicate.status_code == 400
    assert "Slug ja cadastrado" in duplicate.text


def test_tenant_inactive_bloqueia_publico_e_login_mas_preserva_acompanhamento(client, admin_data):
    csrf = login_admin(client, admin_data["root_email"], "10.100.0.7")
    response = client.post(
        f"/admin/tenants/{admin_data['tenant_id']}/status",
        data={"csrf_token": csrf, "status": "inactive"},
        headers={"x-forwarded-for": "10.100.0.7"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    public = client.get(f"/{admin_data['tenant_slug']}", headers={"x-forwarded-for": "10.100.0.8"})
    assert public.status_code == 404
    login = login_tenant(client, admin_data["tenant_admin_email"], "10.100.0.9")
    assert login.status_code == 401
    complainant = client.post(
        "/acompanhar/login",
        data={"protocol": admin_data["report_protocol"], "login": admin_data["report_login"], "password": admin_data["report_password"]},
        headers={"x-forwarded-for": "10.100.0.10"},
        follow_redirects=False,
    )
    assert complainant.status_code == 303
    panel = client.get("/acompanhar/painel", headers={"x-forwarded-for": "10.100.0.10"})
    assert panel.status_code == 200
    assert "Resposta preservada" in panel.text


def test_admin_visualiza_denuncias_globais(client, admin_data):
    login_admin(client, admin_data["root_email"], "10.100.0.11")
    response = client.get("/admin/denuncias", headers={"x-forwarded-for": "10.100.0.11"})
    assert response.status_code == 200
    assert admin_data["report_protocol"] in response.text
    assert "Denuncia admin global" not in response.text


def test_cross_role_bloqueado(client, admin_data):
    assert login_tenant(client, admin_data["tenant_admin_email"], "10.100.0.12").status_code == 303
    response = client.get("/admin/denuncias", headers={"x-forwarded-for": "10.100.0.12"})
    assert response.status_code == 403
