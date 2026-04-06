"""Handlers for manual purchase and sale capture flows."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.enums import MessageEntityType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.keyboards.trade_capture_menu import (
    get_marketplace_choice_keyboard,
    get_purchase_flow_keyboard,
    get_sale_fee_keyboard,
    get_sale_flow_keyboard,
    get_ton_rate_choice_keyboard,
)
from src.bot.message_cleanup import replace_tracked_text
from src.bot.states.trade_capture import TradeCaptureStates
from src.bot.subscription_guard import ensure_paid_access
from src.config.settings import Settings
from src.services.user_service import UserService
from src.services.trade_capture_service import (
    GiftLinkPayload,
    PurchasePricePayload,
    SaleFeePayload,
    SaleNotificationDraft,
    SaleNotificationPayload,
    TradeCaptureService,
)
from src.utils.enums import Currency, Language
from src.utils.helpers import (
    BUTTON_BACK_TO_MENU,
    BUTTON_CANCEL,
    BUTTON_RATE_DATE,
    BUTTON_RATE_SKIP,
    BUTTON_RATE_TODAY,
    BUTTON_SALE_FEE_SKIP,
)
from src.utils.i18n import button_variants

router = Router(name="sync")


@router.message(Command("sync"))
@router.message(F.text.in_(button_variants("add_purchase")))
async def purchase_command(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Open the explicit purchase capture flow."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    service = TradeCaptureService(session_maker, settings)
    await state.clear()
    await state.set_state(TradeCaptureStates.waiting_for_purchase_input)
    await replace_tracked_text(
        message,
        service.build_purchase_prompt(),
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(Command("sale"))
@router.message(F.text.in_(button_variants("add_sale")))
async def sale_command(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Open the explicit sale capture flow."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    service = TradeCaptureService(session_maker, settings)
    await state.clear()
    await state.set_state(TradeCaptureStates.waiting_for_sale_input)
    await replace_tracked_text(
        message,
        service.build_sale_prompt(),
        reply_markup=get_sale_flow_keyboard(),
    )


@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_purchase_input,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_purchase_marketplace,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_purchase_price,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_purchase_rate_choice,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_purchase_rate_date,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_sale_input,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_sale_marketplace,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_sale_price,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_sale_rate_choice,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_sale_rate_date,
)
@router.message(
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
    TradeCaptureStates.waiting_for_sale_fee,
)
async def cancel_capture_flow(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Cancel the current capture flow and return user to the main menu."""

    await state.clear()
    await replace_tracked_text(
        message,
        "Текущий сценарий остановлен.",
        reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
    )


@router.message(TradeCaptureStates.waiting_for_purchase_input)
async def capture_purchase_input_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse a purchase notification or a fallback gift link."""

    if message.from_user is None:
        return

    service = TradeCaptureService(session_maker, settings)
    payload = await service.parse_purchase_input(
        _message_text(message),
        urls=_extract_urls_from_message(message),
        source_label=_build_source_label(message),
    )
    if payload is None:
        await replace_tracked_text(
            message,
            (
                "<b>Не смог распознать покупку</b>\n\n"
                "Перешли уведомление о покупке от маркетплейса или пришли ссылку на подарок. "
                "Если в сообщении есть текст и превью, отправь его одним сообщением без скриншота."
            ),
            reply_markup=get_purchase_flow_keyboard(),
        )
        return

    state_update_payload: dict[str, str | dict[str, str | None]] = {
        "purchase_gift": _serialize_gift(payload.gift),
        "purchase_opened_at": _resolve_event_datetime(message).isoformat(),
    }
    if payload.price is not None:
        state_update_payload["purchase_price"] = _serialize_price(payload.price)
    await state.update_data(**state_update_payload)

    if service.should_request_manual_marketplace(
        raw_text=_message_text(message),
        source_label=_build_source_label(message),
        gift_url=payload.gift.gift_url,
        marketplace=payload.gift.marketplace,
    ):
        await state.set_state(TradeCaptureStates.waiting_for_purchase_marketplace)
        await replace_tracked_text(
            message,
            service.build_purchase_marketplace_request_text(payload.gift),
            reply_markup=get_marketplace_choice_keyboard(),
        )
        return

    if payload.price is None:
        await state.set_state(TradeCaptureStates.waiting_for_purchase_price)
        await replace_tracked_text(
            message,
            service.build_purchase_price_request_text(payload.gift),
            reply_markup=get_purchase_flow_keyboard(),
        )
        return

    await state.set_state(TradeCaptureStates.waiting_for_purchase_rate_choice)
    await replace_tracked_text(
        message,
        service.build_rate_prompt(payload.gift, payload.price),
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_purchase_price)
async def capture_purchase_price_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse the missing purchase price and move to TON-rate selection."""

    data = await state.get_data()
    gift_data = data.get("purchase_gift")
    if not isinstance(gift_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о покупке потерялись. Нажми «Добавить купленный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    price = service.parse_purchase_price(_message_text(message))
    if price is None:
        await replace_tracked_text(
            message,
            (
                "<b>Не удалось распознать цену покупки</b>\n\n"
                "Отправь цену в формате <code>4.9522 TON</code> или <code>25 USDT</code>."
            ),
            reply_markup=get_purchase_flow_keyboard(),
        )
        return

    await state.update_data(purchase_price=_serialize_price(price))
    await state.set_state(TradeCaptureStates.waiting_for_purchase_rate_choice)
    await replace_tracked_text(
        message,
        service.build_rate_prompt(_deserialize_gift(gift_data), price),
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_purchase_marketplace)
async def capture_purchase_marketplace_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Store manually entered purchase marketplace and continue the flow."""

    data = await state.get_data()
    gift_data = data.get("purchase_gift")
    if not isinstance(gift_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные покупки потерялись. Нажми «Добавить купленный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    marketplace = service.parse_marketplace_input(_message_text(message))
    if marketplace is None:
        await replace_tracked_text(
            message,
            "Не удалось распознать маркетплейс. Выбери кнопку ниже или отправь название вроде <code>PORTALS</code>.",
            reply_markup=get_marketplace_choice_keyboard(),
        )
        return

    gift = _deserialize_gift(gift_data)
    gift.marketplace = marketplace
    await state.update_data(purchase_gift=_serialize_gift(gift))

    price_data = data.get("purchase_price")
    if isinstance(price_data, dict):
        price = _deserialize_price(price_data)
        await state.set_state(TradeCaptureStates.waiting_for_purchase_rate_choice)
        await replace_tracked_text(
            message,
            service.build_rate_prompt(gift, price),
            reply_markup=get_ton_rate_choice_keyboard(),
        )
        return

    await state.set_state(TradeCaptureStates.waiting_for_purchase_price)
    await replace_tracked_text(
        message,
        service.build_purchase_price_request_text(gift),
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_purchase_rate_choice, F.text == BUTTON_RATE_TODAY)
async def capture_rate_today_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Fetch current TON rate and finalize the purchase."""

    service = TradeCaptureService(session_maker, settings)
    await state.update_data(purchase_opened_at=_now_in_utc(settings).isoformat())
    rate_result = await service.fetch_today_ton_rate()
    if not rate_result.success:
        await replace_tracked_text(
            message,
            f"{rate_result.message}\n\nПопробуй выбрать дату вручную или нажми «Пропустить».",
            reply_markup=get_ton_rate_choice_keyboard(),
        )
        return

    await _finalize_purchase(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        ton_usd_rate=rate_result.rate,
        rate_source=rate_result.source,
    )


@router.message(TradeCaptureStates.waiting_for_purchase_rate_choice, F.text == BUTTON_RATE_DATE)
async def capture_rate_date_prompt(message: Message, state: FSMContext) -> None:
    """Ask user to enter a calendar date for TON-rate lookup."""

    await state.set_state(TradeCaptureStates.waiting_for_purchase_rate_date)
    await replace_tracked_text(
        message,
        "Введи дату в формате <code>ДД.ММ.ГГГГ</code>, например <code>21.01.2026</code>.",
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_purchase_rate_choice, F.text == BUTTON_RATE_SKIP)
async def capture_rate_skip_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Save the purchase without TON-rate snapshot."""

    await _finalize_purchase(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        ton_usd_rate=None,
        rate_source=None,
    )


@router.message(TradeCaptureStates.waiting_for_purchase_rate_choice)
async def capture_rate_choice_fallback(message: Message) -> None:
    """Prompt user to use one of the predefined TON-rate buttons."""

    await replace_tracked_text(
        message,
        "Выбери один из вариантов ниже: сохранить текущий курс, выбрать дату или пропустить этот шаг.",
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_purchase_rate_date)
async def capture_rate_date_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Lookup historical TON rate for a specific date and finalize purchase."""

    try:
        selected_date = datetime.strptime(_message_text(message).strip(), "%d.%m.%Y").date()
    except ValueError:
        await replace_tracked_text(
            message,
            "Не удалось распознать дату. Используй формат <code>ДД.ММ.ГГГГ</code>.",
            reply_markup=get_purchase_flow_keyboard(),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    data = await state.get_data()
    await state.update_data(
        purchase_opened_at=_merge_selected_date_with_event_time(
            selected_date=selected_date,
            current_event=_deserialize_datetime(data, "purchase_opened_at"),
            settings=settings,
        ).isoformat()
    )
    rate_result = await service.fetch_ton_rate_for_date(selected_date)
    if not rate_result.success:
        await replace_tracked_text(
            message,
            f"{rate_result.message}\n\nМожно отправить другую дату или нажать «Пропустить».",
            reply_markup=get_ton_rate_choice_keyboard(),
        )
        return

    await _finalize_purchase(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        ton_usd_rate=rate_result.rate,
        rate_source=rate_result.source,
    )


@router.message(TradeCaptureStates.waiting_for_sale_input)
async def capture_sale_input_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse a sale notification and either ask for amount or commission."""

    if message.from_user is None:
        return

    service = TradeCaptureService(session_maker, settings)
    draft = service.parse_sale_notification_draft(
        _message_text(message),
        urls=_extract_urls_from_message(message),
        source_label=_build_source_label(message),
    )
    if draft is None:
        await replace_tracked_text(
            message,
            (
                "<b>Не смог распознать продажу</b>\n\n"
                "Перешли уведомление о продаже от маркетплейса одним сообщением. "
                "Если там есть текст и превью, отправляй оригинальное сообщение, а не скриншот."
            ),
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    await state.update_data(
        sale_draft=_serialize_sale_draft(draft),
        sale_closed_at=_resolve_event_datetime(message).isoformat(),
    )
    if service.should_request_manual_marketplace(
        raw_text=_message_text(message),
        source_label=_build_source_label(message),
        gift_url=draft.gift_url,
        marketplace=draft.marketplace,
    ):
        await state.set_state(TradeCaptureStates.waiting_for_sale_marketplace)
        await replace_tracked_text(
            message,
            service.build_sale_marketplace_request_text(draft),
            reply_markup=get_marketplace_choice_keyboard(),
        )
        return

    if draft.amount is None or draft.currency is None:
        await state.set_state(TradeCaptureStates.waiting_for_sale_price)
        await replace_tracked_text(
            message,
            service.build_sale_price_request_text(draft),
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    payload = service.finalize_sale_draft(draft)
    if payload is None:
        await replace_tracked_text(
            message,
            "Не удалось подготовить продажу. Попробуй переслать уведомление еще раз.",
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    await _prepare_sale_payload(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        payload=payload,
        closed_at=_deserialize_datetime(await state.get_data(), "sale_closed_at"),
    )


@router.message(TradeCaptureStates.waiting_for_sale_price)
async def capture_sale_price_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse missing sale amount and continue to commission step."""

    data = await state.get_data()
    draft_data = data.get("sale_draft")
    if not isinstance(draft_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о продаже потерялись. Нажми «Добавить проданный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    sale_amount = service.parse_sale_amount(_message_text(message), default_currency=Currency.TON)
    if sale_amount is None:
        await replace_tracked_text(
            message,
            (
                "<b>Не удалось распознать сумму продажи</b>\n\n"
                "Отправь сумму в формате <code>31.35 TON</code> или <code>120 USDT</code>."
            ),
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    payload = service.finalize_sale_draft(_deserialize_sale_draft(draft_data), amount=sale_amount)
    if payload is None:
        await replace_tracked_text(
            message,
            "Не удалось подготовить продажу. Попробуй переслать уведомление еще раз.",
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    await _prepare_sale_payload(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        payload=payload,
        closed_at=_deserialize_datetime(data, "sale_closed_at"),
    )


@router.message(TradeCaptureStates.waiting_for_sale_marketplace)
async def capture_sale_marketplace_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Store manually entered sale marketplace and continue the flow."""

    data = await state.get_data()
    draft_data = data.get("sale_draft")
    if not isinstance(draft_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о продаже потерялись. Нажми «Добавить проданный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    marketplace = service.parse_marketplace_input(_message_text(message))
    if marketplace is None:
        await replace_tracked_text(
            message,
            "Не удалось распознать маркетплейс. Выбери кнопку ниже или отправь название вроде <code>FRAGMENT</code>.",
            reply_markup=get_marketplace_choice_keyboard(),
        )
        return

    draft = _deserialize_sale_draft(draft_data)
    draft.marketplace = marketplace
    await state.update_data(sale_draft=_serialize_sale_draft(draft))

    if draft.amount is None or draft.currency is None:
        await state.set_state(TradeCaptureStates.waiting_for_sale_price)
        await replace_tracked_text(
            message,
            service.build_sale_price_request_text(draft),
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    payload = service.finalize_sale_draft(draft)
    if payload is None:
        await replace_tracked_text(
            message,
            "Не удалось подготовить продажу. Попробуй переслать уведомление еще раз.",
            reply_markup=get_sale_flow_keyboard(),
        )
        return

    await _prepare_sale_payload(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        payload=payload,
        closed_at=_deserialize_datetime(data, "sale_closed_at"),
    )


@router.message(TradeCaptureStates.waiting_for_sale_fee, F.text == BUTTON_SALE_FEE_SKIP)
async def capture_sale_fee_skip_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Finalize sale without any marketplace fee."""

    data = await state.get_data()
    sale_data = data.get("pending_sale")
    if not isinstance(sale_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о продаже потерялись. Нажми «Добавить проданный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    payload = _deserialize_sale_payload(sale_data)
    await _finalize_sale(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        matched_deal_id=int(sale_data["matched_deal_id"]),
        payload=payload,
        fee=SaleFeePayload(amount=Decimal("0"), currency=payload.currency),
        closed_at=_deserialize_datetime(sale_data, "closed_at"),
    )


@router.message(TradeCaptureStates.waiting_for_sale_rate_choice, F.text == BUTTON_RATE_TODAY)
async def capture_sale_rate_today_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Fetch current TON rate and continue sale capture."""

    service = TradeCaptureService(session_maker, settings)
    await state.update_data(sale_closed_at=_now_in_utc(settings).isoformat())
    rate_result = await service.fetch_today_ton_rate()
    if not rate_result.success:
        await replace_tracked_text(
            message,
            f"{rate_result.message}\n\nПопробуй выбрать дату вручную или нажми «Пропустить».",
            reply_markup=get_ton_rate_choice_keyboard(),
        )
        return

    await _move_sale_to_fee_step(
        message,
        state,
        session_maker=session_maker,
        sale_ton_usd_rate=rate_result.rate,
    )


@router.message(TradeCaptureStates.waiting_for_sale_rate_choice, F.text == BUTTON_RATE_DATE)
async def capture_sale_rate_date_prompt(message: Message, state: FSMContext) -> None:
    """Ask user to enter a calendar date for sale TON-rate lookup."""

    await state.set_state(TradeCaptureStates.waiting_for_sale_rate_date)
    await replace_tracked_text(
        message,
        "Введи дату продажи в формате <code>ДД.ММ.ГГГГ</code>, например <code>21.01.2026</code>.",
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_sale_rate_choice, F.text == BUTTON_RATE_SKIP)
async def capture_sale_rate_skip_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Continue sale capture without a TON-rate snapshot."""

    await _move_sale_to_fee_step(
        message,
        state,
        session_maker=session_maker,
        sale_ton_usd_rate=None,
    )


@router.message(TradeCaptureStates.waiting_for_sale_rate_choice)
async def capture_sale_rate_choice_fallback(message: Message) -> None:
    """Prompt user to use one of the predefined sale rate buttons."""

    await replace_tracked_text(
        message,
        "Выбери один из вариантов ниже: сохранить текущий курс, выбрать дату или пропустить этот шаг.",
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_sale_rate_date)
async def capture_sale_rate_date_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Lookup historical TON rate for a specific sale date."""

    try:
        selected_date = datetime.strptime(_message_text(message).strip(), "%d.%m.%Y").date()
    except ValueError:
        await replace_tracked_text(
            message,
            "Не удалось распознать дату. Используй формат <code>ДД.ММ.ГГГГ</code>.",
            reply_markup=get_ton_rate_choice_keyboard(),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    data = await state.get_data()
    await state.update_data(
        sale_closed_at=_merge_selected_date_with_event_time(
            selected_date=selected_date,
            current_event=_deserialize_datetime(data, "sale_closed_at"),
            settings=settings,
        ).isoformat()
    )
    rate_result = await service.fetch_ton_rate_for_date(selected_date)
    if not rate_result.success:
        await replace_tracked_text(
            message,
            f"{rate_result.message}\n\nМожно отправить другую дату или нажать «Пропустить».",
            reply_markup=get_ton_rate_choice_keyboard(),
        )
        return

    await _move_sale_to_fee_step(
        message,
        state,
        session_maker=session_maker,
        sale_ton_usd_rate=rate_result.rate,
    )


@router.message(TradeCaptureStates.waiting_for_sale_fee)
async def capture_sale_fee_value_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse sale fee and finalize the matched sale."""

    data = await state.get_data()
    sale_data = data.get("pending_sale")
    if not isinstance(sale_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о продаже потерялись. Нажми «Добавить проданный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    payload = _deserialize_sale_payload(sale_data)
    service = TradeCaptureService(session_maker, settings)
    fee = service.parse_sale_fee(_message_text(message), default_currency=payload.currency)
    if fee is None:
        await replace_tracked_text(
            message,
            (
                "<b>Не удалось распознать комиссию</b>\n\n"
                "Отправь комиссию в формате <code>0.5 TON</code> или нажми «Без комиссии»."
            ),
            reply_markup=get_sale_fee_keyboard(),
        )
        return

    await _finalize_sale(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        matched_deal_id=int(sale_data["matched_deal_id"]),
        payload=payload,
        fee=fee,
        closed_at=_deserialize_datetime(sale_data, "closed_at"),
    )


async def _finalize_purchase(
    message: Message,
    state: FSMContext,
    *,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    ton_usd_rate: Decimal | None,
    rate_source: str | None,
) -> None:
    """Persist purchase using FSM data and return to the main menu."""

    if message.from_user is None:
        return

    data = await state.get_data()
    gift_data = data.get("purchase_gift")
    price_data = data.get("purchase_price")
    if not isinstance(gift_data, dict) or not isinstance(price_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные покупки потерялись. Нажми «Добавить купленный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    result = await service.save_manual_purchase(
        message.from_user.id,
        gift=_deserialize_gift(gift_data),
        price=_deserialize_price(price_data),
        ton_usd_rate=ton_usd_rate,
        rate_source=rate_source,
        opened_at=_deserialize_datetime(data, "purchase_opened_at"),
    )
    await state.clear()
    await replace_tracked_text(
        message,
        result.message,
        reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
    )


async def _prepare_sale_payload(
    message: Message,
    state: FSMContext,
    *,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    payload: SaleNotificationPayload,
    closed_at: datetime | None,
) -> None:
    """Match sale payload to an open deal and move to sale-rate selection."""

    if message.from_user is None:
        return

    service = TradeCaptureService(session_maker, settings)
    prepared = await service.prepare_sale_payload(message.from_user.id, payload=payload)
    if not prepared.success or prepared.payload is None or prepared.matched_deal_id is None:
        await state.clear()
        await replace_tracked_text(
            message,
            prepared.message,
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    await state.update_data(
        pending_sale=_serialize_sale_payload(
            prepared.payload,
            matched_deal_id=prepared.matched_deal_id,
            closed_at=closed_at,
            fee_prompt=prepared.fee_prompt,
            sale_ton_usd_rate=None,
        )
    )
    await state.set_state(TradeCaptureStates.waiting_for_sale_rate_choice)
    await replace_tracked_text(
        message,
        prepared.message,
        reply_markup=get_ton_rate_choice_keyboard(),
    )


async def _finalize_sale(
    message: Message,
    state: FSMContext,
    *,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    matched_deal_id: int,
    payload: SaleNotificationPayload,
    fee: SaleFeePayload,
    closed_at: datetime | None,
) -> None:
    """Finalize sale with commission and show the result."""

    if message.from_user is None:
        return

    service = TradeCaptureService(session_maker, settings)
    result = await service.finalize_sale_notification(
        message.from_user.id,
        matched_deal_id=matched_deal_id,
        payload=payload,
        fee=fee,
        sale_ton_usd_rate=_deserialize_decimal_from_state(await state.get_data(), "pending_sale", "sale_ton_usd_rate"),
        closed_at=closed_at,
    )
    if result.success:
        await state.clear()
        reply_markup = get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker))
    elif result.retry_stage == "sale_rate":
        await state.set_state(TradeCaptureStates.waiting_for_sale_rate_choice)
        reply_markup = get_ton_rate_choice_keyboard()
    else:
        reply_markup = get_sale_fee_keyboard()

    await replace_tracked_text(
        message,
        result.message,
        reply_markup=reply_markup,
    )


async def _move_sale_to_fee_step(
    message: Message,
    state: FSMContext,
    *,
    session_maker: async_sessionmaker[AsyncSession],
    sale_ton_usd_rate: Decimal | None,
) -> None:
    """Persist sale rate choice in FSM and move to commission input."""

    data = await state.get_data()
    sale_data = data.get("pending_sale")
    if not isinstance(sale_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о продаже потерялись. Нажми «Добавить проданный подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(await _resolve_language_for_user(message, session_maker)),
        )
        return

    sale_data["sale_ton_usd_rate"] = format(sale_ton_usd_rate, "f") if sale_ton_usd_rate is not None else None
    await state.update_data(pending_sale=sale_data)
    await state.set_state(TradeCaptureStates.waiting_for_sale_fee)
    await replace_tracked_text(
        message,
        sale_data.get("fee_prompt") or "Теперь отправь комиссию продажи.",
        reply_markup=get_sale_fee_keyboard(),
    )


async def _resolve_language_for_user(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> Language:
    """Resolve preferred UI language for current user."""

    if message.from_user is None:
        return Language.RU

    user_service = UserService(session_maker)
    return await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )


def _message_text(message: Message) -> str:
    """Return plain text or caption from the message."""

    return (message.text or message.caption or "").strip()


def _extract_urls_from_message(message: Message) -> list[str]:
    """Extract visible and hidden URLs from message entities."""

    text = message.text or message.caption or ""
    entities = list(message.entities or [])
    entities.extend(message.caption_entities or [])

    urls: list[str] = []
    for entity in entities:
        if entity.type == MessageEntityType.TEXT_LINK and entity.url:
            urls.append(entity.url)
            continue
        if entity.type != MessageEntityType.URL:
            continue
        start = entity.offset
        end = entity.offset + entity.length
        candidate = text[start:end]
        if candidate:
            urls.append(candidate)
    return urls


def _build_source_label(message: Message) -> str | None:
    """Build a marketplace hint from forward metadata."""

    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        sender_user = getattr(origin, "sender_user", None)
        if sender_user is not None:
            return sender_user.username or sender_user.full_name
        chat = getattr(origin, "chat", None)
        if chat is not None:
            return chat.title or chat.username
        sender_name = getattr(origin, "sender_user_name", None)
        if sender_name:
            return sender_name

    sender_chat = getattr(message, "sender_chat", None)
    if sender_chat is not None:
        return sender_chat.title or sender_chat.username
    return None


def _resolve_event_datetime(message: Message) -> datetime:
    """Resolve original forwarded message time when available."""

    origin = getattr(message, "forward_origin", None)
    origin_date = getattr(origin, "date", None) if origin is not None else None
    return origin_date or message.date


def _now_in_utc(settings: Settings) -> datetime:
    """Return current timestamp normalized to UTC using business timezone when possible."""

    timezone_name = settings.business_timezone
    try:
        return datetime.now(ZoneInfo(timezone_name)).astimezone(timezone.utc)
    except ZoneInfoNotFoundError:
        return datetime.now(timezone.utc)


def _merge_selected_date_with_event_time(
    *,
    selected_date: date,
    current_event: datetime | None,
    settings: Settings,
) -> datetime:
    """Apply selected calendar date while preserving event time component."""

    base = current_event or _now_in_utc(settings)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.replace(
        year=selected_date.year,
        month=selected_date.month,
        day=selected_date.day,
    )


def _serialize_gift(payload: GiftLinkPayload) -> dict[str, str | None]:
    """Serialize parsed gift payload into FSM storage."""

    return {
        "gift_url": payload.gift_url,
        "item_name": payload.item_name,
        "gift_number": payload.gift_number,
        "marketplace": payload.marketplace,
    }


def _deserialize_gift(data: dict[str, str | None]) -> GiftLinkPayload:
    """Deserialize gift payload from FSM storage."""

    return GiftLinkPayload(
        gift_url=data.get("gift_url"),
        item_name=data.get("item_name") or "Gift",
        gift_number=data.get("gift_number"),
        marketplace=data.get("marketplace") or "TELEGRAM",
    )


def _serialize_price(payload: PurchasePricePayload) -> dict[str, str]:
    """Serialize price payload into FSM storage."""

    return {
        "amount": format(payload.amount, "f"),
        "currency": payload.currency.value,
    }


def _deserialize_price(data: dict[str, str]) -> PurchasePricePayload:
    """Deserialize price payload from FSM storage."""

    return PurchasePricePayload(
        amount=Decimal(data["amount"]),
        currency=Currency(data["currency"]),
    )


def _serialize_sale_draft(payload: SaleNotificationDraft) -> dict[str, str | None]:
    """Serialize sale draft into FSM storage."""

    return {
        "item_name": payload.item_name,
        "gift_number": payload.gift_number,
        "amount": format(payload.amount, "f") if payload.amount is not None else None,
        "currency": payload.currency.value if payload.currency is not None else None,
        "marketplace": payload.marketplace,
        "gift_url": payload.gift_url,
        "raw_text": payload.raw_text,
    }


def _deserialize_sale_draft(data: dict[str, str | None]) -> SaleNotificationDraft:
    """Deserialize sale draft from FSM storage."""

    currency_raw = data.get("currency")
    return SaleNotificationDraft(
        item_name=data.get("item_name") or "Gift",
        gift_number=data.get("gift_number"),
        amount=Decimal(data["amount"]) if data.get("amount") else None,
        currency=Currency(currency_raw) if currency_raw else None,
        marketplace=data.get("marketplace") or "TELEGRAM",
        gift_url=data.get("gift_url"),
        raw_text=data.get("raw_text") or "",
    )


def _serialize_sale_payload(
    payload: SaleNotificationPayload,
    *,
    matched_deal_id: int,
    closed_at: datetime | None,
    fee_prompt: str | None,
    sale_ton_usd_rate: Decimal | None,
) -> dict[str, str | None]:
    """Serialize pending sale data into FSM storage."""

    return {
        "matched_deal_id": str(matched_deal_id),
        "item_name": payload.item_name,
        "gift_number": payload.gift_number,
        "amount": format(payload.amount, "f"),
        "currency": payload.currency.value,
        "marketplace": payload.marketplace,
        "raw_text": payload.raw_text,
        "closed_at": closed_at.isoformat() if closed_at is not None else None,
        "fee_prompt": fee_prompt,
        "sale_ton_usd_rate": format(sale_ton_usd_rate, "f") if sale_ton_usd_rate is not None else None,
    }


def _deserialize_sale_payload(data: dict[str, str | None]) -> SaleNotificationPayload:
    """Deserialize pending sale data from FSM storage."""

    return SaleNotificationPayload(
        item_name=data.get("item_name") or "Gift",
        gift_number=data.get("gift_number"),
        amount=Decimal(data["amount"] or "0"),
        currency=Currency(data.get("currency") or Currency.TON.value),
        marketplace=data.get("marketplace") or "TELEGRAM",
        raw_text=data.get("raw_text") or "",
    )


def _deserialize_datetime(data: dict[str, str | None], key: str) -> datetime | None:
    """Deserialize stored datetime from FSM storage."""

    raw_value = data.get(key)
    if not raw_value:
        return None
    return datetime.fromisoformat(raw_value)


def _deserialize_decimal_from_state(
    data: dict[str, object],
    nested_key: str,
    field_name: str,
) -> Decimal | None:
    """Deserialize an optional Decimal value from nested FSM data."""

    nested = data.get(nested_key)
    if not isinstance(nested, dict):
        return None

    raw_value = nested.get(field_name)
    if raw_value in (None, ""):
        return None
    return Decimal(str(raw_value))
