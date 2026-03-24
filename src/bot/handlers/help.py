"""Handlers for the /help command."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.utils.helpers import build_help_text

router = Router(name="help")


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Show bot help information."""

    await replace_tracked_text(
        message,
        build_help_text(),
        reply_markup=get_main_menu_keyboard(),
    )
