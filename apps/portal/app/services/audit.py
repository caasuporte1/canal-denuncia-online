from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def audit_event(
    db: Session,
    event_type: str,
    *,
    tenant_id=None,
    user_id=None,
    report_id=None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        report_id=report_id,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
    db.add(entry)
    return entry
