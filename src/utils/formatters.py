"""Formatting helpers for bot messages."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.utils.enums import Currency


def format_money(amount: Decimal | int | float | None, currency: Currency | str) -> str:
    """Format numeric amounts for Telegram messages."""

    if amount is None:
        return "—"

    decimal_amount = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{decimal_amount} {currency}"


def format_bool_flag(value: bool) -> str:
    """Render a user-friendly enabled or disabled flag."""

    return "включено" if value else "выключено"
