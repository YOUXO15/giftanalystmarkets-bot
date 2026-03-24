"""Repository for user settings."""

from __future__ import annotations

from sqlalchemy import select

from src.db.models.user_settings import UserSettings
from src.db.repositories.base import BaseRepository
from src.utils.enums import Currency


class SettingsRepository(BaseRepository[UserSettings]):
    """Data access for user settings."""

    async def get_by_user_id(self, user_id: int) -> UserSettings | None:
        """Fetch settings by user identifier."""

        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return await self.session.scalar(stmt)

    async def create_default(self, user_id: int) -> UserSettings:
        """Create default settings for a user."""

        settings = UserSettings(
            user_id=user_id,
            notifications_enabled=True,
            report_currency=Currency.USD,
            auto_sync_enabled=False,
        )
        return await self.add(settings)
