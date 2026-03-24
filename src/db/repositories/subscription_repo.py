"""Repository for subscription entities."""

from __future__ import annotations

from sqlalchemy import select

from src.db.models.user_subscription import UserSubscription
from src.db.repositories.base import BaseRepository
from src.utils.enums import SubscriptionStatus


class SubscriptionRepository(BaseRepository[UserSubscription]):
    """Data access for user subscription records."""

    async def get_by_user_id(self, user_id: int) -> UserSubscription | None:
        """Fetch subscription by user identifier."""

        stmt = select(UserSubscription).where(UserSubscription.user_id == user_id)
        return await self.session.scalar(stmt)

    async def create_default(self, user_id: int) -> UserSubscription:
        """Create an inactive subscription record for a new user."""

        subscription = UserSubscription(
            user_id=user_id,
            status=SubscriptionStatus.INACTIVE,
            discount_consumed=False,
        )
        return await self.add(subscription)
