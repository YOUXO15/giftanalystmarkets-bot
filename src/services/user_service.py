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
from src.utils.formatters import format_bool_flag
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
                    settings = await settings_repo.create_default(user.id)

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

    async def build_settings_overview(self, telegram_id: int) -> str:
        """Build a user-facing settings overview message."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            settings_repo = SettingsRepository(session)
            subscription_repo = SubscriptionRepository(session)

            user = await user_repo.get_by_telegram_id(telegram_id)
            if user is None:
                return build_registration_required_text()

            settings = await settings_repo.get_by_user_id(user.id)
            if settings is None:
                return "Настройки не найдены. Выполни /start, чтобы инициализировать профиль."

            subscription = await subscription_repo.get_by_user_id(user.id)
            subscription_status = "не активирована"
            if subscription is not None and subscription.current_period_ends_at is not None:
                status_label = {
                    "active": "активна",
                    "expired": "истекла",
                    "inactive": "не активирована",
                }.get(subscription.status.value, subscription.status.value)
                subscription_status = (
                    f"{status_label} до {subscription.current_period_ends_at.strftime('%d.%m.%Y %H:%M UTC')}"
                )

            return (
                "<b>Настройки пользователя</b>\n\n"
                f"Уведомления: {format_bool_flag(settings.notifications_enabled)}\n"
                f"Автосинхронизация: {format_bool_flag(settings.auto_sync_enabled)}\n"
                f"Валюта отчётов: {settings.report_currency.value}\n"
                f"Подписка: {subscription_status}"
            )
