"""Repository for Crypto Pay invoices."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from src.db.models.payment_invoice import PaymentInvoice
from src.db.repositories.base import BaseRepository
from src.utils.enums import BillingPlanType, Currency, PaymentInvoiceStatus


class PaymentInvoiceRepository(BaseRepository[PaymentInvoice]):
    """Data access for locally tracked payment invoices."""

    async def get_by_provider_invoice_id(self, provider_invoice_id: int) -> PaymentInvoice | None:
        """Fetch an invoice by the provider-side identifier."""

        stmt = select(PaymentInvoice).where(PaymentInvoice.provider_invoice_id == provider_invoice_id)
        return await self.session.scalar(stmt)

    async def get_latest_active_for_user(self, user_id: int) -> PaymentInvoice | None:
        """Return the most recent active invoice for a user."""

        stmt = (
            select(PaymentInvoice)
            .where(
                PaymentInvoice.user_id == user_id,
                PaymentInvoice.status == PaymentInvoiceStatus.ACTIVE,
            )
            .order_by(PaymentInvoice.created_at.desc(), PaymentInvoice.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def get_latest_for_user(self, user_id: int) -> PaymentInvoice | None:
        """Return the latest invoice for a user regardless of status."""

        stmt = (
            select(PaymentInvoice)
            .where(PaymentInvoice.user_id == user_id)
            .order_by(PaymentInvoice.created_at.desc(), PaymentInvoice.id.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def create_invoice(
        self,
        *,
        user_id: int,
        provider_invoice_id: int,
        invoice_hash: str,
        asset: Currency,
        amount: Decimal,
        plan_type: BillingPlanType,
        status: PaymentInvoiceStatus,
        pay_url: str,
        description: str | None,
        payload: str | None,
        expires_at,
        paid_at,
    ) -> PaymentInvoice:
        """Persist a newly created provider invoice."""

        invoice = PaymentInvoice(
            user_id=user_id,
            provider_invoice_id=provider_invoice_id,
            invoice_hash=invoice_hash,
            asset=asset,
            amount=amount,
            plan_type=plan_type,
            status=status,
            pay_url=pay_url,
            description=description,
            payload=payload,
            expires_at=expires_at,
            paid_at=paid_at,
        )
        return await self.add(invoice)
