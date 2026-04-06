"""Referral profile and internal balance for a user."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class ReferralProfile(TimestampMixin, Base):
    """Stores referral link settings and TON balance for a user."""

    __tablename__ = "referral_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    referral_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    referrer_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    available_balance_ton: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8),
        nullable=False,
        default=Decimal("0"),
    )
    total_earned_ton: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8),
        nullable=False,
        default=Decimal("0"),
    )
    paid_referrals_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(
        back_populates="referral_profile",
        foreign_keys=[user_id],
    )
