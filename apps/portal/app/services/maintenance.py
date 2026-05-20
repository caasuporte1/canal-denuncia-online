from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.report import Report
from app.services.audit import audit_event
from app.services.upload import UPLOAD_ROOT


def retention_cleanup(db: Session, *, dry_run: bool = True) -> dict:
    now = datetime.now(timezone.utc)
    attachments = db.scalars(
        select(Attachment)
        .join(Report, Attachment.report_id == Report.id)
        .where(Report.retention_due_at.is_not(None), Report.retention_due_at <= now, Attachment.deleted_at.is_(None))
    ).all()
    removed_files = 0
    for attachment in attachments:
        path = Path(attachment.storage_path)
        if not dry_run and path.is_file():
            path.unlink()
            removed_files += 1
        elif path.is_file():
            removed_files += 1
        if not dry_run:
            attachment.deleted_at = now
    if not dry_run:
        audit_event(db, "retention_cleanup_executed", metadata={"attachments": len(attachments), "removed_files": removed_files})
        db.commit()
    return {"dry_run": dry_run, "attachments": len(attachments), "files": removed_files}


def cleanup_orphan_uploads(db: Session, *, dry_run: bool = True) -> dict:
    referenced = {row[0] for row in db.execute(select(Attachment.storage_path).where(Attachment.deleted_at.is_(None))).all()}
    deleted = {row[0] for row in db.execute(select(Attachment.storage_path).where(Attachment.deleted_at.is_not(None))).all()}
    candidates: list[Path] = []
    if UPLOAD_ROOT.exists():
        for path in UPLOAD_ROOT.rglob("*"):
            if path.is_file() and (str(path) not in referenced or str(path) in deleted):
                candidates.append(path)
    if not dry_run:
        for path in candidates:
            path.unlink(missing_ok=True)
    return {"dry_run": dry_run, "files": len(candidates)}
