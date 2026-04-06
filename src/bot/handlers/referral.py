"""Handlers for referral program and internal balance actions."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.keyboards.trade_capture_menu import get_purchase_flow_keyboard
from src.bot.message_cleanup import replace_tracked_text
from src.bot.states.referral import ReferralStates
from src.config.settings import Settings
from src.services.referral_service import ReferralService
from src.services.user_service import UserService
from src.utils.i18n import button_variants

router = Router(name="referral")


@router.message(Command("balance"))
@router.message(F.text.in_(button_variants("balance")))
async def balance_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show internal TON balance and recent operations."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    referral_service = ReferralService(session_maker, settings)
    response_text = await referral_service.build_balance_overview(message.from_user.id)
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_main_menu_keyboard(language),
    )


@router.message(Command("referrals"))
@router.message(F.text.in_(button_variants("referrals")))
async def referrals_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show referral link and referral-level progress."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    referral_service = ReferralService(session_maker, settings)
    response_text = await referral_service.build_referrals_overview(message.from_user.id)
    await replace_tracked_text(
        message,
        response_text,
        reply_markup=get_main_menu_keyboard(language),
    )


@router.message(Command("gift"))
@router.message(F.text.in_(button_variants("gift_subscription")))
async def gift_subscription_prompt(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Ask sender to provide target Telegram ID for gift subscription."""

    await state.clear()
    await state.set_state(ReferralStates.waiting_for_gift_target)
    await replace_tracked_text(
        message,
        (
            "<b>Подарить подписку</b>\n\n"
            "Отправь Telegram ID пользователя, которому нужно продлить доступ.\n"
            "Пример: <code>123456789</code>\n\n"
            "Если пользователь ещё не запускал бота, сначала попроси его нажать /start."
        ),
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(Command("withdraw"))
@router.message(F.text.in_(button_variants("withdraw")))
async def withdraw_prompt(
    message: Message,
    state: FSMContext,
) -> None:
    """Ask user for withdrawal amount and wallet address."""

    await state.clear()
    await state.set_state(ReferralStates.waiting_for_withdraw_details)
    await replace_tracked_text(
        message,
        (
            "<b>Вывод TON</b>\n\n"
            "Отправь сумму и TON-кошелёк одной строкой.\n"
            "Пример: <code>1.5 UQABCDEF123...</code>\n\n"
            "Минимум для вывода: 1 TON."
        ),
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(
    ReferralStates.waiting_for_gift_target,
    F.text.in_(button_variants("cancel") | button_variants("back_to_menu")),
)
@router.message(
    ReferralStates.waiting_for_withdraw_details,
    F.text.in_(button_variants("cancel") | button_variants("back_to_menu")),
)
async def cancel_referral_flow(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Cancel current referral action and return to main menu."""

    await state.clear()
    if message.from_user is None:
        return
    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    await replace_tracked_text(
        message,
        "Действие отменено.",
        reply_markup=get_main_menu_keyboard(language),
    )


@router.message(ReferralStates.waiting_for_gift_target)
async def gift_subscription_submit(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Deduct balance and gift one subscription period to target user."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    text = (message.text or "").strip()
    match = re.search(r"\d{5,20}", text)
    if match is None:
        await replace_tracked_text(
            message,
            "Не удалось распознать Telegram ID. Отправь только число, например <code>123456789</code>.",
            reply_markup=get_purchase_flow_keyboard(),
        )
        return

    target_telegram_id = int(match.group(0))
    referral_service = ReferralService(session_maker, settings)
    result = await referral_service.gift_subscription_from_balance(
        sender_telegram_id=message.from_user.id,
        target_telegram_id=target_telegram_id,
    )
    if result.success:
        await state.clear()
    await replace_tracked_text(
        message,
        result.message,
        reply_markup=get_main_menu_keyboard(language) if result.success else get_purchase_flow_keyboard(),
    )


@router.message(ReferralStates.waiting_for_withdraw_details)
async def withdraw_submit(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Create a withdrawal request from internal balance."""

    if message.from_user is None:
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    parsed = _parse_withdraw_input(message.text or "")
    if parsed is None:
        await replace_tracked_text(
            message,
            "Формат не распознан. Пример: <code>1.5 UQABCDEF123...</code>",
            reply_markup=get_purchase_flow_keyboard(),
        )
        return
    amount_ton, wallet_address = parsed

    referral_service = ReferralService(session_maker, settings)
    result = await referral_service.request_withdrawal(
        message.from_user.id,
        wallet_address=wallet_address,
        amount_ton=amount_ton,
    )
    if result.success:
        await state.clear()
    await replace_tracked_text(
        message,
        result.message,
        reply_markup=get_main_menu_keyboard(language) if result.success else get_purchase_flow_keyboard(),
    )


def _parse_withdraw_input(raw_text: str) -> tuple[Decimal, str] | None:
    """Parse `<amount> <wallet>` input for withdrawal command."""

    parts = raw_text.strip().replace(",", ".").split(maxsplit=1)
    if len(parts) != 2:
        return None
    amount_raw, wallet = parts
    try:
        amount_ton = Decimal(amount_raw)
    except (InvalidOperation, ValueError):
        return None
    wallet = wallet.strip()
    if len(wallet) < 16:
        return None
    return amount_ton, wallet
