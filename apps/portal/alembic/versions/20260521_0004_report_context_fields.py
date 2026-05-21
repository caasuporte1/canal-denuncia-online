"""add report context fields

Revision ID: 20260521_0004
Revises: 20260520_0003
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa

revision = "20260521_0004"
down_revision = "20260520_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("involved_department", sa.String(length=255), nullable=True))
    op.add_column("reports", sa.Column("involved_location", sa.String(length=255), nullable=True))
    op.add_column("reports", sa.Column("involved_role", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "involved_role")
    op.drop_column("reports", "involved_location")
    op.drop_column("reports", "involved_department")
