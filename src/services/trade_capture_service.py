"""Manual purchase intake and sale notification processing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import re
from urllib.parse import unquote, urlparse, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import Settings
from src.db.models.deal import Deal
from src.db.repositories.deal_repo import DealRepository
from src.db.repositories.ton_rate_repo import TonRateRepository
from src.db.repositories.user_repo import UserRepository
from src.integrations.ton_client import TonClient
from src.utils.currency_conversion import convert_amount
from src.utils.enums import Currency, DealStatus
from src.utils.formatters import format_money
from src.utils.helpers import build_registration_required_text

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_PRICE_RE = re.compile(
    r"(?P<amount>\d+(?:[.,]\d{1,8})?)\s*(?P<currency>TON|USDT|USD|EUR|RUB)?",
    re.IGNORECASE,
)
_GIFT_NUMBER_RE = re.compile(r"#(?P<number>\d{2,})")
_GIFT_NAME_WITH_NUMBER_PATTERNS = (
    re.compile(
        r"(?P<name>[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9\s'’._\-]{1,80}?)\s*#(?P<number>\d{2,})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9\s'’._\-]{1,80}?)\s*\((?P<number>\d{2,})\)",
        re.IGNORECASE,
    ),
)
_SALE_HINT_RE = re.compile(r"\b(has been sold|sold|продан|продана|продано)\b", re.IGNORECASE)
_SALE_RECEIPT_RE = re.compile(
    r"\b(you received|received|РІС‹ РїРѕР»СѓС‡РёР»Рё|РїРѕР»СѓС‡РµРЅРѕ|РїРѕСЃС‚СѓРїРёР»Рѕ|credited|zachisleno)\b",
    re.IGNORECASE,
)
_SALE_AMOUNT_PATTERNS = (
    re.compile(
        r"(?:you received|received|вы получили|получено|получил|полученная сумма)\s*[:\-]?\s*"
        r"(?P<amount>\d+(?:[.,]\d{1,8})?)\s*(?P<currency>TON|USDT|USD|EUR|RUB)",
        re.IGNORECASE,
    ),
    re.compile(r"(?P<amount>\d+(?:[.,]\d{1,8})?)\s*(?P<currency>TON|USDT|USD|EUR|RUB)", re.IGNORECASE),
)
_MARKET_ALIASES = {
    "portals": "PORTALS",
    "portal": "PORTALS",
    "fragment": "FRAGMENT",
    "getgems": "GETGEMS",
    "mrkt": "MRKT",
    "market": "MARKET",
    "telegram": "TELEGRAM",
}
@dataclass(slots=True)
class GiftLinkPayload:
    """Parsed information from a manually sent gift link."""

    gift_url: str
    item_name: str
    gift_number: str | None
    marketplace: str


@dataclass(slots=True)
class PurchasePricePayload:
    """Parsed manual purchase price entered by the user."""

    amount: Decimal
    currency: Currency


@dataclass(slots=True)
class SaleFeePayload:
    """Parsed sale fee entered by the user."""

    amount: Decimal
    currency: Currency


@dataclass(slots=True)
class RateSelectionResult:
    """Represents TON/USD rate lookup result for manual purchase flow."""

    success: bool
    rate: Decimal | None
    source: str | None
    message: str


@dataclass(slots=True)
class PurchaseSaveResult:
    """Outcome of saving a purchase to the local database."""

    success: bool
    message: str


@dataclass(slots=True)
class SaleNotificationPayload:
    """Parsed sale notification details."""

    item_name: str
    gift_number: str | None
    amount: Decimal
    currency: Currency
    marketplace: str
    raw_text: str


@dataclass(slots=True)
class PreparedSaleCaptureResult:
    """Outcome of detecting a sale before final fee confirmation."""

    handled: bool
    success: bool
    message: str
    matched_deal_id: int | None = None
    payload: SaleNotificationPayload | None = None


@dataclass(slots=True)
class SaleCaptureResult:
    """Outcome of attempting to register a sale notification."""

    handled: bool
    success: bool
    message: str


class TradeCaptureService:
    """Coordinates manual purchase intake and sale closing flows."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_maker = session_maker
        self._settings = settings
        self._ton_client = TonClient(settings)

    def build_purchase_prompt(self) -> str:
        """Return instructions for starting manual purchase intake."""

        return (
            "<b>Добавление покупки</b>\n\n"
            "Отправь ссылку на подарок одним сообщением.\n"
            "После этого я попрошу цену покупки и, при желании, сохраню курс TON/USD.\n\n"
            "Когда позже придет уведомление о продаже, просто перешли его сюда, "
            "и я попробую автоматически найти открытую сделку, а затем спрошу комиссию продажи."
        )

    def build_link_received_text(self, payload: GiftLinkPayload) -> str:
        """Return confirmation text after a gift link is parsed."""

        number_line = payload.gift_number or "—"
        return (
            "<b>Ссылка на подарок получена</b>\n\n"
            f"Название: <b>{escape(payload.item_name)}</b>\n"
            f"Номер: <b>{escape(number_line)}</b>\n"
            f"Маркет: <b>{escape(payload.marketplace)}</b>\n"
            f'Ссылка: <a href="{escape(payload.gift_url)}">открыть подарок</a>\n\n'
            "Теперь отправь цену покупки в формате <code>4.9522 TON</code>.\n"
            "Если валюту не указать, по умолчанию будет TON."
        )

    def build_rate_prompt(self, payload: GiftLinkPayload, price: PurchasePricePayload) -> str:
        """Return TON rate selection prompt after price input."""

        number_line = payload.gift_number or "—"
        return (
            "<b>Покупка почти готова</b>\n\n"
            f"Название: <b>{escape(payload.item_name)}</b>\n"
            f"Номер: <b>{escape(number_line)}</b>\n"
            f"Цена: <b>{format_money(price.amount, price.currency.value)}</b>\n"
            f"Маркет: <b>{escape(payload.marketplace)}</b>\n\n"
            "Выбери, нужно ли сохранить курс TON/USD для этой покупки."
        )

    def build_sale_fee_prompt(self, deal: Deal, payload: SaleNotificationPayload) -> str:
        """Return fee prompt after sale notification was matched."""

        return (
            "<b>Продажа найдена</b>\n\n"
            f"Название: <b>{escape(deal.item_name)}</b>\n"
            f"Номер: <b>{escape(deal.gift_number or payload.gift_number or '—')}</b>\n"
            f"Цена покупки: <b>{format_money(deal.buy_price, deal.currency.value)}</b>\n"
            f"Получено по уведомлению: <b>{format_money(payload.amount, payload.currency.value)}</b>\n"
            f"Маркет продажи: <b>{escape(payload.marketplace)}</b>\n\n"
            "Теперь отправь комиссию продажи в формате <code>0.5 TON</code>.\n"
            "Если комиссии не было, нажми <b>Без комиссии</b>.\n"
            "Если отправишь только число, я возьму валюту из уведомления о продаже."
        )

    def parse_gift_link(self, raw_text: str, urls: list[str] | None = None) -> GiftLinkPayload | None:
        """Parse the first gift URL found in user input."""

        raw_text = (raw_text or "").strip()
        if not raw_text and not urls:
            return None

        candidates = list(urls or [])
        candidates.extend(_URL_RE.findall(raw_text))
        gift_url = next(
            (
                candidate.rstrip(").,]>")
                for candidate in candidates
                if candidate.startswith(("http://", "https://"))
            ),
            None,
        )
        if gift_url is None:
            return None
        gift_url = _normalize_gift_url(gift_url)

        text_name, text_number = _extract_name_and_number(raw_text)
        url_name, url_number = _extract_name_and_number_from_url(gift_url)
        item_name = text_name or url_name or "Gift"
        gift_number = text_number or url_number
        marketplace = _infer_marketplace(gift_url, raw_text)

        return GiftLinkPayload(
            gift_url=gift_url,
            item_name=item_name,
            gift_number=gift_number,
            marketplace=marketplace,
        )

    def parse_purchase_price(self, raw_text: str) -> PurchasePricePayload | None:
        """Parse purchase price entered by the user."""

        amount_payload = self._parse_amount(raw_text, default_currency=Currency.TON, allow_zero=False)
        if amount_payload is None:
            return None
        return PurchasePricePayload(amount=amount_payload.amount, currency=amount_payload.currency)

    def parse_sale_fee(self, raw_text: str, *, default_currency: Currency) -> SaleFeePayload | None:
        """Parse sale fee entered by the user."""

        return self._parse_amount(raw_text, default_currency=default_currency, allow_zero=True)

    def parse_sale_notification(
        self,
        raw_text: str,
        *,
        source_label: str | None = None,
    ) -> SaleNotificationPayload | None:
        """Parse a marketplace sale notification."""

        normalized_text = (raw_text or "").strip()
        if not normalized_text:
            return None
        if _SALE_HINT_RE.search(normalized_text) is None and _SALE_RECEIPT_RE.search(normalized_text) is None:
            return None

        item_name, gift_number = _extract_name_and_number(normalized_text)
        if item_name is None:
            first_line = normalized_text.splitlines()[0].strip()
            item_name = _cleanup_item_name(_GIFT_NUMBER_RE.sub("", first_line)) or "Gift"

        amount: Decimal | None = None
        currency: Currency | None = None
        for pattern in _SALE_AMOUNT_PATTERNS:
            amount_match = pattern.search(normalized_text)
            if amount_match is None:
                continue
            try:
                amount = Decimal(amount_match.group("amount").replace(",", "."))
                currency = Currency(amount_match.group("currency").upper())
            except Exception:
                continue
            if amount > 0:
                break

        if amount is None or currency is None or amount <= 0:
            return None

        marketplace = _infer_marketplace("", source_label or normalized_text)
        return SaleNotificationPayload(
            item_name=item_name,
            gift_number=gift_number,
            amount=amount,
            currency=currency,
            marketplace=marketplace,
            raw_text=normalized_text,
        )

    async def fetch_today_ton_rate(self) -> RateSelectionResult:
        """Fetch and persist the current TON/USD rate."""

        payload = await self._ton_client.get_current_rate()
        if not payload.success or payload.rate is None:
            return RateSelectionResult(False, None, None, payload.message)

        await self._store_ton_rate_snapshot(payload.rate, payload.source)
        return RateSelectionResult(
            True,
            payload.rate,
            payload.source,
            f"Курс TON/USD сохранен: {self._format_decimal(payload.rate)}",
        )

    async def fetch_ton_rate_for_date(self, target_date: date) -> RateSelectionResult:
        """Fetch and persist TON/USD rate for a selected calendar date."""

        payload = await self._ton_client.get_rate_for_date(target_date)
        if not payload.success or payload.rate is None:
            return RateSelectionResult(False, None, None, payload.message)

        await self._store_ton_rate_snapshot(payload.rate, payload.source)
        return RateSelectionResult(
            True,
            payload.rate,
            payload.source,
            f"Курс за {target_date.strftime('%d.%m.%Y')} установлен: {self._format_decimal(payload.rate)}",
        )

    async def save_manual_purchase(
        self,
        telegram_id: int,
        *,
        gift: GiftLinkPayload,
        price: PurchasePricePayload,
        ton_usd_rate: Decimal | None,
        rate_source: str | None,
        opened_at: datetime | None = None,
    ) -> PurchaseSaveResult:
        """Persist a manually entered purchase in the database."""

        purchase_at = opened_at or self._now()

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            deal_repo = DealRepository(session)
            ton_rate_repo = TonRateRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return PurchaseSaveResult(False, build_registration_required_text())

                existing_open_deals = await deal_repo.get_open_by_user(user.id)
                existing_open_deal = self._find_existing_purchase(existing_open_deals, gift)
                if existing_open_deal is not None:
                    return PurchaseSaveResult(
                        False,
                        (
                            "<b>Такая покупка уже есть в учете</b>\n\n"
                            f"Подарок <b>{escape(existing_open_deal.item_name)}</b> уже записан как открытая сделка. "
                            "Если нужно, дождись продажи или добавь другой подарок."
                        ),
                    )

                if ton_usd_rate is not None:
                    await ton_rate_repo.create(ton_usd_rate, rate_source or "manual_purchase")

                deal = await deal_repo.create_manual_purchase(
                    user_id=user.id,
                    external_deal_id=self._build_external_deal_id(user.id),
                    item_name=gift.item_name,
                    gift_number=gift.gift_number,
                    gift_url=gift.gift_url,
                    marketplace=gift.marketplace,
                    buy_price=price.amount,
                    currency=price.currency,
                    ton_usd_rate=ton_usd_rate,
                    opened_at=self._ensure_utc(purchase_at),
                )

        return PurchaseSaveResult(True, self._build_purchase_saved_text(deal, rate_source=rate_source))

    async def prepare_sale_notification(
        self,
        telegram_id: int,
        *,
        raw_text: str,
        source_label: str | None = None,
    ) -> PreparedSaleCaptureResult:
        """Find an open deal for a sale notification and ask for commission."""

        payload = self.parse_sale_notification(raw_text, source_label=source_label)
        if payload is None:
            return PreparedSaleCaptureResult(False, False, "")

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            deal_repo = DealRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return PreparedSaleCaptureResult(True, False, build_registration_required_text())

                open_deals = await deal_repo.get_open_by_user(user.id)
                matched_deal = self._find_matching_open_deal(open_deals, payload)
                if matched_deal is None:
                    return PreparedSaleCaptureResult(
                        True,
                        False,
                        self._build_sale_not_found_text(payload),
                    )

        return PreparedSaleCaptureResult(
            True,
            True,
            self.build_sale_fee_prompt(matched_deal, payload),
            matched_deal_id=matched_deal.id,
            payload=payload,
        )

    async def finalize_sale_notification(
        self,
        telegram_id: int,
        *,
        matched_deal_id: int,
        payload: SaleNotificationPayload,
        fee: SaleFeePayload | None,
        closed_at: datetime | None = None,
    ) -> SaleCaptureResult:
        """Close a matched deal using provided sale fee."""

        normalized_fee = fee or SaleFeePayload(amount=Decimal("0"), currency=payload.currency)

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            deal_repo = DealRepository(session)
            ton_rate_repo = TonRateRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return SaleCaptureResult(True, False, build_registration_required_text())

                matched_deal = await deal_repo.get_by_id_for_user(matched_deal_id, user.id)
                if matched_deal is None or matched_deal.status != DealStatus.OPEN:
                    return SaleCaptureResult(
                        True,
                        False,
                        (
                            "<b>Не удалось закрыть продажу</b>\n\n"
                            "Открытая сделка уже закрыта или не найдена. "
                            "Открой раздел «Сделки» и проверь текущее состояние учета."
                        ),
                    )

                conversion_rate = matched_deal.ton_usd_rate
                if conversion_rate is None:
                    latest_rate = await ton_rate_repo.get_latest()
                    if latest_rate is not None:
                        conversion_rate = latest_rate.rate

                converted_sell_price = self._convert_amount(
                    payload.amount,
                    source_currency=payload.currency,
                    target_currency=matched_deal.currency,
                    ton_usd_rate=conversion_rate,
                )
                if converted_sell_price is None:
                    return SaleCaptureResult(
                        True,
                        False,
                        (
                            "<b>Не удалось закрыть продажу</b>\n\n"
                            "Валюту из уведомления не получилось конвертировать в валюту покупки. "
                            "Проверь, что у покупки сохранен курс TON/USD, или добавь покупку заново."
                        ),
                    )

                converted_fee = self._convert_amount(
                    normalized_fee.amount,
                    source_currency=normalized_fee.currency,
                    target_currency=matched_deal.currency,
                    ton_usd_rate=conversion_rate,
                )
                if converted_fee is None:
                    return SaleCaptureResult(
                        True,
                        False,
                        (
                            "<b>Не удалось сохранить комиссию</b>\n\n"
                            "Комиссию не получилось конвертировать в валюту сделки. "
                            "Попробуй ввести комиссию в валюте из уведомления о продаже."
                        ),
                    )

                matched_deal.sell_price = converted_sell_price
                matched_deal.status = DealStatus.CLOSED
                matched_deal.closed_at = self._ensure_utc(closed_at or self._now())
                matched_deal.fee = converted_fee
                matched_deal.net_profit = converted_sell_price - matched_deal.buy_price - converted_fee
                if not matched_deal.marketplace:
                    matched_deal.marketplace = payload.marketplace

        return SaleCaptureResult(
            True,
            True,
            self._build_sale_saved_text(payload=payload, deal=matched_deal),
        )

    async def process_sale_notification(
        self,
        telegram_id: int,
        *,
        raw_text: str,
        source_label: str | None = None,
        closed_at: datetime | None = None,
    ) -> SaleCaptureResult:
        """Backward-compatible zero-fee sale closing flow."""

        prepared = await self.prepare_sale_notification(
            telegram_id,
            raw_text=raw_text,
            source_label=source_label,
        )
        if not prepared.handled or not prepared.success or prepared.payload is None or prepared.matched_deal_id is None:
            return SaleCaptureResult(prepared.handled, prepared.success, prepared.message)

        return await self.finalize_sale_notification(
            telegram_id,
            matched_deal_id=prepared.matched_deal_id,
            payload=prepared.payload,
            fee=SaleFeePayload(amount=Decimal("0"), currency=prepared.payload.currency),
            closed_at=closed_at,
        )

    async def _store_ton_rate_snapshot(self, rate: Decimal, source: str) -> None:
        """Persist a TON/USD snapshot for later fallbacks and exports."""

        async with self._session_maker() as session:
            ton_rate_repo = TonRateRepository(session)
            async with session.begin():
                await ton_rate_repo.create(rate, source)

    def _parse_amount(
        self,
        raw_text: str,
        *,
        default_currency: Currency,
        allow_zero: bool,
    ) -> SaleFeePayload | None:
        """Parse a generic amount and currency pair."""

        match = _PRICE_RE.search((raw_text or "").strip())
        if match is None:
            return None

        try:
            amount = Decimal(match.group("amount").replace(",", "."))
        except Exception:
            return None

        if amount < 0 or (amount == 0 and not allow_zero):
            return None

        currency_raw = (match.group("currency") or default_currency.value).upper()
        try:
            currency = Currency(currency_raw)
        except ValueError:
            return None

        return SaleFeePayload(amount=amount, currency=currency)

    def _build_purchase_saved_text(self, deal: Deal, *, rate_source: str | None) -> str:
        """Build purchase confirmation text."""

        rate_text = "—"
        if deal.ton_usd_rate is not None:
            rate_text = self._format_decimal(deal.ton_usd_rate)
            if rate_source:
                rate_text = f"{rate_text} ({escape(rate_source)})"

        return (
            "<b>Покупка записана</b>\n\n"
            f"Название: <b>{escape(deal.item_name)}</b>\n"
            f"Номер: <b>{escape(deal.gift_number or '—')}</b>\n"
            f"Цена: <b>{format_money(deal.buy_price, deal.currency.value)}</b>\n"
            f"Курс TON/USD: <b>{rate_text}</b>\n"
            f"Маркет: <b>{escape(deal.marketplace or 'ручной ввод')}</b>\n"
            f"Дата: <b>{self._format_datetime(deal.opened_at)}</b>\n"
            "Статус: <b>открыта</b>\n\n"
            "Когда получишь уведомление о продаже, просто перешли его сюда."
        )

    def _build_sale_saved_text(self, *, payload: SaleNotificationPayload, deal: Deal) -> str:
        """Build sale confirmation text."""

        margin = self._format_margin_percent(deal.net_profit, deal.buy_price)
        return (
            "<b>Продажа записана</b>\n\n"
            f"Название: <b>{escape(deal.item_name)}</b>\n"
            f"Номер: <b>{escape(deal.gift_number or payload.gift_number or '—')}</b>\n"
            f"Покупка: <b>{format_money(deal.buy_price, deal.currency.value)}</b>\n"
            f"Продажа: <b>{format_money(deal.sell_price, deal.currency.value)}</b>\n"
            f"Комиссия: <b>{format_money(deal.fee, deal.currency.value)}</b>\n"
            f"Получено в уведомлении: <b>{format_money(payload.amount, payload.currency.value)}</b>\n"
            f"Чистая прибыль: <b>{format_money(deal.net_profit, deal.currency.value)}</b>\n"
            f"Маржа: <b>{margin}</b>\n"
            f"Маркет продажи: <b>{escape(payload.marketplace)}</b>\n"
            f"Дата продажи: <b>{self._format_datetime(deal.closed_at)}</b>"
        )

    def _build_sale_not_found_text(self, payload: SaleNotificationPayload) -> str:
        """Build a not-found message when no matching purchase exists."""

        return (
            "<b>Продажу распознал, но покупку не нашел</b>\n\n"
            f"Подарок: <b>{escape(payload.item_name)}</b>\n"
            f"Номер: <b>{escape(payload.gift_number or '—')}</b>\n"
            f"Сумма: <b>{format_money(payload.amount, payload.currency.value)}</b>\n\n"
            "Сначала добавь покупку по ссылке через кнопку «Добавить подарок», а потом повтори уведомление о продаже."
        )

    def _find_existing_purchase(
        self,
        deals: list[Deal],
        payload: GiftLinkPayload,
    ) -> Deal | None:
        """Find an already open purchase for the same gift."""

        payload_name = _normalize_matching_key(payload.item_name)
        payload_number = payload.gift_number

        for deal in deals:
            if deal.gift_url and deal.gift_url == payload.gift_url:
                return deal

            deal_number = deal.gift_number or _extract_number_only(deal.item_name)
            if not payload_number or deal_number != payload_number:
                continue

            if payload_name and _normalize_matching_key(deal.item_name) != payload_name:
                continue

            return deal

        return None

    def _find_matching_open_deal(
        self,
        deals: list[Deal],
        payload: SaleNotificationPayload,
    ) -> Deal | None:
        """Select the best open deal candidate for a sale notification."""

        payload_name = _normalize_matching_key(payload.item_name)

        exact_number_matches: list[Deal] = []
        fuzzy_name_matches: list[Deal] = []
        for deal in deals:
            deal_number = deal.gift_number or _extract_number_only(deal.item_name)
            deal_name = _normalize_matching_key(deal.item_name)

            if payload.gift_number and deal_number == payload.gift_number:
                if payload_name and deal_name == payload_name:
                    return deal
                exact_number_matches.append(deal)
                continue

            if payload_name and deal_name == payload_name:
                fuzzy_name_matches.append(deal)

        if exact_number_matches:
            return exact_number_matches[0]
        if fuzzy_name_matches:
            return fuzzy_name_matches[0]
        return None

    def _convert_amount(
        self,
        amount: Decimal,
        *,
        source_currency: Currency,
        target_currency: Currency,
        ton_usd_rate: Decimal | None,
    ) -> Decimal | None:
        """Convert amount between supported currencies via USD pivot."""

        return convert_amount(
            amount,
            source_currency=source_currency,
            target_currency=target_currency,
            ton_usd_rate=ton_usd_rate,
        )

    @staticmethod
    def _build_external_deal_id(user_id: int) -> str:
        """Generate a unique local identifier for manual deals."""

        return f"manual-{user_id}-{uuid4().hex[:12]}"

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        """Format Decimal with up to 8 fractional digits."""

        normalized = value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP).normalize()
        return format(normalized, "f")

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        """Format datetime for Telegram messages."""

        if value is None:
            return "—"
        normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
        return normalized.strftime("%d.%m.%Y %H:%M UTC")

    @staticmethod
    def _format_margin_percent(
        net_profit: Decimal | None,
        buy_price: Decimal,
    ) -> str:
        """Calculate margin percentage using net profit and entry price."""

        if net_profit is None or buy_price == 0:
            return "—"
        margin = (net_profit / buy_price) * Decimal("100")
        margin = margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{format(margin, 'f')}%"

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        """Normalize datetime to timezone-aware UTC."""

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _now() -> datetime:
        """Return current UTC timestamp."""

        return datetime.now(timezone.utc)


def _extract_name_and_number(text: str) -> tuple[str | None, str | None]:
    """Extract gift name and number from free text."""

    for pattern in _GIFT_NAME_WITH_NUMBER_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        name = _cleanup_item_name(match.group("name"))
        number = match.group("number")
        return name, number

    number_match = _GIFT_NUMBER_RE.search(text)
    number = number_match.group("number") if number_match is not None else None
    return None, number


def _normalize_gift_url(url: str) -> str:
    """Normalize gift URLs to reduce duplicate purchases caused by formatting noise."""

    parsed = urlsplit(url.strip())
    normalized_path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            normalized_path,
            parsed.query,
            "",
        )
    )


def _extract_name_and_number_from_url(url: str) -> tuple[str | None, str | None]:
    """Try to parse gift name and number from URL path segments."""

    parsed = urlparse(url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    for segment in reversed(path_segments):
        slug = unquote(segment).strip()
        if not slug:
            continue
        if slug.lower() in {"gift", "nft", "c", "s", "app"}:
            continue
        slug = slug.replace(".html", "")
        slug = slug.replace("%23", "#")

        hash_match = re.search(r"(?P<name>.+?)#(?P<number>\d{2,})$", slug)
        if hash_match is not None:
            return _cleanup_item_name(hash_match.group("name")), hash_match.group("number")

        dash_match = re.search(r"(?P<name>.+?)[\-_](?P<number>\d{2,})$", slug)
        if dash_match is not None:
            return _cleanup_item_name(dash_match.group("name")), dash_match.group("number")

        clean_name = _cleanup_item_name(slug)
        if clean_name is not None:
            return clean_name, None

    return None, None


def _cleanup_item_name(raw_name: str | None) -> str | None:
    """Normalize item name for storing and matching."""

    if raw_name is None:
        return None

    clean = re.sub(r"[_\-]+", " ", raw_name).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean or None


def _infer_marketplace(url: str, raw_text: str) -> str:
    """Infer marketplace label from URL or raw text."""

    haystack = f"{url} {raw_text}".lower()
    for alias, normalized in _MARKET_ALIASES.items():
        if alias in haystack:
            return normalized
    return "TELEGRAM"


def _normalize_matching_key(value: str | None) -> str | None:
    """Normalize item names for fuzzy matching."""

    if value is None:
        return None

    normalized = value.casefold()
    normalized = re.sub(r"[_\-\s]+", "", normalized)
    normalized = re.sub(r"[^a-zа-я0-9]", "", normalized)
    return normalized or None


def _extract_number_only(value: str | None) -> str | None:
    """Extract gift number from a free-form name."""

    if value is None:
        return None

    match = _GIFT_NUMBER_RE.search(value)
    if match is not None:
        return match.group("number")

    trailing_match = re.search(r"(\d{2,})$", value)
    if trailing_match is not None:
        return trailing_match.group(1)
    return None
