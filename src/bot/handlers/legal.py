"""Handlers for legal documents links."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.config.settings import Settings
from src.services.user_service import UserService
from src.utils.i18n import button_variants, t

router = Router(name="legal")


@router.message(Command("privacy"))
@router.message(Command("terms"))
@router.message(F.text.in_(button_variants("privacy_policy")))
@router.message(F.text.in_(button_variants("terms_of_service")))
async def legal_documents_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show privacy policy and terms of service links."""

    language = None
    if message.from_user is not None:
        user_service = UserService(session_maker)
        language = await user_service.get_user_language(
            message.from_user.id,
            fallback_telegram_language=message.from_user.language_code,
        )

    await replace_tracked_text(
        message,
        t(
            "legal_documents_text",
            language,
            privacy_url=settings.privacy_policy_url,
            terms_url=settings.terms_of_service_url,
        ),
        reply_markup=get_main_menu_keyboard(language),
    )
