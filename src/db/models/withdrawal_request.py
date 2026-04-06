"""Withdrawal requests from the internal referral balance."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, TimestampMixin
from src.utils.enums import WithdrawalStatus

if TYPE_CHECKING:
    from src.db.models.user import User


class WithdrawalRequest(TimestampMixin, Base):
    """Represents a user request to withdraw TON from internal balance."""

    __tablename__ = "withdrawal_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    wallet_address: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_ton: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    status: Mapped[WithdrawalStatus] = mapped_column(
        SAEnum(
            WithdrawalStatus,
            name="withdrawal_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=WithdrawalStatus.PENDING,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="withdrawal_requests", foreign_keys=[user_id])
