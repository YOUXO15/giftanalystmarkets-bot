"""Main menu keyboard builders."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.utils.helpers import get_main_menu_buttons


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the main reply keyboard."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in get_main_menu_buttons()
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
