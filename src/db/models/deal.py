"""Deal database model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, TimestampMixin
from src.utils.enums import Currency, DealStatus

if TYPE_CHECKING:
    from src.db.models.user import User


class Deal(TimestampMixin, Base):
    """Represents a manually tracked gift deal."""

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    external_deal_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gift_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gift_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    marketplace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sale_marketplace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    buy_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    sell_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"), nullable=False)
    net_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    ton_usd_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    sale_ton_usd_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(
            Currency,
            name="deal_currency_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=Currency.USD,
        nullable=False,
    )
    status: Mapped[DealStatus] = mapped_column(
        SAEnum(
            DealStatus,
            name="deal_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DealStatus.OPEN,
        nullable=False,
    )
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="deals")
