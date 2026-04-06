"""Handlers for statistics commands."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.bot.subscription_guard import ensure_paid_access
from src.config.settings import Settings
from src.services.stats_service import StatsService
from src.services.user_service import UserService
from src.utils.i18n import button_variants

router = Router(name="stats")


@router.message(Command("stats"))
@router.message(F.text.in_(button_variants("stats")))
async def stats_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show aggregated statistics."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    stats_service = StatsService(session_maker)
    response_text = await stats_service.build_stats_message(message.from_user.id)
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_main_menu_keyboard(language),
    )
