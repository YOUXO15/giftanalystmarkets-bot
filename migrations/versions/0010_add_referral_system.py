"""Add referral system tables and withdrawal requests."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_add_referral_system"
down_revision = "0009_add_preferred_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create referral profile, reward, transaction, and withdrawal tables."""

    op.create_table(
        "referral_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("referral_code", sa.String(length=64), nullable=False),
        sa.Column("referrer_user_id", sa.Integer(), nullable=True),
        sa.Column("available_balance_ton", sa.Numeric(precision=18, scale=8), nullable=False, server_default="0"),
        sa.Column("total_earned_ton", sa.Numeric(precision=18, scale=8), nullable=False, server_default="0"),
        sa.Column("paid_referrals_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_referral_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referrer_user_id"],
            ["users.id"],
            name=op.f("fk_referral_profiles_referrer_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referral_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_referral_profiles_user_id")),
        sa.UniqueConstraint("referral_code", name=op.f("uq_referral_profiles_referral_code")),
    )
    op.create_index(op.f("ix_referral_profiles_user_id"), "referral_profiles", ["user_id"], unique=False)
    op.create_index(op.f("ix_referral_profiles_referral_code"), "referral_profiles", ["referral_code"], unique=False)
    op.create_index(
        op.f("ix_referral_profiles_referrer_user_id"),
        "referral_profiles",
        ["referrer_user_id"],
        unique=False,
    )

    op.create_table(
        "referral_rewards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referrer_user_id", sa.Integer(), nullable=False),
        sa.Column("referred_user_id", sa.Integer(), nullable=False),
        sa.Column("payment_invoice_id", sa.Integer(), nullable=False),
        sa.Column("reward_percent", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("reward_amount_ton", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["referrer_user_id"],
            ["users.id"],
            name=op.f("fk_referral_rewards_referrer_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referred_user_id"],
            ["users.id"],
            name=op.f("fk_referral_rewards_referred_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["payment_invoice_id"],
            ["payment_invoices.id"],
            name=op.f("fk_referral_rewards_payment_invoice_id_payment_invoices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referral_rewards")),
        sa.UniqueConstraint("payment_invoice_id", name=op.f("uq_referral_rewards_payment_invoice_id")),
    )
    op.create_index(op.f("ix_referral_rewards_referrer_user_id"), "referral_rewards", ["referrer_user_id"], unique=False)
    op.create_index(op.f("ix_referral_rewards_referred_user_id"), "referral_rewards", ["referred_user_id"], unique=False)
    op.create_index(op.f("ix_referral_rewards_payment_invoice_id"), "referral_rewards", ["payment_invoice_id"], unique=False)

    op.create_table(
        "referral_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "reward",
                "subscription_payment",
                "gift_subscription",
                "withdrawal_request",
                name="referral_transaction_type_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("amount_ton", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("balance_after_ton", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("related_user_id", sa.Integer(), nullable=True),
        sa.Column("payment_invoice_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_referral_transactions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_user_id"],
            ["users.id"],
            name=op.f("fk_referral_transactions_related_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["payment_invoice_id"],
            ["payment_invoices.id"],
            name=op.f("fk_referral_transactions_payment_invoice_id_payment_invoices"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referral_transactions")),
    )
    op.create_index(op.f("ix_referral_transactions_user_id"), "referral_transactions", ["user_id"], unique=False)
    op.create_index(op.f("ix_referral_transactions_related_user_id"), "referral_transactions", ["related_user_id"], unique=False)
    op.create_index(
        op.f("ix_referral_transactions_payment_invoice_id"),
        "referral_transactions",
        ["payment_invoice_id"],
        unique=False,
    )

    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("wallet_address", sa.String(length=255), nullable=False),
        sa.Column("amount_ton", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="withdrawal_status_enum",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_withdrawal_requests_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_withdrawal_requests")),
    )
    op.create_index(op.f("ix_withdrawal_requests_user_id"), "withdrawal_requests", ["user_id"], unique=False)

    op.alter_column("referral_profiles", "available_balance_ton", server_default=None)
    op.alter_column("referral_profiles", "total_earned_ton", server_default=None)
    op.alter_column("referral_profiles", "paid_referrals_count", server_default=None)
    op.alter_column("withdrawal_requests", "status", server_default=None)


def downgrade() -> None:
    """Drop referral and withdrawal tables."""

    op.drop_index(op.f("ix_withdrawal_requests_user_id"), table_name="withdrawal_requests")
    op.drop_table("withdrawal_requests")

    op.drop_index(op.f("ix_referral_transactions_payment_invoice_id"), table_name="referral_transactions")
    op.drop_index(op.f("ix_referral_transactions_related_user_id"), table_name="referral_transactions")
    op.drop_index(op.f("ix_referral_transactions_user_id"), table_name="referral_transactions")
    op.drop_table("referral_transactions")

    op.drop_index(op.f("ix_referral_rewards_payment_invoice_id"), table_name="referral_rewards")
    op.drop_index(op.f("ix_referral_rewards_referred_user_id"), table_name="referral_rewards")
    op.drop_index(op.f("ix_referral_rewards_referrer_user_id"), table_name="referral_rewards")
    op.drop_table("referral_rewards")

    op.drop_index(op.f("ix_referral_profiles_referrer_user_id"), table_name="referral_profiles")
    op.drop_index(op.f("ix_referral_profiles_referral_code"), table_name="referral_profiles")
    op.drop_index(op.f("ix_referral_profiles_user_id"), table_name="referral_profiles")
    op.drop_table("referral_profiles")
