"""Handlers for user settings."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.keyboards.settings_menu import get_settings_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.services.user_service import UserService
from src.utils.helpers import (
    BUTTON_AUTOSYNC,
    BUTTON_BACK,
    BUTTON_NOTIFICATIONS,
    BUTTON_SETTINGS,
    build_feature_stub_text,
)

router = Router(name="settings")


@router.message(Command("settings"))
@router.message(F.text == BUTTON_SETTINGS)
async def settings_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Show the user settings menu and current values."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    response_text = await user_service.build_settings_overview(message.from_user.id)
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_settings_menu_keyboard(),
    )


@router.message(F.text == BUTTON_NOTIFICATIONS)
async def notifications_placeholder(message: Message) -> None:
    """Placeholder for notifications settings management."""

    await replace_tracked_text(
        message,
        build_feature_stub_text("Управление уведомлениями"),
        reply_markup=get_settings_menu_keyboard(),
    )


@router.message(F.text == BUTTON_AUTOSYNC)
async def autosync_placeholder(message: Message) -> None:
    """Explain that manual intake replaced automatic external sync."""

    await replace_tracked_text(
        message,
        (
            "<b>Автосинхронизация</b>\n\n"
            "Сейчас бот работает в ручном режиме: покупки добавляются по ссылке на подарок, "
            "а продажи закрываются по уведомлениям маркетплейсов. Внешний автосинк по API больше не используется."
        ),
        reply_markup=get_settings_menu_keyboard(),
    )


@router.message(F.text == BUTTON_BACK)
async def back_to_main_menu(message: Message) -> None:
    """Return the user from settings to the main menu."""

    await replace_tracked_text(
        message,
        "Главное меню снова перед тобой.",
        reply_markup=get_main_menu_keyboard(),
    )
