"""Reply keyboards for manual purchase and sale capture flow."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.utils.helpers import (
    get_marketplace_choice_buttons,
    get_purchase_flow_buttons,
    get_sale_fee_buttons,
    get_sale_flow_buttons,
    get_ton_rate_choice_buttons,
)


def get_purchase_flow_keyboard() -> ReplyKeyboardMarkup:
    """Return a minimal keyboard for purchase capture steps."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_purchase_flow_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Перешли уведомление о покупке или пришли цену",
    )


def get_sale_flow_keyboard() -> ReplyKeyboardMarkup:
    """Return a minimal keyboard for sale capture steps."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_sale_flow_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Перешли уведомление о продаже или пришли сумму",
    )


def get_ton_rate_choice_keyboard() -> ReplyKeyboardMarkup:
    """Return keyboard for TON/USD rate selection."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_ton_rate_choice_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери, нужно ли сохранять курс TON/USD",
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


def get_marketplace_choice_keyboard() -> ReplyKeyboardMarkup:
    """Return keyboard for manual marketplace selection."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_marketplace_choice_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери или введи маркетплейс",
    )
