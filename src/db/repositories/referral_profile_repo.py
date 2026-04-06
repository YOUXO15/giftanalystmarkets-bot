"""Repository for referral profile records."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from src.db.models.referral_profile import ReferralProfile
from src.db.repositories.base import BaseRepository


class ReferralProfileRepository(BaseRepository[ReferralProfile]):
    """Data access for referral profiles."""

    async def get_by_user_id(self, user_id: int) -> ReferralProfile | None:
        """Fetch profile by owner user id."""

        stmt = select(ReferralProfile).where(ReferralProfile.user_id == user_id)
        return await self.session.scalar(stmt)

    async def get_by_referral_code(self, referral_code: str) -> ReferralProfile | None:
        """Fetch profile by referral code."""

        stmt = select(ReferralProfile).where(ReferralProfile.referral_code == referral_code)
        return await self.session.scalar(stmt)

    async def create_profile(
        self,
        *,
        user_id: int,
        referral_code: str,
        referrer_user_id: int | None = None,
    ) -> ReferralProfile:
        """Create a profile with zeroed balances."""

        profile = ReferralProfile(
            user_id=user_id,
            referral_code=referral_code,
            referrer_user_id=referrer_user_id,
            available_balance_ton=Decimal("0"),
            total_earned_ton=Decimal("0"),
            paid_referrals_count=0,
        )
        return await self.add(profile)

    async def count_total_referrals(self, referrer_user_id: int) -> int:
        """Count linked users for a given referrer."""

        stmt = select(func.count(ReferralProfile.id)).where(
            ReferralProfile.referrer_user_id == referrer_user_id
        )
        result = await self.session.scalar(stmt)
        return int(result or 0)
