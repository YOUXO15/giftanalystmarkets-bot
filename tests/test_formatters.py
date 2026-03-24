"""Smoke tests for utility formatters."""

from decimal import Decimal

from src.utils.enums import Currency
from src.utils.formatters import format_bool_flag, format_money


def test_format_money_rounds_to_two_decimal_places() -> None:
    assert format_money(Decimal("12.345"), Currency.USD) == "12.35 USD"


def test_format_bool_flag() -> None:
    assert format_bool_flag(True) == "включено"
    assert format_bool_flag(False) == "выключено"
