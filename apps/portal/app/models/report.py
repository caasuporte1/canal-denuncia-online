import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('recebida', 'em_triagem', 'em_apuracao', 'aguardando_resposta', 'concluida', 'arquivada')",
            name="ck_reports_status",
        ),
        CheckConstraint(
            "category IN ('assedio_moral', 'assedio_sexual', 'discriminacao', 'seguranca_do_trabalho', 'conduta_etica', 'outros')",
            name="ck_reports_category",
        ),
        Index("ix_reports_tenant_status_created_at", "tenant_id", "status", "created_at"),
        Index("ix_reports_protocol", "protocol"),
        Index("ix_reports_retention_due_at_not_null", "retention_due_at", postgresql_where=text("retention_due_at IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    protocol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    access_login: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    access_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reporter_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporter_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reporter_ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reporter_ip_clear: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    involved_department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    involved_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    involved_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="recebida")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="reports")
    attachments = relationship("Attachment", back_populates="report", cascade="all, delete-orphan")
    messages = relationship("ReportMessage", back_populates="report", cascade="all, delete-orphan")
