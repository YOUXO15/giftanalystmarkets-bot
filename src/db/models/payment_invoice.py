"""Tracked Crypto Pay invoices for subscription billing."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, TimestampMixin
from src.utils.enums import BillingPlanType, Currency, PaymentInvoiceStatus

if TYPE_CHECKING:
    from src.db.models.user import User


class PaymentInvoice(TimestampMixin, Base):
    """Represents a subscription invoice created in Crypto Pay."""

    __tablename__ = "payment_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider_invoice_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)
    invoice_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    asset: Mapped[Currency] = mapped_column(
        SAEnum(
            Currency,
            name="payment_invoice_asset_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    plan_type: Mapped[BillingPlanType] = mapped_column(
        SAEnum(
            BillingPlanType,
            name="billing_plan_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[PaymentInvoiceStatus] = mapped_column(
        SAEnum(
            PaymentInvoiceStatus,
            name="payment_invoice_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    pay_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payment_invoices")
