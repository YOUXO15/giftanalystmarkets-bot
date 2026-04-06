"""User-related business logic."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models.user import User
from src.db.models.user_settings import UserSettings
from src.db.models.user_subscription import UserSubscription
from src.db.repositories.settings_repo import SettingsRepository
from src.db.repositories.subscription_repo import SubscriptionRepository
from src.db.repositories.user_repo import UserRepository
from src.utils.enums import Language
from src.utils.i18n import language_from_telegram_code, t
from src.utils.helpers import build_registration_required_text


@dataclass(slots=True)
class UserRegistrationResult:
    """Represents the result of /start registration flow."""

    user: User
    settings: UserSettings
    subscription: UserSubscription
    is_new_user: bool


class UserService:
    """Application service for user registration and preferences."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def register_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        telegram_language_code: str | None = None,
    ) -> UserRegistrationResult:
        """Create a user and default settings if they do not exist yet."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            settings_repo = SettingsRepository(session)
            subscription_repo = SubscriptionRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                is_new_user = user is None
                if user is None:
                    user = await user_repo.create(telegram_id, username, first_name)
                else:
                    user = await user_repo.update_profile(user, username, first_name)

                settings = await settings_repo.get_by_user_id(user.id)
                if settings is None:
                    settings = await settings_repo.create_default(
                        user.id,
                        preferred_language=language_from_telegram_code(telegram_language_code),
                    )

                subscription = await subscription_repo.get_by_user_id(user.id)
                if subscription is None:
                    subscription = await subscription_repo.create_default(user.id)

            return UserRegistrationResult(
                user=user,
                settings=settings,
                subscription=subscription,
                is_new_user=is_new_user,
            )

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Fetch a user by Telegram identifier."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            return await user_repo.get_by_telegram_id(telegram_id)

    async def get_user_language(
        self,
        telegram_id: int,
        *,
        fallback_telegram_language: str | None = None,
    ) -> Language:
        """Resolve user's preferred language from settings."""

        fallback = language_from_telegram_code(fallback_telegram_language)
        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            settings_repo = SettingsRepository(session)

            user = await user_repo.get_by_telegram_id(telegram_id)
            if user is None:
                return fallback

            settings = await settings_repo.get_by_user_id(user.id)
            if settings is None:
                return fallback

            return settings.preferred_language

    async def update_user_language(self, telegram_id: int, language: Language) -> bool:
        """Persist selected interface language for a user."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            settings_repo = SettingsRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return False

                settings = await settings_repo.get_by_user_id(user.id)
                if settings is None:
                    settings = await settings_repo.create_default(user.id, preferred_language=language)
                else:
                    await settings_repo.update_language(settings, language)
            return True

    async def build_settings_overview(
        self,
        telegram_id: int,
        *,
        fallback_telegram_language: str | None = None,
    ) -> str:
        """Build a user-facing settings overview message."""

        fallback = language_from_telegram_code(fallback_telegram_language)
        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            settings_repo = SettingsRepository(session)
            subscription_repo = SubscriptionRepository(session)

            user = await user_repo.get_by_telegram_id(telegram_id)
            if user is None:
                return build_registration_required_text(language=fallback)

            settings = await settings_repo.get_by_user_id(user.id)
            if settings is None:
                return t("settings_not_found", fallback)

            language = settings.preferred_language
            subscription = await subscription_repo.get_by_user_id(user.id)
            subscription_status = t("settings_subscription_inactive", language)
            if subscription is not None and subscription.current_period_ends_at is not None:
                status_label = {
                    "active": t("settings_subscription_active", language),
                    "expired": t("settings_subscription_expired", language),
                    "inactive": t("settings_subscription_inactive", language),
                }.get(subscription.status.value, subscription.status.value)
                subscription_status = t(
                    "settings_subscription_until",
                    language,
                    status=status_label,
                    date=subscription.current_period_ends_at.strftime("%d.%m.%Y %H:%M UTC"),
                )

            return (
                f"{t('settings_title', language)}\n\n"
                f"{t('settings_label_currency', language)}: {settings.report_currency.value}\n"
                f"{t('settings_label_language', language)}: {language.value.upper()}\n"
                f"{t('settings_label_subscription', language)}: {subscription_status}"
            )
