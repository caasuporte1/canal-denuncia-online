import random
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.session import redis_client
from app.main import app
from app.models.report import Report
from app.models.report_message import ReportMessage
from app.models.tenant import Tenant
from app.services.credential_check import _DUMMY_HASH, verify_credentials_constant_time


@pytest.fixture()
def client():
    return TestClient(app, base_url="https://testserver")


@pytest.fixture()
def reports_data():
    marker = uuid.uuid4().hex[:10].upper()
    db = SessionLocal()
    try:
        tenant = Tenant(name=f"Tenant Acompanhamento {marker}", document=f"AC{marker}", slug=f"acomp-{marker.lower()}", status="active")
        db.add(tenant)
        db.flush()
        report_a = Report(
            tenant_id=tenant.id,
            protocol=f"CDO-A{marker[:9]}",
            access_login=f"USR-A{marker[:7]}",
            access_password_hash=hash_password("SenhaA123!"),
            is_anonymous=True,
            reporter_ip_hash="hash-a",
            category="outros",
            description="Descricao denuncia A",
            status="aguardando_resposta",
        )
        report_b = Report(
            tenant_id=tenant.id,
            protocol=f"CDO-B{marker[:9]}",
            access_login=f"USR-B{marker[:7]}",
            access_password_hash=hash_password("SenhaB123!"),
            is_anonymous=True,
            reporter_ip_hash="hash-b",
            category="conduta_etica",
            description="Descricao denuncia B",
            status="recebida",
        )
        db.add_all([report_a, report_b])
        db.flush()
        db.add_all(
            [
                ReportMessage(tenant_id=tenant.id, report_id=report_a.id, sender_type="empresa", message="Resposta visivel da empresa"),
                ReportMessage(tenant_id=tenant.id, report_id=report_a.id, sender_type="sistema", message="Mensagem visivel do sistema"),
                ReportMessage(tenant_id=tenant.id, report_id=report_a.id, sender_type="admin_triton", message="Mensagem interna invisivel"),
                ReportMessage(tenant_id=tenant.id, report_id=report_b.id, sender_type="empresa", message="Resposta da denuncia B"),
            ]
        )
        db.commit()
        return {
            "protocol_a": report_a.protocol,
            "login_a": report_a.access_login,
            "password_a": "SenhaA123!",
            "protocol_b": report_b.protocol,
            "login_b": report_b.access_login,
            "password_b": "SenhaB123!",
        }
    finally:
        db.close()


def login(client: TestClient, data: dict, ip: str = "10.90.0.1"):
    return client.post(
        "/acompanhar/login",
        data={"protocol": data["protocol_a"], "login": data["login_a"], "password": data["password_a"]},
        headers={"x-forwarded-for": ip},
        follow_redirects=False,
    )


def test_login_valido_cria_sessao(client, reports_data):
    response = login(client, reports_data, "10.90.0.2")
    assert response.status_code == 303
    assert response.headers["location"] == "/acompanhar/painel"
    assert settings.complainant_session_cookie_name in client.cookies


def test_login_invalido_mensagem_generica(client, reports_data):
    response = client.post(
        "/acompanhar/login",
        data={"protocol": reports_data["protocol_a"], "login": reports_data["login_a"], "password": "errada"},
        headers={"x-forwarded-for": "10.90.0.3"},
    )
    assert response.status_code == 401
    assert "Credenciais inválidas" in response.text
    assert "Protocolo inválido" not in response.text
    assert "Login inválido" not in response.text
    assert "Senha inválida" not in response.text


def test_dummy_hash_executado(monkeypatch):
    calls = {}

    def fake_verify(password, password_hash):
        calls["hash"] = password_hash
        return False

    monkeypatch.setattr("app.services.credential_check.verify_password", fake_verify)
    db = SessionLocal()
    try:
        assert verify_credentials_constant_time(db, "CDO-INEXISTENTE", "USR-INEXIST", "qualquer") is False
        assert calls["hash"] == _DUMMY_HASH
    finally:
        db.close()


def test_timing_helper_usado_no_endpoint(monkeypatch, client, reports_data):
    calls = {"count": 0}

    def wrapped(db, protocol, login_value, password):
        calls["count"] += 1
        return verify_credentials_constant_time(db, protocol, login_value, password)

    monkeypatch.setattr("app.routes.acompanhar.verify_credentials_constant_time", wrapped)
    response = login(client, reports_data, "10.90.0.4")
    assert response.status_code == 303
    assert calls["count"] == 1


def test_logout(client, reports_data):
    assert login(client, reports_data, "10.90.0.5").status_code == 303
    page = client.get("/acompanhar/painel", headers={"x-forwarded-for": "10.90.0.5"})
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = client.post("/acompanhar/logout", data={"csrf_token": csrf}, headers={"x-forwarded-for": "10.90.0.5"}, follow_redirects=False)
    assert response.status_code == 303
    blocked = client.get("/acompanhar/painel", headers={"x-forwarded-for": "10.90.0.5"}, follow_redirects=False)
    assert blocked.status_code == 303


def test_painel_exige_sessao(client):
    response = client.get("/acompanhar/painel", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/acompanhar"


def test_timeline_renderiza_e_filtra_interno(client, reports_data):
    assert login(client, reports_data, "10.90.0.6").status_code == 303
    response = client.get("/acompanhar/painel", headers={"x-forwarded-for": "10.90.0.6"})
    assert response.status_code == 200
    assert "Resposta visivel da empresa" in response.text
    assert "Mensagem visivel do sistema" in response.text
    assert "Mensagem interna invisivel" not in response.text


def test_cross_report_bloqueado(client, reports_data):
    assert login(client, reports_data, "10.90.0.7").status_code == 303
    response = client.get("/acompanhar/painel", headers={"x-forwarded-for": "10.90.0.7"})
    assert response.status_code == 200
    assert "Descricao denuncia A" in response.text
    assert "Descricao denuncia B" not in response.text
    assert "Resposta da denuncia B" not in response.text


def test_rate_limit_login_retorna_429(client, reports_data):
    ip = f"10.91.{random.randint(1, 254)}.{random.randint(1, 254)}"
    for _ in range(5):
        response = client.post(
            "/acompanhar/login",
            data={"protocol": "CDO-NAOEXISTE", "login": "USR-NAOEX", "password": "x"},
            headers={"x-forwarded-for": ip},
        )
        assert response.status_code == 401
    response = client.post(
        "/acompanhar/login",
        data={"protocol": "CDO-NAOEXISTE", "login": "USR-NAOEX", "password": "x"},
        headers={"x-forwarded-for": ip},
    )
    assert response.status_code == 429


def test_sessao_expira_quando_chave_redis_some(client, reports_data):
    assert login(client, reports_data, "10.90.0.8").status_code == 303
    session_id = client.cookies.get(settings.complainant_session_cookie_name)
    redis_client.delete(f"complainant_session:{session_id}")
    response = client.get("/acompanhar/painel", headers={"x-forwarded-for": "10.90.0.8"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/acompanhar"
