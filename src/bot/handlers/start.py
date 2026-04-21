"""Handlers for the /start command."""

from __future__ import annotations

import logging
from datetime import timezone
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import send_and_track_text
from src.config.settings import Settings
from src.services.referral_service import ReferralService
from src.services.user_service import UserService
from src.utils.helpers import build_welcome_text

router = Router(name="start")
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Register the user and show the main menu."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    registration = await user_service.register_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        telegram_language_code=message.from_user.language_code,
    )
    if registration.is_new_user:
        referral_service = ReferralService(session_maker, settings)
        await referral_service.bind_referrer_from_deep_link(
            registration.user.id,
            _extract_start_payload(message.text),
        )

    await send_and_track_text(
        message,
        build_welcome_text(
            message.from_user.first_name,
            registration.is_new_user,
            language=registration.settings.preferred_language,
            subscription_price_ton=str(settings.subscription_monthly_price_ton),
        ),
        reply_markup=get_main_menu_keyboard(registration.settings.preferred_language),
    )
    await _notify_start_to_owner(message, settings)


def _extract_start_payload(message_text: str | None) -> str | None:
    """Extract optional deep-link payload from /start command."""

    if message_text is None:
        return None
    parts = message_text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip()


async def _notify_start_to_owner(message: Message, settings: Settings) -> None:
    """Send /start audit notification to the configured owner Telegram ID."""

    owner_id = settings.start_notify_telegram_id
    user = message.from_user
    if owner_id is None or user is None or user.id == owner_id:
        return

    try:
        try:
            tz = ZoneInfo(settings.business_timezone)
        except ZoneInfoNotFoundError:
            logger.warning(
                "Unknown BUSINESS_TIMEZONE '%s'. Falling back to UTC for /start notification.",
                settings.business_timezone,
            )
            tz = timezone.utc

        pressed_at = message.date.astimezone(tz)
        username = f"@{user.username}" if user.username else "без username"
        notify_text = (
            "Новый /start в боте\n\n"
            f"Username: {escape(username)}\n"
            f"ID: <code>{user.id}</code>\n"
            f"Имя: {escape(user.full_name)}\n"
            f"Дата/время: {escape(pressed_at.strftime('%d.%m.%Y %H:%M:%S %Z'))}"
        )
        await message.bot.send_message(owner_id, notify_text, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to send /start notification to owner_id=%s", owner_id)
