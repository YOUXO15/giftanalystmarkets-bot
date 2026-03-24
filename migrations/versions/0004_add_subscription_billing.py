"""Add subscription and payment invoice tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_add_subscription_billing"
down_revision = "0003_drop_google_sheets_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create billing tables used by Crypto Pay subscription flow."""

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "inactive",
                "active",
                "expired",
                name="subscription_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="inactive",
        ),
        sa.Column("current_period_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discount_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_subscriptions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_subscriptions")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_subscriptions_user_id")),
    )
    op.create_index(op.f("ix_user_subscriptions_user_id"), "user_subscriptions", ["user_id"], unique=False)

    op.create_table(
        "payment_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider_invoice_id", sa.Integer(), nullable=False),
        sa.Column("invoice_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "asset",
            sa.Enum(
                "USD",
                "EUR",
                "RUB",
                "TON",
                "USDT",
                name="payment_invoice_asset_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column(
            "plan_type",
            sa.Enum(
                "intro",
                "monthly",
                name="billing_plan_type_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "paid",
                "expired",
                name="payment_invoice_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("pay_url", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_payment_invoices_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_invoices")),
        sa.UniqueConstraint("provider_invoice_id", name=op.f("uq_payment_invoices_provider_invoice_id")),
    )
    op.create_index(op.f("ix_payment_invoices_provider_invoice_id"), "payment_invoices", ["provider_invoice_id"], unique=False)
    op.create_index(op.f("ix_payment_invoices_user_id"), "payment_invoices", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop billing tables."""

    op.drop_index(op.f("ix_payment_invoices_user_id"), table_name="payment_invoices")
    op.drop_index(op.f("ix_payment_invoices_provider_invoice_id"), table_name="payment_invoices")
    op.drop_table("payment_invoices")
    op.drop_index(op.f("ix_user_subscriptions_user_id"), table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
