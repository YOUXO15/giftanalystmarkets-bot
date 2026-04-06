"""Referral rewards created from paid invoices."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, CreatedAtMixin


class ReferralReward(CreatedAtMixin, Base):
    """Represents one reward payout for one paid invoice."""

    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    referred_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    payment_invoice_id: Mapped[int] = mapped_column(
        ForeignKey("payment_invoices.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    reward_percent: Mapped[Decimal] = mapped_column(Numeric(precision=6, scale=2), nullable=False)
    reward_amount_ton: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
