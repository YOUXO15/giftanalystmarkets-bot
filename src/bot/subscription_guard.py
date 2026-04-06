"""Shared helper for protecting paid analytics features."""

from __future__ import annotations

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.subscription_menu import get_subscription_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.config.settings import Settings
from src.services.billing_service import BillingService
from src.services.user_service import UserService


async def ensure_paid_access(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> bool:
    """Return True when the user has an active subscription, otherwise show the paywall."""

    if message.from_user is None:
        return False

    billing_service = BillingService(session_maker, settings)
    access = await billing_service.ensure_analytics_access(message.from_user.id)
    if access.allowed:
        return True

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    await replace_tracked_text(
        message,
        access.message,
        reply_markup=get_subscription_menu_keyboard(language),
    )
    return False
