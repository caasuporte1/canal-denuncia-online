import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.seed_pilot import PILOT_TENANTS, seed_pilot_tenants


def test_homepage_portal_exibe_acessos_principais():
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/")
    assert response.status_code == 200
    assert "Canal de Denúncia Online" in response.text
    assert "Ambiente seguro para registrar, acompanhar e tratar relatos internos." in response.text
    assert 'href="/static/favicon.svg"' in response.text
    assert "Fazer denúncia" in response.text
    assert "Utilize o link fornecido pela sua empresa" in response.text
    assert 'href="/acompanhar"' in response.text
    assert 'href="/auth/login"' in response.text
    assert "Acesso administrativo" in response.text
    assert "Como funciona" in response.text
    assert "Guarde protocolo, login e senha" in response.text


def test_paginas_institucionais_provisorias():
    client = TestClient(app, base_url="https://testserver")
    pages = [
        ("/privacidade", "Privacidade", "validação jurídica/compliance"),
        ("/termos", "Termos de Uso", "validação jurídica/compliance"),
        ("/orientacoes", "Orientações ao usuário", "Use o canal de forma responsável."),
    ]
    for path, title, content in pages:
        response = client.get(path)
        assert response.status_code == 200
        assert title in response.text
        assert content in response.text
        assert "Início" in response.text


def test_favicon_placeholder_disponivel():
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/static/favicon.svg")
    assert response.status_code == 200
    assert "svg" in response.text


def test_login_redirect_empresa_e_admin():
    marker = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        tenant = Tenant(name=f"Tenant UX {marker}", document=f"UX{marker}", slug=f"ux-{marker}", status="active")
        db.add(tenant)
        db.flush()
        db.add_all(
            [
                User(
                    tenant_id=tenant.id,
                    name="Admin Empresa",
                    email=f"empresa-{marker}@example.invalid",
                    password_hash=hash_password("Admin123!"),
                    role="tenant_admin",
                    status="active",
                ),
                User(
                    tenant_id=None,
                    name="Root UX",
                    email=f"root-{marker}@triton.local",
                    password_hash=hash_password("Root123!"),
                    role="admin_triton",
                    status="active",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    client = TestClient(app, base_url="https://testserver")
    empresa = client.post(
        "/auth/login",
        data={"email": f"empresa-{marker}@example.invalid", "password": "Admin123!"},
        headers={"x-forwarded-for": f"10.170.1.{int(marker[:2], 16) or 1}"},
        follow_redirects=False,
    )
    assert empresa.status_code == 303
    assert empresa.headers["location"] == "/empresa"

    admin = TestClient(app, base_url="https://testserver").post(
        "/auth/login",
        data={"email": f"root-{marker}@triton.local", "password": "Root123!"},
        headers={"x-forwarded-for": f"10.170.2.{int(marker[2:4], 16) or 1}"},
        follow_redirects=False,
    )
    assert admin.status_code == 303
    assert admin.headers["location"] == "/admin"


def test_tenant_inactive_ux_amigavel():
    marker = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        db.add(Tenant(name=f"Tenant Inativo {marker}", document=f"IN{marker}", slug=f"inativo-{marker}", status="inactive"))
        db.commit()
    finally:
        db.close()

    client = TestClient(app, base_url="https://testserver")
    response = client.get(f"/inativo-{marker}", headers={"x-forwarded-for": f"10.171.0.{int(marker[:2], 16) or 1}"})
    assert response.status_code == 404
    assert "Canal não encontrado" in response.text
    assert "Voltar ao portal" in response.text


def test_seed_pilot_tenants_cria_tenants_e_usuarios():
    seed_pilot_tenants()
    db = SessionLocal()
    try:
        for item in PILOT_TENANTS:
            tenant = db.scalar(select(Tenant).where(Tenant.slug == item.slug))
            assert tenant is not None
            assert tenant.status == "active"
            admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == f"admin@{item.slug}.local"))
            user = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == f"usuario@{item.slug}.local"))
            assert admin is not None
            assert admin.role == "tenant_admin"
            assert user is not None
            assert user.role == "tenant_user"
    finally:
        db.close()
