"""Handlers for the /help command."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.services.user_service import UserService
from src.utils.helpers import build_help_text

router = Router(name="help")


@router.message(Command("help"))
async def help_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Show bot help information."""

    language = None
    if message.from_user is not None:
        user_service = UserService(session_maker)
        language = await user_service.get_user_language(
            message.from_user.id,
            fallback_telegram_language=message.from_user.language_code,
        )

    await replace_tracked_text(
        message,
        build_help_text(language=language),
        reply_markup=get_main_menu_keyboard(language),
    )
