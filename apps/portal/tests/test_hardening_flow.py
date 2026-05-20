import base64
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models.attachment import Attachment
from app.models.report import Report
from app.models.tenant import Tenant
from app.services.credentials import hash_access_password
from app.services.maintenance import cleanup_orphan_uploads, retention_cleanup
from app.services.upload import UPLOAD_ROOT


def test_health_expandido():
    client = TestClient(app, base_url="https://testserver")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["postgres"] == "ok"
    assert data["checks"]["redis"] == "ok"
    assert "uptime_seconds" in data


def test_upload_mime_spoof_recusado():
    client = TestClient(app, base_url="https://testserver")
    response = client.post(
        "/triton/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Spoof"},
        files={"attachments": ("arquivo.pdf", b"MZ fake exe", "application/pdf")},
        headers={"x-forwarded-for": f"10.200.0.{uuid.uuid4().int % 200 + 1}"},
    )
    assert response.status_code == 400
    assert "Conteudo do arquivo" in response.text


def test_upload_extensao_invalida_recusada():
    client = TestClient(app, base_url="https://testserver")
    response = client.post(
        "/triton/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Extensao invalida"},
        files={"attachments": ("arquivo.exe", b"fake", "application/octet-stream")},
        headers={"x-forwarded-for": f"10.201.0.{uuid.uuid4().int % 200 + 1}"},
    )
    assert response.status_code == 400
    assert "Tipo de arquivo nao permitido" in response.text


def test_upload_filename_traversal_sanitizado():
    client = TestClient(app, base_url="https://testserver")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
    response = client.post(
        "/triton/denuncias",
        data={"report_type": "anonima", "category": "outros", "description": "Traversal upload"},
        files={"attachments": ("../evil.png", png, "image/png")},
        headers={"x-forwarded-for": f"10.202.0.{uuid.uuid4().int % 200 + 1}"},
    )
    assert response.status_code == 200
    db = SessionLocal()
    try:
        attachment = db.scalar(select(Attachment).where(Attachment.original_filename == "evil.png").order_by(Attachment.created_at.desc()))
        assert attachment is not None
        assert ".." not in attachment.original_filename
        assert "/" not in attachment.original_filename
    finally:
        db.close()


def test_retention_cleanup_dry_run():
    db = SessionLocal()
    try:
        tenant = Tenant(name=f"Retention {uuid.uuid4()}", document=f"R{uuid.uuid4().hex[:12]}", slug=f"retention-{uuid.uuid4().hex[:8]}", status="active")
        db.add(tenant)
        db.flush()
        report = Report(
            tenant_id=tenant.id,
            protocol=f"CDO-R{uuid.uuid4().hex[:9].upper()}",
            access_login=f"USR-R{uuid.uuid4().hex[:7].upper()}",
            access_password_hash=hash_access_password("secret"),
            is_anonymous=True,
            reporter_ip_hash="hash",
            category="outros",
            description="Retention",
            retention_due_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(report)
        db.flush()
        path = UPLOAD_ROOT / str(tenant.id) / str(report.id) / "retention.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("retention", encoding="utf-8")
        db.add(
            Attachment(
                tenant_id=tenant.id,
                report_id=report.id,
                original_filename="retention.txt",
                stored_filename="retention.txt",
                storage_path=str(path),
                mime_type="text/plain",
                size_bytes=9,
                sha256_hash="0" * 64,
                uploaded_by_type="denunciante",
            )
        )
        db.commit()
        result = retention_cleanup(db, dry_run=True)
        assert result["attachments"] >= 1
        assert path.exists()
    finally:
        db.close()


def test_cleanup_orphan_uploads_dry_run():
    db = SessionLocal()
    try:
        path = UPLOAD_ROOT / "orphan-test" / f"{uuid.uuid4()}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("orphan", encoding="utf-8")
        result = cleanup_orphan_uploads(db, dry_run=True)
        assert result["files"] >= 1
        assert path.exists()
    finally:
        db.close()
