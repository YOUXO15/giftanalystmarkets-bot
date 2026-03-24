"""Drop Google Sheets related user settings fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_drop_google_sheets_fields"
down_revision = "0002_add_google_account_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove Google Sheets specific columns from user settings."""

    op.drop_column("user_settings", "google_account_email")
    op.drop_column("user_settings", "google_sheet_id")


def downgrade() -> None:
    """Restore Google Sheets specific columns in user settings."""

    op.add_column("user_settings", sa.Column("google_sheet_id", sa.String(length=255), nullable=True))
    op.add_column("user_settings", sa.Column("google_account_email", sa.String(length=255), nullable=True))
