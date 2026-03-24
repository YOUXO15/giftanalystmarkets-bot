"""Add manual deal capture fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_add_manual_deal_fields"
down_revision = "0005_add_export_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add fields required for manual purchase intake and sale matching."""

    op.add_column("deals", sa.Column("gift_number", sa.String(length=100), nullable=True))
    op.add_column("deals", sa.Column("gift_url", sa.String(length=1024), nullable=True))
    op.add_column("deals", sa.Column("marketplace", sa.String(length=255), nullable=True))
    op.add_column("deals", sa.Column("ton_usd_rate", sa.Numeric(18, 8), nullable=True))


def downgrade() -> None:
    """Drop manual capture fields from deals table."""

    op.drop_column("deals", "ton_usd_rate")
    op.drop_column("deals", "marketplace")
    op.drop_column("deals", "gift_url")
    op.drop_column("deals", "gift_number")
