"""Handlers for manual purchase capture and sale notification intake."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.enums import MessageEntityType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.keyboards.trade_capture_menu import (
    get_purchase_flow_keyboard,
    get_sale_fee_keyboard,
    get_ton_rate_choice_keyboard,
)
from src.bot.message_cleanup import replace_tracked_text
from src.bot.states.trade_capture import TradeCaptureStates
from src.bot.subscription_guard import ensure_paid_access
from src.config.settings import Settings
from src.services.trade_capture_service import (
    GiftLinkPayload,
    PurchasePricePayload,
    SaleFeePayload,
    SaleNotificationPayload,
    TradeCaptureService,
)
from src.utils.enums import Currency
from src.utils.helpers import (
    BUTTON_BACK_TO_MENU,
    BUTTON_CANCEL,
    BUTTON_RATE_DATE,
    BUTTON_RATE_SKIP,
    BUTTON_RATE_TODAY,
    BUTTON_SALE_FEE_SKIP,
    BUTTON_SYNC,
    get_known_button_texts,
)

router = Router(name="sync")

_KNOWN_BUTTONS = get_known_button_texts()


@router.message(Command("sync"))
@router.message(F.text == BUTTON_SYNC)
async def purchase_command(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Open the manual purchase intake flow."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    service = TradeCaptureService(session_maker, settings)
    await state.clear()
    await state.set_state(TradeCaptureStates.waiting_for_gift_link)
    await replace_tracked_text(
        message,
        service.build_purchase_prompt(),
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(
    TradeCaptureStates.waiting_for_gift_link,
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
)
@router.message(
    TradeCaptureStates.waiting_for_buy_price,
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
)
@router.message(
    TradeCaptureStates.waiting_for_rate_choice,
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
)
@router.message(
    TradeCaptureStates.waiting_for_rate_date,
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
)
@router.message(
    TradeCaptureStates.waiting_for_sale_fee,
    F.text.in_({BUTTON_CANCEL, BUTTON_BACK_TO_MENU}),
)
async def cancel_purchase_flow(message: Message, state: FSMContext) -> None:
    """Cancel the current flow and return user to the main menu."""

    await state.clear()
    await replace_tracked_text(
        message,
        "Текущий сценарий остановлен.",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_gift_link)
async def capture_gift_link_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse a gift link and ask for the purchase price."""

    if message.from_user is None:
        return

    service = TradeCaptureService(session_maker, settings)
    raw_text = _message_text(message)
    payload = service.parse_gift_link(raw_text, urls=_extract_urls_from_message(message))
    if payload is None:
        await replace_tracked_text(
            message,
            (
                "<b>Не вижу ссылки на подарок</b>\n\n"
                "Отправь одно сообщение с прямой ссылкой. "
                "После этого я сразу попрошу цену покупки."
            ),
            reply_markup=get_purchase_flow_keyboard(),
        )
        return

    await state.update_data(gift=_serialize_gift(payload))
    await state.set_state(TradeCaptureStates.waiting_for_buy_price)
    await replace_tracked_text(
        message,
        service.build_link_received_text(payload),
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_buy_price)
async def capture_purchase_price_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse the manual purchase price and ask about TON rate snapshot."""

    if message.from_user is None:
        return

    data = await state.get_data()
    gift_data = data.get("gift")
    if not isinstance(gift_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о подарке потерялись. Нажми «Добавить подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(),
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

    await state.update_data(price=_serialize_price(price))
    await state.set_state(TradeCaptureStates.waiting_for_rate_choice)
    await replace_tracked_text(
        message,
        service.build_rate_prompt(_deserialize_gift(gift_data), price),
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_rate_choice, F.text == BUTTON_RATE_TODAY)
async def capture_rate_today_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Fetch current TON rate and finalize the purchase."""

    service = TradeCaptureService(session_maker, settings)
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


@router.message(TradeCaptureStates.waiting_for_rate_choice, F.text == BUTTON_RATE_DATE)
async def capture_rate_date_prompt(message: Message, state: FSMContext) -> None:
    """Ask user to enter a calendar date for TON rate lookup."""

    await state.set_state(TradeCaptureStates.waiting_for_rate_date)
    await replace_tracked_text(
        message,
        "Введи дату в формате <code>ДД.ММ.ГГГГ</code>, например <code>21.01.2026</code>.",
        reply_markup=get_purchase_flow_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_rate_choice, F.text == BUTTON_RATE_SKIP)
async def capture_rate_skip_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Save the purchase without TON rate snapshot."""

    await _finalize_purchase(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        ton_usd_rate=None,
        rate_source=None,
    )


@router.message(TradeCaptureStates.waiting_for_rate_choice)
async def capture_rate_choice_fallback(message: Message) -> None:
    """Prompt user to use the predefined TON rate buttons."""

    await replace_tracked_text(
        message,
        "Выбери один из вариантов кнопками ниже: сохранить текущий курс, выбрать дату или пропустить.",
        reply_markup=get_ton_rate_choice_keyboard(),
    )


@router.message(TradeCaptureStates.waiting_for_rate_date)
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
    rate_result = await service.fetch_ton_rate_for_date(selected_date)
    if not rate_result.success:
        await replace_tracked_text(
            message,
            f"{rate_result.message}\n\nМожно отправить другую дату или нажать «Пропустить».",
            reply_markup=get_purchase_flow_keyboard(),
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
            "Данные о продаже потерялись. Перешли уведомление о продаже еще раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    sale_payload = _deserialize_sale_payload(sale_data)
    await _finalize_sale(
        message,
        state,
        session_maker=session_maker,
        settings=settings,
        matched_deal_id=int(sale_data["matched_deal_id"]),
        payload=sale_payload,
        fee=SaleFeePayload(amount=Decimal("0"), currency=sale_payload.currency),
        closed_at=_deserialize_sale_date(sale_data),
    )


@router.message(TradeCaptureStates.waiting_for_sale_fee)
async def capture_sale_fee_value_step(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Parse sale fee and finalize a detected sale notification."""

    data = await state.get_data()
    sale_data = data.get("pending_sale")
    if not isinstance(sale_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные о продаже потерялись. Перешли уведомление о продаже еще раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    sale_payload = _deserialize_sale_payload(sale_data)
    service = TradeCaptureService(session_maker, settings)
    fee_payload = service.parse_sale_fee(
        _message_text(message),
        default_currency=sale_payload.currency,
    )
    if fee_payload is None:
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
        payload=sale_payload,
        fee=fee_payload,
        closed_at=_deserialize_sale_date(sale_data),
    )


@router.message(StateFilter(None))
async def auto_capture_messages(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Auto-detect direct gift links and sale notifications outside explicit commands."""

    if message.from_user is None:
        raise SkipHandler()

    raw_text = _message_text(message)
    if not raw_text:
        raise SkipHandler()
    if raw_text.startswith("/") or raw_text in _KNOWN_BUTTONS:
        raise SkipHandler()

    service = TradeCaptureService(session_maker, settings)
    sale_preview = service.parse_sale_notification(raw_text, source_label=_build_source_label(message))
    if sale_preview is not None:
        if not await ensure_paid_access(message, session_maker, settings):
            return

        prepared = await service.prepare_sale_notification(
            message.from_user.id,
            raw_text=raw_text,
            source_label=_build_source_label(message),
        )
        if not prepared.handled:
            raise SkipHandler()

        if not prepared.success or prepared.payload is None or prepared.matched_deal_id is None:
            await replace_tracked_text(
                message,
                prepared.message,
                reply_markup=get_main_menu_keyboard(),
            )
            return

        await state.clear()
        await state.update_data(
            pending_sale=_serialize_sale_payload(
                prepared.payload,
                matched_deal_id=prepared.matched_deal_id,
                closed_at=message.date,
            )
        )
        await state.set_state(TradeCaptureStates.waiting_for_sale_fee)
        await replace_tracked_text(
            message,
            prepared.message,
            reply_markup=get_sale_fee_keyboard(),
        )
        return

    urls = _extract_urls_from_message(message)
    gift_payload = service.parse_gift_link(raw_text, urls=urls)
    if gift_payload is None:
        raise SkipHandler()
    if not await ensure_paid_access(message, session_maker, settings):
        return

    await state.clear()
    await state.update_data(gift=_serialize_gift(gift_payload))
    await state.set_state(TradeCaptureStates.waiting_for_buy_price)
    await replace_tracked_text(
        message,
        service.build_link_received_text(gift_payload),
        reply_markup=get_purchase_flow_keyboard(),
    )


async def _finalize_purchase(
    message: Message,
    state: FSMContext,
    *,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    ton_usd_rate,
    rate_source: str | None,
) -> None:
    """Persist purchase using FSM data and return to the main menu."""

    if message.from_user is None:
        return

    data = await state.get_data()
    gift_data = data.get("gift")
    price_data = data.get("price")
    if not isinstance(gift_data, dict) or not isinstance(price_data, dict):
        await state.clear()
        await replace_tracked_text(
            message,
            "Данные покупки потерялись. Нажми «Добавить подарок» и начни заново.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    service = TradeCaptureService(session_maker, settings)
    result = await service.save_manual_purchase(
        message.from_user.id,
        gift=_deserialize_gift(gift_data),
        price=_deserialize_price(price_data),
        ton_usd_rate=ton_usd_rate,
        rate_source=rate_source,
        opened_at=message.date,
    )
    await state.clear()
    await replace_tracked_text(
        message,
        result.message,
        reply_markup=get_main_menu_keyboard(),
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
        closed_at=closed_at,
    )
    if result.success:
        await state.clear()
        reply_markup = get_main_menu_keyboard()
    else:
        reply_markup = get_sale_fee_keyboard()

    await replace_tracked_text(
        message,
        result.message,
        reply_markup=reply_markup,
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
    """Build a simple sale source label from forward metadata."""

    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        sender_user = getattr(origin, "sender_user", None)
        if sender_user is not None:
            if sender_user.username:
                return sender_user.username
            return sender_user.full_name
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
        gift_url=data["gift_url"] or "",
        item_name=data["item_name"] or "Gift",
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


def _serialize_sale_payload(
    payload: SaleNotificationPayload,
    *,
    matched_deal_id: int,
    closed_at: datetime | None,
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


def _deserialize_sale_date(data: dict[str, str | None]) -> datetime | None:
    """Deserialize stored sale timestamp from FSM storage."""

    raw_value = data.get("closed_at")
    if not raw_value:
        return None
    return datetime.fromisoformat(raw_value)
