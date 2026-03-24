"""Shared currency conversion helpers used across services."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.utils.enums import Currency

USD_PER_UNIT: dict[Currency, Decimal] = {
    Currency.USD: Decimal("1"),
    Currency.USDT: Decimal("1"),
    Currency.EUR: Decimal("1.08"),
    Currency.RUB: Decimal("0.011"),
}


def normalize_currency(value: Currency | str | None) -> Currency | None:
    """Normalize a raw currency value into the Currency enum."""

    if value is None:
        return None
    if isinstance(value, Currency):
        return value

    try:
        return Currency(str(value).upper())
    except ValueError:
        return None


def convert_amount(
    amount: Decimal | int | float | None,
    *,
    source_currency: Currency | str,
    target_currency: Currency,
    ton_usd_rate: Decimal | None,
    quantize_to: str | None = "0.00000001",
) -> Decimal | None:
    """Convert an amount between supported currencies via USD."""

    if amount is None:
        return None

    source = normalize_currency(source_currency)
    if source is None:
        return None

    amount_decimal = Decimal(str(amount))
    if source == target_currency:
        return _quantize(amount_decimal, quantize_to)

    usd_amount = to_usd(amount_decimal, source_currency=source, ton_usd_rate=ton_usd_rate)
    if usd_amount is None:
        return None

    converted = from_usd(usd_amount, target_currency=target_currency, ton_usd_rate=ton_usd_rate)
    if converted is None:
        return None

    return _quantize(converted, quantize_to)


def convert_amount_to_ton(
    amount: Decimal | int | float | None,
    *,
    source_currency: Currency | str,
    ton_usd_rate: Decimal | None,
    quantize_to: str | None = "0.00000001",
) -> Decimal | None:
    """Convert an amount from any supported currency into TON."""

    return convert_amount(
        amount,
        source_currency=source_currency,
        target_currency=Currency.TON,
        ton_usd_rate=ton_usd_rate,
        quantize_to=quantize_to,
    )


def to_usd(
    amount: Decimal,
    *,
    source_currency: Currency,
    ton_usd_rate: Decimal | None,
) -> Decimal | None:
    """Convert an amount into USD."""

    if source_currency is Currency.TON:
        if ton_usd_rate is None or ton_usd_rate <= 0:
            return None
        return amount * ton_usd_rate

    usd_per_unit = USD_PER_UNIT.get(source_currency)
    if usd_per_unit is None:
        return None
    return amount * usd_per_unit


def from_usd(
    amount: Decimal,
    *,
    target_currency: Currency,
    ton_usd_rate: Decimal | None,
) -> Decimal | None:
    """Convert a USD amount to the target currency."""

    if target_currency is Currency.TON:
        if ton_usd_rate is None or ton_usd_rate <= 0:
            return None
        return amount / ton_usd_rate

    usd_per_unit = USD_PER_UNIT.get(target_currency)
    if usd_per_unit is None or usd_per_unit == 0:
        return None
    return amount / usd_per_unit


def _quantize(value: Decimal, quantize_to: str | None) -> Decimal:
    """Quantize converted values when a scale is requested."""

    if quantize_to is None:
        return value
    return value.quantize(Decimal(quantize_to), rounding=ROUND_HALF_UP)
