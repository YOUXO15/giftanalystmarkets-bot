"""Handlers for subscription and billing flows."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.keyboards.subscription_menu import get_subscription_menu_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.config.settings import Settings
from src.services.billing_service import BillingService
from src.utils.helpers import (
    BUTTON_SUBSCRIPTION,
    BUTTON_SUBSCRIPTION_CHECK,
    BUTTON_SUBSCRIPTION_CREATE,
)

router = Router(name="billing")


@router.message(Command("pay"))
@router.message(F.text == BUTTON_SUBSCRIPTION)
async def subscription_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show the current subscription screen."""

    if message.from_user is None:
        return

    billing_service = BillingService(session_maker, settings)
    response_text = await billing_service.build_subscription_overview(message.from_user.id)
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_subscription_menu_keyboard(),
    )


@router.message(F.text == BUTTON_SUBSCRIPTION_CREATE)
async def create_subscription_invoice(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Create or reuse a subscription invoice."""

    if message.from_user is None:
        return

    billing_service = BillingService(session_maker, settings)
    result = await billing_service.create_or_reuse_invoice(message.from_user.id)
    await replace_tracked_text(
        message,
        result.message,
        reply_markup=get_main_menu_keyboard() if result.reply_to_main_menu else get_subscription_menu_keyboard(),
    )


@router.message(F.text == BUTTON_SUBSCRIPTION_CHECK)
async def check_subscription_payment(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Refresh payment state for the latest invoice."""

    if message.from_user is None:
        return

    billing_service = BillingService(session_maker, settings)
    result = await billing_service.refresh_payment_status(message.from_user.id)
    await replace_tracked_text(
        message,
        result.message,
        reply_markup=get_main_menu_keyboard() if result.reply_to_main_menu else get_subscription_menu_keyboard(),
    )
