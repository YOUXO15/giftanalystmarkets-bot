"""Handlers for user settings."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.keyboards.settings_menu import get_language_menu_keyboard, get_settings_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.services.user_service import UserService
from src.utils.enums import Language
from src.utils.i18n import button_variants, t

router = Router(name="settings")


async def _resolve_language(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> Language:
    """Resolve UI language for current user."""

    user_service = UserService(session_maker)
    if message.from_user is None:
        return Language.RU
    return await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )


@router.message(Command("settings"))
@router.message(F.text.in_(button_variants("settings")))
async def settings_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Show the user settings menu and current values."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    language = await _resolve_language(message, session_maker)
    response_text = await user_service.build_settings_overview(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_settings_menu_keyboard(language),
    )


@router.message(F.text.in_(button_variants("language")))
async def open_language_menu(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Open language selection menu."""

    language = await _resolve_language(message, session_maker)
    await replace_tracked_text(
        message,
        t("language_menu_title", language),
        reply_markup=get_language_menu_keyboard(),
    )


@router.message(
    F.text.in_(
        button_variants("language_ru")
        | button_variants("language_en")
        | button_variants("language_zh")
    )
)
async def select_language(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Persist selected language."""

    if message.from_user is None or message.text is None:
        return

    if message.text in button_variants("language_ru"):
        selected = Language.RU
    elif message.text in button_variants("language_en"):
        selected = Language.EN
    else:
        selected = Language.ZH

    user_service = UserService(session_maker)
    updated = await user_service.update_user_language(message.from_user.id, selected)
    if not updated:
        await replace_tracked_text(
            message,
            t("registration_required", selected),
            reply_markup=get_main_menu_keyboard(selected),
        )
        return

    response_text = await user_service.build_settings_overview(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    await replace_tracked_text(
        message,
        f"{t('language_changed', selected)}\n\n{response_text}",
        reply_markup=get_settings_menu_keyboard(selected),
    )


@router.message(F.text.in_(button_variants("back")))
async def back_to_main_menu(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Return the user from settings to the main menu."""

    language = await _resolve_language(message, session_maker)
    await replace_tracked_text(
        message,
        t("back_to_main_menu", language),
        reply_markup=get_main_menu_keyboard(language),
    )
