#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.email_notification import EmailNotification
from app.models.report import Report
from app.models.report_message import ReportMessage
from app.models.tenant import Tenant
from app.models.user import User
from app.services.upload import UPLOAD_ROOT


ROOT_ADMIN_EMAIL = "root@triton.local"


def _safe_upload_path(path_value: str) -> Path | None:
    try:
        path = Path(path_value).resolve()
        root = UPLOAD_ROOT.resolve()
        path.relative_to(root)
        return path
    except (OSError, ValueError):
        return None


def _cleanup_empty_dirs() -> None:
    if not UPLOAD_ROOT.exists():
        return
    for path in sorted(UPLOAD_ROOT.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def main() -> int:
    db = SessionLocal()
    try:
        root_admin = db.scalar(select(User).where(User.email == ROOT_ADMIN_EMAIL, User.role == "admin_triton"))
        if not root_admin:
            print(f"ERRO: admin Triton obrigatório não encontrado: {ROOT_ADMIN_EMAIL}")
            return 1

        upload_paths = [
            path
            for path_value in db.scalars(select(Attachment.storage_path)).all()
            if path_value and (path := _safe_upload_path(path_value))
        ]

        counts_before = {
            "tenants": db.scalar(select(func.count()).select_from(Tenant)) or 0,
            "reports": db.scalar(select(func.count()).select_from(Report)) or 0,
            "report_messages": db.scalar(select(func.count()).select_from(ReportMessage)) or 0,
            "attachments": db.scalar(select(func.count()).select_from(Attachment)) or 0,
            "email_notifications": db.scalar(select(func.count()).select_from(EmailNotification)) or 0,
            "audit_logs": db.scalar(select(func.count()).select_from(AuditLog)) or 0,
            "tenant_users": db.scalar(select(func.count()).select_from(User).where(User.role.in_(("tenant_admin", "tenant_user")))) or 0,
        }

        db.execute(delete(AuditLog))
        db.execute(delete(EmailNotification))
        db.execute(delete(ReportMessage))
        db.execute(delete(Attachment))
        db.execute(delete(Report))
        db.execute(delete(User).where(User.role.in_(("tenant_admin", "tenant_user"))))
        db.execute(delete(Tenant))
        db.commit()

        removed_files = 0
        for path in upload_paths:
            if path.is_file():
                path.unlink()
                removed_files += 1
        _cleanup_empty_dirs()

        remaining = {
            "tenants": db.scalar(select(func.count()).select_from(Tenant)) or 0,
            "reports": db.scalar(select(func.count()).select_from(Report)) or 0,
            "tenant_users": db.scalar(select(func.count()).select_from(User).where(User.role.in_(("tenant_admin", "tenant_user")))) or 0,
            "root_admin": db.scalar(select(func.count()).select_from(User).where(User.email == ROOT_ADMIN_EMAIL, User.role == "admin_triton")) or 0,
        }

        print("Reset de dados demo concluído.")
        print(f"Antes: {counts_before}")
        print(f"Arquivos físicos removidos: {removed_files}")
        print(f"Depois: {remaining}")
        if remaining["tenants"] or remaining["reports"] or remaining["tenant_users"] or remaining["root_admin"] != 1:
            print("ERRO: validação pós-reset falhou.")
            return 1
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
