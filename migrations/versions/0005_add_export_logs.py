"""Add export logs for daily export quota."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_add_export_logs"
down_revision = "0004_add_subscription_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create export_logs table for daily export rate limiting."""

    op.create_table(
        "export_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "export_format",
            sa.Enum(
                "csv",
                "xlsx",
                name="export_log_format_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("rows_exported", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_export_logs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_logs")),
    )
    op.create_index(op.f("ix_export_logs_user_id"), "export_logs", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop export_logs table."""

    op.drop_index(op.f("ix_export_logs_user_id"), table_name="export_logs")
    op.drop_table("export_logs")
