import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.attachment import Attachment
from app.models.report import Report
from app.models.report_message import ReportMessage
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture()
def client():
    return TestClient(app, base_url="https://testserver")


@pytest.fixture()
def empresa_data():
    marker = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        tenant_a = Tenant(name=f"Tenant A {marker}", document=f"A{marker}", slug=f"tenant-a-{marker}", status="active")
        tenant_b = Tenant(name=f"Tenant B {marker}", document=f"B{marker}", slug=f"tenant-b-{marker}", status="active")
        db.add_all([tenant_a, tenant_b])
        db.flush()
        user_a = User(tenant_id=tenant_a.id, name="Admin A", email=f"admin-a-{marker}@example.invalid", password_hash=hash_password("Admin123!"), role="tenant_admin", status="active")
        user_b = User(tenant_id=tenant_b.id, name="Admin B", email=f"admin-b-{marker}@example.invalid", password_hash=hash_password("Admin123!"), role="tenant_admin", status="active")
        report_a = Report(
            tenant_id=tenant_a.id,
            protocol=f"CDO-A{marker[:9]}",
            access_login=f"USR-A{marker[:7]}",
            access_password_hash=hash_password("report-secret-a"),
            is_anonymous=False,
            reporter_name="Pessoa A",
            reporter_email="pessoa-a@example.invalid",
            reporter_phone="1111",
            reporter_ip_clear="10.1.1.1",
            category="outros",
            description="Denuncia tenant A",
            involved_department="Produção",
            involved_location="Turno da noite",
            involved_role="Supervisor",
            status="recebida",
        )
        report_b = Report(
            tenant_id=tenant_b.id,
            protocol=f"CDO-B{marker[:9]}",
            access_login=f"USR-B{marker[:7]}",
            access_password_hash=hash_password("report-secret-b"),
            is_anonymous=True,
            reporter_ip_hash="hash-b",
            category="conduta_etica",
            description="Denuncia tenant B",
            status="recebida",
        )
        db.add_all([user_a, user_b, report_a, report_b])
        db.flush()
        attachment_path = Path("/app/uploads") / str(tenant_a.id) / str(report_a.id) / "evidencia.txt"
        attachment_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_path.write_text("evidencia", encoding="utf-8")
        attachment_a = Attachment(
            tenant_id=tenant_a.id,
            report_id=report_a.id,
            original_filename="evidencia.txt",
            stored_filename="evidencia.txt",
            storage_path=str(attachment_path),
            mime_type="text/plain",
            size_bytes=9,
            sha256_hash="0" * 64,
            uploaded_by_type="denunciante",
        )
        attachment_b_path = Path("/app/uploads") / str(tenant_b.id) / str(report_b.id) / "b.txt"
        attachment_b_path.parent.mkdir(parents=True, exist_ok=True)
        attachment_b_path.write_text("b", encoding="utf-8")
        attachment_b = Attachment(
            tenant_id=tenant_b.id,
            report_id=report_b.id,
            original_filename="b.txt",
            stored_filename="b.txt",
            storage_path=str(attachment_b_path),
            mime_type="text/plain",
            size_bytes=1,
            sha256_hash="1" * 64,
            uploaded_by_type="denunciante",
        )
        db.add_all([attachment_a, attachment_b])
        db.commit()
        return {
            "email_a": user_a.email,
            "email_b": user_b.email,
            "report_a": str(report_a.id),
            "report_b": str(report_b.id),
            "attachment_a": str(attachment_a.id),
            "attachment_b": str(attachment_b.id),
        }
    finally:
        db.close()


def login(client: TestClient, email: str, ip: str = "10.80.0.1") -> str:
    response = client.post(
        "/auth/login",
        data={"email": email, "password": "Admin123!"},
        headers={"x-forwarded-for": ip},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get("/empresa", headers={"x-forwarded-for": ip})
    assert page.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert match
    return match.group(1)


def test_login_valido(client, empresa_data):
    response = client.post(
        "/auth/login",
        data={"email": empresa_data["email_a"], "password": "Admin123!"},
        headers={"x-forwarded-for": "10.80.0.2"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/empresa"


def test_login_invalido(client, empresa_data):
    response = client.post(
        "/auth/login",
        data={"email": empresa_data["email_a"], "password": "errada"},
        headers={"x-forwarded-for": "10.80.0.3"},
    )
    assert response.status_code == 401
    assert "Usuário ou senha inválidos" in response.text


def test_logout(client, empresa_data):
    csrf = login(client, empresa_data["email_a"], "10.80.0.4")
    response = client.post("/auth/logout", data={"csrf_token": csrf}, headers={"x-forwarded-for": "10.80.0.4"}, follow_redirects=False)
    assert response.status_code == 303
    blocked = client.get("/empresa", headers={"x-forwarded-for": "10.80.0.4"}, follow_redirects=False)
    assert blocked.status_code == 303


def test_acesso_sem_sessao_redirect_login(client):
    response = client.get("/empresa", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_listagem_tenant_correta(client, empresa_data):
    login(client, empresa_data["email_a"], "10.80.0.5")
    response = client.get("/empresa/denuncias", headers={"x-forwarded-for": "10.80.0.5"})
    assert response.status_code == 200
    assert "Denuncia tenant A" not in response.text
    assert "CDO-A" in response.text
    assert "CDO-B" not in response.text


def test_cross_tenant_bloqueado(client, empresa_data):
    login(client, empresa_data["email_a"], "10.80.0.6")
    response = client.get(f"/empresa/denuncias/{empresa_data['report_b']}", headers={"x-forwarded-for": "10.80.0.6"})
    assert response.status_code == 404


def test_detalhe_denuncia_mostra_contexto(client, empresa_data):
    login(client, empresa_data["email_a"], "10.80.0.12")
    response = client.get(f"/empresa/denuncias/{empresa_data['report_a']}", headers={"x-forwarded-for": "10.80.0.12"})
    assert response.status_code == 200
    assert "Contexto do ocorrido" in response.text
    assert "Produção" in response.text
    assert "Turno da noite" in response.text
    assert "Supervisor" in response.text


def test_criacao_resposta(client, empresa_data):
    csrf = login(client, empresa_data["email_a"], "10.80.0.7")
    response = client.post(
        f"/empresa/denuncias/{empresa_data['report_a']}/responder",
        data={"message": "Resposta da empresa", "csrf_token": csrf},
        headers={"x-forwarded-for": "10.80.0.7"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    db = SessionLocal()
    try:
        message = db.scalar(select(ReportMessage).where(ReportMessage.report_id == uuid.UUID(empresa_data["report_a"])))
        assert message is not None
        assert message.sender_type == "empresa"
    finally:
        db.close()


def test_alteracao_status_valida_e_transicao_invalida(client, empresa_data):
    csrf = login(client, empresa_data["email_a"], "10.80.0.8")
    invalid = client.post(
        f"/empresa/denuncias/{empresa_data['report_a']}/status",
        data={"status": "arquivada", "csrf_token": csrf},
        headers={"x-forwarded-for": "10.80.0.8"},
    )
    assert invalid.status_code == 400
    valid = client.post(
        f"/empresa/denuncias/{empresa_data['report_a']}/status",
        data={"status": "em_triagem", "csrf_token": csrf},
        headers={"x-forwarded-for": "10.80.0.8"},
        follow_redirects=False,
    )
    assert valid.status_code == 303


def test_status_tenant_errado_falha(client, empresa_data):
    csrf = login(client, empresa_data["email_a"], "10.80.0.9")
    response = client.post(
        f"/empresa/denuncias/{empresa_data['report_b']}/status",
        data={"status": "em_triagem", "csrf_token": csrf},
        headers={"x-forwarded-for": "10.80.0.9"},
    )
    assert response.status_code == 404


def test_resposta_tenant_errado_falha(client, empresa_data):
    csrf = login(client, empresa_data["email_a"], "10.80.0.10")
    response = client.post(
        f"/empresa/denuncias/{empresa_data['report_b']}/responder",
        data={"message": "Nao pode", "csrf_token": csrf},
        headers={"x-forwarded-for": "10.80.0.10"},
    )
    assert response.status_code == 404


def test_download_anexo_autorizado_e_cross_tenant_bloqueado(client, empresa_data):
    login(client, empresa_data["email_a"], "10.80.0.11")
    ok = client.get(f"/empresa/anexos/{empresa_data['attachment_a']}", headers={"x-forwarded-for": "10.80.0.11"})
    assert ok.status_code == 200
    assert ok.content == b"evidencia"
    blocked = client.get(f"/empresa/anexos/{empresa_data['attachment_b']}", headers={"x-forwarded-for": "10.80.0.11"})
    assert blocked.status_code == 404
