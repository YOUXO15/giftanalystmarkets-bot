"""Subscription menu keyboard builders."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.utils.enums import Language
from src.utils.helpers import get_subscription_menu_buttons


def get_subscription_menu_keyboard(language: Language | str | None = None) -> ReplyKeyboardMarkup:
    """Return the subscription management keyboard."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_subscription_menu_buttons(language)
        ],
        resize_keyboard=True,
        input_field_placeholder="Subscription",
    )
