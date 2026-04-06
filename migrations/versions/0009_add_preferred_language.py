"""Add preferred interface language to user settings."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_add_preferred_language"
down_revision = "0008_add_sale_ton_usd_rate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add preferred_language column to user_settings."""

    op.add_column(
        "user_settings",
        sa.Column(
            "preferred_language",
            sa.String(length=8),
            nullable=False,
            server_default="ru",
        ),
    )
    op.alter_column("user_settings", "preferred_language", server_default=None)


def downgrade() -> None:
    """Drop preferred_language column from user_settings."""

    op.drop_column("user_settings", "preferred_language")
