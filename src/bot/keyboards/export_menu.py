"""Export menu keyboard builders."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.utils.helpers import (
    get_export_builder_buttons,
    get_export_currency_buttons,
    get_export_days_buttons,
    get_export_fields_buttons,
    get_export_format_buttons,
    get_export_limit_buttons,
    get_export_menu_buttons,
    get_export_profit_buttons,
    get_export_status_buttons,
)


def get_export_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the export entry keyboard."""

    return _build_keyboard(
        get_export_menu_buttons(),
        input_field_placeholder="Выберите формат экспорта",
    )


def get_export_builder_keyboard() -> ReplyKeyboardMarkup:
    """Return the export parameter constructor root keyboard."""

    return _build_keyboard(
        get_export_builder_buttons(),
        input_field_placeholder="Выберите параметр для настройки",
    )


def get_export_format_keyboard() -> ReplyKeyboardMarkup:
    """Return the format selection keyboard."""

    return _build_keyboard(
        get_export_format_buttons(),
        input_field_placeholder="Формат файла",
    )


def get_export_status_keyboard() -> ReplyKeyboardMarkup:
    """Return the status filter keyboard."""

    return _build_keyboard(
        get_export_status_buttons(),
        input_field_placeholder="Фильтр статуса",
    )


def get_export_currency_keyboard() -> ReplyKeyboardMarkup:
    """Return the report currency keyboard."""

    return _build_keyboard(
        get_export_currency_buttons(),
        input_field_placeholder="Валюта отчета",
    )


def get_export_profit_keyboard() -> ReplyKeyboardMarkup:
    """Return the profit filter keyboard."""

    return _build_keyboard(
        get_export_profit_buttons(),
        input_field_placeholder="Фильтр прибыли",
    )


def get_export_days_keyboard() -> ReplyKeyboardMarkup:
    """Return the period filter keyboard."""

    return _build_keyboard(
        get_export_days_buttons(),
        input_field_placeholder="Период сделок",
    )


def get_export_limit_keyboard() -> ReplyKeyboardMarkup:
    """Return the limit keyboard."""

    return _build_keyboard(
        get_export_limit_buttons(),
        input_field_placeholder="Ограничение количества строк",
    )


def get_export_fields_keyboard() -> ReplyKeyboardMarkup:
    """Return the field preset keyboard."""

    return _build_keyboard(
        get_export_fields_buttons(),
        input_field_placeholder="Выберите набор колонок",
    )


def _build_keyboard(rows: list[list[str]], *, input_field_placeholder: str) -> ReplyKeyboardMarkup:
    """Build a standard reply keyboard from text rows."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button_text) for button_text in row]
            for row in rows
        ],
        resize_keyboard=True,
        input_field_placeholder=input_field_placeholder,
    )
