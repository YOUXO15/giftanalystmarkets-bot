"""TON exchange rate model."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, CreatedAtMixin


class TonRate(CreatedAtMixin, Base):
    """Stores snapshots of TON exchange rates."""

    __tablename__ = "ton_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
