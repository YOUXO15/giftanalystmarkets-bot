"""Initial database schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial project tables."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_users_telegram_id")),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=False)

    op.create_table(
        "ton_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ton_rates")),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "report_currency",
            sa.Enum(
                "USD",
                "EUR",
                "RUB",
                "TON",
                "USDT",
                name="user_report_currency_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="USD",
        ),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("google_sheet_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_settings_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_settings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_settings_user_id")),
    )

    op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("external_deal_id", sa.String(length=255), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("buy_price", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("sell_price", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("fee", sa.Numeric(precision=18, scale=8), nullable=False, server_default="0"),
        sa.Column("net_profit", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column(
            "currency",
            sa.Enum(
                "USD",
                "EUR",
                "RUB",
                "TON",
                "USDT",
                name="deal_currency_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="USD",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "closed",
                "cancelled",
                name="deal_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_deals_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deals")),
        sa.UniqueConstraint("external_deal_id", name=op.f("uq_deals_external_deal_id")),
    )
    op.create_index(op.f("ix_deals_external_deal_id"), "deals", ["external_deal_id"], unique=False)
    op.create_index(op.f("ix_deals_user_id"), "deals", ["user_id"], unique=False)

    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sync_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "in_progress",
                "success",
                "failed",
                name="sync_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_sync_logs_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_logs")),
    )
    op.create_index(op.f("ix_sync_logs_user_id"), "sync_logs", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop initial project tables."""

    op.drop_index(op.f("ix_sync_logs_user_id"), table_name="sync_logs")
    op.drop_table("sync_logs")
    op.drop_index(op.f("ix_deals_user_id"), table_name="deals")
    op.drop_index(op.f("ix_deals_external_deal_id"), table_name="deals")
    op.drop_table("deals")
    op.drop_table("user_settings")
    op.drop_table("ton_rates")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_table("users")
