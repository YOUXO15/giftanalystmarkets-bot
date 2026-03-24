"""Reply keyboards for manual purchase and sale capture flow."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.utils.helpers import (
    get_purchase_flow_buttons,
    get_sale_fee_buttons,
    get_ton_rate_choice_buttons,
)


def get_purchase_flow_keyboard() -> ReplyKeyboardMarkup:
    """Return a minimal keyboard for link and price input steps."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_purchase_flow_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Отправь ссылку или цену покупки",
    )


def get_ton_rate_choice_keyboard() -> ReplyKeyboardMarkup:
    """Return keyboard for TON/USD rate selection."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_ton_rate_choice_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери вариант сохранения курса",
    )


def get_sale_fee_keyboard() -> ReplyKeyboardMarkup:
    """Return keyboard for sale fee input."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_sale_fee_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Введи комиссию продажи",
    )
