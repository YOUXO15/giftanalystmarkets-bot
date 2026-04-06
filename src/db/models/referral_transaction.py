"""Internal TON balance transactions for referral system."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, CreatedAtMixin
from src.utils.enums import ReferralTransactionType

if TYPE_CHECKING:
    from src.db.models.user import User


class ReferralTransaction(CreatedAtMixin, Base):
    """Audit trail for all referral balance movements."""

    __tablename__ = "referral_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    transaction_type: Mapped[ReferralTransactionType] = mapped_column(
        SAEnum(
            ReferralTransactionType,
            name="referral_transaction_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    amount_ton: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    balance_after_ton: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    related_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    payment_invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_invoices.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="referral_transactions", foreign_keys=[user_id])
