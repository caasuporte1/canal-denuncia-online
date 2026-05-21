"""add tenant operational fields

Revision ID: 20260520_0003
Revises: 20260520_0002
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = "20260520_0003"
down_revision = "20260520_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("tenants", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("tenants", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("tenants", sa.Column("state", sa.String(length=2), nullable=True))
    op.add_column("tenants", sa.Column("complaints_handler_name", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("complaints_handler_email", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("complaints_handler_phone", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "complaints_handler_phone")
    op.drop_column("tenants", "complaints_handler_email")
    op.drop_column("tenants", "complaints_handler_name")
    op.drop_column("tenants", "state")
    op.drop_column("tenants", "city")
    op.drop_column("tenants", "address")
    op.drop_column("tenants", "email")
    op.drop_column("tenants", "phone")
