"""Handlers for the /start command."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import send_and_track_text
from src.services.user_service import UserService
from src.utils.helpers import build_welcome_text

router = Router(name="start")


@router.message(CommandStart())
async def start_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Register the user and show the main menu."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    registration = await user_service.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    await send_and_track_text(
        message,
        build_welcome_text(message.from_user.first_name, registration.is_new_user),
        reply_markup=get_main_menu_keyboard(),
    )
