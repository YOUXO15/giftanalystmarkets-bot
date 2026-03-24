"""User database model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.deal import Deal
    from src.db.models.export_log import ExportLog
    from src.db.models.payment_invoice import PaymentInvoice
    from src.db.models.sync_log import SyncLog
    from src.db.models.user_settings import UserSettings
    from src.db.models.user_subscription import UserSubscription


class User(TimestampMixin, Base):
    """Represents a Telegram bot user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    settings: Mapped["UserSettings | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    subscription: Mapped["UserSubscription | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    deals: Mapped[list["Deal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    export_logs: Mapped[list["ExportLog"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payment_invoices: Mapped[list["PaymentInvoice"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
