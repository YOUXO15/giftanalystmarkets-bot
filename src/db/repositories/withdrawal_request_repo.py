"""Repository for referral withdrawal requests."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from src.db.models.withdrawal_request import WithdrawalRequest
from src.db.repositories.base import BaseRepository
from src.utils.enums import WithdrawalStatus


class WithdrawalRequestRepository(BaseRepository[WithdrawalRequest]):
    """Data access for balance withdrawal requests."""

    async def create_request(
        self,
        *,
        user_id: int,
        wallet_address: str,
        amount_ton: Decimal,
        note: str | None = None,
    ) -> WithdrawalRequest:
        """Create a pending withdrawal request."""

        request = WithdrawalRequest(
            user_id=user_id,
            wallet_address=wallet_address,
            amount_ton=amount_ton,
            status=WithdrawalStatus.PENDING,
            note=note,
        )
        return await self.add(request)

    async def get_recent_for_user(self, user_id: int, *, limit: int = 5) -> list[WithdrawalRequest]:
        """Return latest withdrawal requests for user."""

        stmt = (
            select(WithdrawalRequest)
            .where(WithdrawalRequest.user_id == user_id)
            .order_by(WithdrawalRequest.created_at.desc(), WithdrawalRequest.id.desc())
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
