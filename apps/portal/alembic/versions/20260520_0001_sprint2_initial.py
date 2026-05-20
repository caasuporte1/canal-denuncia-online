"""sprint 2 initial schema

Revision ID: 20260520_0001
Revises:
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260520_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("document", sa.String(length=32), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document", name="uq_tenants_document"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin_triton', 'tenant_admin', 'tenant_user')", name="ck_users_role"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("protocol", sa.String(length=32), nullable=False, unique=True),
        sa.Column("access_login", sa.String(length=32), nullable=False, unique=True),
        sa.Column("access_password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False),
        sa.Column("reporter_name", sa.String(length=255), nullable=True),
        sa.Column("reporter_email", sa.String(length=255), nullable=True),
        sa.Column("reporter_phone", sa.String(length=40), nullable=True),
        sa.Column("reporter_ip_hash", sa.String(length=64), nullable=True),
        sa.Column("reporter_ip_clear", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="recebida"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column("retention_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('recebida', 'em_triagem', 'em_apuracao', 'aguardando_resposta', 'concluida', 'arquivada')",
            name="ck_reports_status",
        ),
        sa.CheckConstraint(
            "category IN ('assedio_moral', 'assedio_sexual', 'discriminacao', 'seguranca_do_trabalho', 'conduta_etica', 'outros')",
            name="ck_reports_category",
        ),
    )
    op.execute("CREATE INDEX ix_reports_tenant_status_created_at ON reports (tenant_id, status, created_at DESC)")
    op.create_index("ix_reports_protocol", "reports", ["protocol"])
    op.create_index("ix_reports_retention_due_at_not_null", "reports", ["retention_due_at"], postgresql_where=sa.text("retention_due_at IS NOT NULL"))

    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("uploaded_by_type IN ('denunciante', 'empresa', 'admin_triton', 'sistema')", name="ck_attachments_uploaded_by_type"),
    )
    op.create_index("ix_attachments_report_active", "attachments", ["report_id"], postgresql_where=sa.text("deleted_at IS NULL"))

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("CREATE INDEX ix_audit_logs_tenant_created_at ON audit_logs (tenant_id, created_at DESC)")
    op.create_index("ix_audit_logs_report_not_null", "audit_logs", ["report_id"], postgresql_where=sa.text("report_id IS NOT NULL"))

    op.create_table(
        "email_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_notifications_pending", "email_notifications", ["status", "created_at"], postgresql_where=sa.text("status = 'pending'"))


def downgrade() -> None:
    op.drop_table("email_notifications")
    op.drop_table("audit_logs")
    op.drop_table("attachments")
    op.drop_table("reports")
    op.drop_table("users")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
