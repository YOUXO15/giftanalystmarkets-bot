"""Add sale TON/USD rate snapshot to deals."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_add_sale_ton_usd_rate"
down_revision = "0007_add_sale_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add per-sale TON/USD snapshot column."""

    op.add_column("deals", sa.Column("sale_ton_usd_rate", sa.Numeric(18, 8), nullable=True))


def downgrade() -> None:
    """Drop per-sale TON/USD snapshot column."""

    op.drop_column("deals", "sale_ton_usd_rate")
