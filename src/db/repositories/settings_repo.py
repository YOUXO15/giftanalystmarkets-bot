"""Repository for user settings."""

from __future__ import annotations

from sqlalchemy import select

from src.db.models.user_settings import UserSettings
from src.db.repositories.base import BaseRepository
from src.utils.enums import Currency, Language


class SettingsRepository(BaseRepository[UserSettings]):
    """Data access for user settings."""

    async def get_by_user_id(self, user_id: int) -> UserSettings | None:
        """Fetch settings by user identifier."""

        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return await self.session.scalar(stmt)

    async def create_default(self, user_id: int, *, preferred_language: Language = Language.RU) -> UserSettings:
        """Create default settings for a user."""

        settings = UserSettings(
            user_id=user_id,
            notifications_enabled=True,
            report_currency=Currency.USD,
            auto_sync_enabled=False,
            preferred_language=preferred_language,
        )
        return await self.add(settings)

    async def update_language(self, settings: UserSettings, language: Language) -> UserSettings:
        """Update interface language preference."""

        settings.preferred_language = language
        self.session.add(settings)
        return settings
