import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_notification import EmailNotification
from app.models.report import Report
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit import audit_event


def notify_tenant_admins(db: Session, tenant: Tenant, report: Report, ip_address: str | None, user_agent: str | None) -> None:
    admins = db.scalars(
        select(User).where(
            User.tenant_id == tenant.id,
            User.role == "tenant_admin",
            User.status == "active",
        )
    ).all()
    for admin in admins:
        notification = EmailNotification(
            tenant_id=tenant.id,
            report_id=report.id,
            recipient_email=admin.email,
            subject="Nova denúncia recebida",
            status="pending",
        )
        db.add(notification)
        audit_event(
            db,
            "email_notification_created",
            tenant_id=tenant.id,
            report_id=report.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"recipient_role": "tenant_admin"},
        )
        db.flush()
        _send_notification(notification, tenant, report)


def _send_notification(notification: EmailNotification, tenant: Tenant, report: Report) -> None:
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_from_email]):
        notification.status = "failed"
        notification.error_message = "SMTP não configurado"
        return

    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = notification.recipient_email
    message["Subject"] = notification.subject
    message.set_content(
        "\n".join(
            [
                f"Uma nova denúncia foi recebida para {tenant.name}.",
                f"Protocolo: {report.protocol}",
                f"Portal: https://{settings.domain_portal}/{tenant.slug}",
                f"Data/hora UTC: {datetime.now(timezone.utc).isoformat()}",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        notification.status = "sent"
        notification.sent_at = datetime.now(timezone.utc)
    except Exception as exc:
        notification.status = "failed"
        notification.error_message = exc.__class__.__name__
