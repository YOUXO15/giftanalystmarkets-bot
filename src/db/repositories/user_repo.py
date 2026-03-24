"""Repository for user entities."""

from __future__ import annotations

from sqlalchemy import select

from src.db.models.user import User
from src.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access for Telegram users."""

    async def get_by_id(self, user_id: int) -> User | None:
        """Fetch a user by primary key."""

        return await self.session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Fetch a user by Telegram identifier."""

        stmt = select(User).where(User.telegram_id == telegram_id)
        return await self.session.scalar(stmt)

    async def create(self, telegram_id: int, username: str | None, first_name: str | None) -> User:
        """Create a new user."""

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            is_active=True,
        )
        return await self.add(user)

    async def update_profile(self, user: User, username: str | None, first_name: str | None) -> User:
        """Update profile fields for an existing user."""

        user.username = username
        user.first_name = first_name
        user.is_active = True
        await self.session.flush()
        return user
