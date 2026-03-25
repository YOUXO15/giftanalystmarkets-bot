"""Add sale marketplace to deals.

Revision ID: 0007_add_sale_marketplace
Revises: 0006_add_manual_deal_fields
Create Date: 2026-03-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_add_sale_marketplace"
down_revision = "0006_add_manual_deal_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add separate marketplace field for sale-side notifications."""

    op.add_column("deals", sa.Column("sale_marketplace", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove sale-side marketplace field."""

    op.drop_column("deals", "sale_marketplace")
