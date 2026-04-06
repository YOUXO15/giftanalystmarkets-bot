"""Repository for internal referral balance transactions."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from src.db.models.referral_transaction import ReferralTransaction
from src.db.repositories.base import BaseRepository
from src.utils.enums import ReferralTransactionType


class ReferralTransactionRepository(BaseRepository[ReferralTransaction]):
    """Data access for referral TON balance ledger."""

    async def create_transaction(
        self,
        *,
        user_id: int,
        transaction_type: ReferralTransactionType,
        amount_ton: Decimal,
        balance_after_ton: Decimal,
        related_user_id: int | None = None,
        payment_invoice_id: int | None = None,
        note: str | None = None,
    ) -> ReferralTransaction:
        """Create a balance transaction row."""

        transaction = ReferralTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount_ton=amount_ton,
            balance_after_ton=balance_after_ton,
            related_user_id=related_user_id,
            payment_invoice_id=payment_invoice_id,
            note=note,
        )
        return await self.add(transaction)

    async def get_recent_for_user(self, user_id: int, *, limit: int = 10) -> list[ReferralTransaction]:
        """Return latest transactions for user balance history."""

        stmt = (
            select(ReferralTransaction)
            .where(ReferralTransaction.user_id == user_id)
            .order_by(ReferralTransaction.created_at.desc(), ReferralTransaction.id.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
