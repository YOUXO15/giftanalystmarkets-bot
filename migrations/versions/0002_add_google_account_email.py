"""Add google_account_email to user_settings."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_google_account_email"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add google account email column used for personal Sheets access."""

    op.add_column("user_settings", sa.Column("google_account_email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Drop google account email column."""

    op.drop_column("user_settings", "google_account_email")

