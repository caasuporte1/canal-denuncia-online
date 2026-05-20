import random

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.audit_log import AuditLog
from app.models.report import Report
from app.models.tenant import Tenant
from app.models.user import User
from app.services.credential_check import _DUMMY_HASH, verify_credentials_constant_time


@pytest.fixture(scope="session", autouse=True)
def seed_tenant():
    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "triton"))
        if not tenant:
            tenant = Tenant(name="Triton SST", document="00000000000000", slug="triton", status="active")
            db.add(tenant)
            db.flush()
        admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == "admin-triton@example.invalid"))
        if not admin:
            db.add(
                User(
                    tenant_id=tenant.id,
                    name="Admin Triton",
                    email="admin-triton@example.invalid",
                    password_hash=hash_password("dev-only-change-me"),
                    role="tenant_admin",
                    status="active",
                )
            )
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def client():
    return TestClient(app)


def headers(ip: str) -> dict[str, str]:
    return {"x-forwarded-for": ip}


def test_get_triton_exibe_formulario(client):
    response = client.get("/triton", headers=headers("10.10.0.1"))
    assert response.status_code == 200
    assert "Enviar denúncia" in response.text


def test_get_tenant_inexistente_retorna_pagina_amigavel(client):
    response = client.get("/empresa-inexistente", headers=headers("10.10.0.2"))
    assert response.status_code == 404
    assert "Canal não encontrado" in response.text


def test_post_cria_denuncia_anonima_e_credenciais(client):
    response = client.post(
        "/triton/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Descricao anonima de teste"},
        headers=headers("10.10.0.3"),
    )
    assert response.status_code == 200
    assert "CDO-" in response.text
    assert "USR-" in response.text

    db = SessionLocal()
    try:
        report = db.scalar(select(Report).where(Report.description == "Descricao anonima de teste"))
        assert report is not None
        assert report.protocol.startswith("CDO-")
        assert len(report.protocol) == 14
        assert "2026" not in report.protocol
        assert report.reporter_ip_hash is not None
        assert report.reporter_ip_clear is None
    finally:
        db.close()


def test_upload_invalido_e_recusado(client):
    response = client.post(
        "/triton/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Upload invalido"},
        files={"attachments": ("malware.exe", b"fake", "application/octet-stream")},
        headers=headers("10.10.0.4"),
    )
    assert response.status_code == 400
    assert "Tipo de arquivo não permitido" in response.text


def test_tenant_inexistente_nao_cria_denuncia(client):
    db = SessionLocal()
    try:
        before = db.scalar(select(func.count(Report.id)))
    finally:
        db.close()
    response = client.post(
        "/empresa-inexistente/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Nao deve criar"},
        headers=headers("10.10.0.5"),
    )
    assert response.status_code == 404
    db = SessionLocal()
    try:
        after = db.scalar(select(func.count(Report.id)))
        assert after == before
    finally:
        db.close()


def test_honeypot_nao_cria_denuncia_real(client):
    db = SessionLocal()
    try:
        before = db.scalar(select(func.count(Report.id)))
    finally:
        db.close()
    response = client.post(
        "/triton/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Spam", "website": "https://bot.test"},
        headers=headers("10.10.0.6"),
    )
    assert response.status_code == 200
    assert "CDO-" not in response.text
    db = SessionLocal()
    try:
        after = db.scalar(select(func.count(Report.id)))
        spam = db.scalar(select(AuditLog).where(AuditLog.event_type == "spam_detected").order_by(AuditLog.created_at.desc()))
        assert after == before
        assert spam is not None
    finally:
        db.close()


def test_denuncia_identificada_grava_ip_claro(client):
    response = client.post(
        "/triton/denuncias",
        data={
            "report_type": "identificada",
            "category": "conduta_etica",
            "description": "Descricao identificada",
            "reporter_name": "Pessoa Teste",
            "reporter_email": "pessoa@example.invalid",
        },
        headers=headers("10.10.0.7"),
    )
    assert response.status_code == 200
    db = SessionLocal()
    try:
        report = db.scalar(select(Report).where(Report.description == "Descricao identificada"))
        assert report is not None
        assert report.reporter_ip_clear == "10.10.0.7"
        assert report.reporter_ip_hash is None
    finally:
        db.close()


def test_credential_check_executa_dummy_hash(monkeypatch):
    calls = {}

    def fake_verify(password, password_hash):
        calls["hash"] = password_hash
        return False

    monkeypatch.setattr("app.services.credential_check.verify_password", fake_verify)
    db = SessionLocal()
    try:
        assert verify_credentials_constant_time(db, "CDO-NAOEXISTE", "USR-XXXXXXX", "senha") is False
        assert calls["hash"] == _DUMMY_HASH
    finally:
        db.close()


def test_rate_limit_retorna_429(client):
    ip = f"10.250.{random.randint(1, 254)}.{random.randint(1, 254)}"
    for _ in range(30):
        response = client.get("/triton", headers=headers(ip))
        assert response.status_code == 200
    response = client.get("/triton", headers=headers(ip))
    assert response.status_code == 429
