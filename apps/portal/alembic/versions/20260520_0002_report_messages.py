"""add report messages

Revision ID: 20260520_0002
Revises: 20260520_0001
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260520_0002"
down_revision = "20260520_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_type", sa.String(length=30), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sender_type IN ('empresa', 'admin_triton', 'sistema')", name="ck_report_messages_sender_type"),
    )
    op.create_index("ix_report_messages_report_created_at", "report_messages", ["report_id", "created_at"])


def downgrade() -> None:
    op.drop_table("report_messages")
