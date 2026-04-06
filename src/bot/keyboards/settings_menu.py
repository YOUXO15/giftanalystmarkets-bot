"""Settings menu keyboard builders."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.utils.enums import Language
from src.utils.helpers import get_language_menu_buttons, get_settings_menu_buttons


def get_settings_menu_keyboard(language: Language | str | None = None) -> ReplyKeyboardMarkup:
    """Return the settings reply keyboard."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_settings_menu_buttons(language)
        ],
        resize_keyboard=True,
        input_field_placeholder="User settings",
    )


def get_language_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the language selection keyboard."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_language_menu_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Language",
    )
