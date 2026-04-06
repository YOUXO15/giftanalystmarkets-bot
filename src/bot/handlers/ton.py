"""Handlers for TON rate commands."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.bot.subscription_guard import ensure_paid_access
from src.config.settings import Settings
from src.services.ton_service import TonService
from src.services.user_service import UserService
from src.utils.i18n import button_variants

router = Router(name="ton")


@router.message(Command("ton"))
@router.message(F.text.in_(button_variants("ton")))
async def ton_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show the current TON rate or fallback snapshot."""

    if not await ensure_paid_access(message, session_maker, settings):
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    ton_service = TonService(session_maker, settings)
    response_text = await ton_service.build_rate_message()
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_main_menu_keyboard(language),
    )
