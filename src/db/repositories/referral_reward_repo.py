"""Repository for referral reward records."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import exists, select

from src.db.models.referral_reward import ReferralReward
from src.db.repositories.base import BaseRepository


class ReferralRewardRepository(BaseRepository[ReferralReward]):
    """Data access for referral rewards."""

    async def get_by_payment_invoice_id(self, payment_invoice_id: int) -> ReferralReward | None:
        """Fetch reward by processed invoice id."""

        stmt = select(ReferralReward).where(ReferralReward.payment_invoice_id == payment_invoice_id)
        return await self.session.scalar(stmt)

    async def has_reward_for_pair(self, referrer_user_id: int, referred_user_id: int) -> bool:
        """Return whether this invited user has already yielded at least one reward."""

        stmt = select(
            exists().where(
                ReferralReward.referrer_user_id == referrer_user_id,
                ReferralReward.referred_user_id == referred_user_id,
            )
        )
        return bool(await self.session.scalar(stmt))

    async def create_reward(
        self,
        *,
        referrer_user_id: int,
        referred_user_id: int,
        payment_invoice_id: int,
        reward_percent: Decimal,
        reward_amount_ton: Decimal,
    ) -> ReferralReward:
        """Create a reward row for one paid invoice."""

        reward = ReferralReward(
            referrer_user_id=referrer_user_id,
            referred_user_id=referred_user_id,
            payment_invoice_id=payment_invoice_id,
            reward_percent=reward_percent,
            reward_amount_ton=reward_amount_ton,
        )
        return await self.add(reward)
