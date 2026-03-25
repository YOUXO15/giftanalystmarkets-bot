"""Manual purchase intake and sale notification processing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from html import escape, unescape
import re
from urllib.parse import unquote, urlparse, urlsplit, urlunsplit
from uuid import uuid4

import httpx
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
        r"(?P<name>[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9\s'’._\-]{1,80}?)\s*#(?P<number>\d{2,})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>[A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9\s'’._\-]{1,80}?)\s*\((?P<number>\d{2,})\)",
        re.IGNORECASE,
    ),
)
_PURCHASE_AMOUNT_PATTERNS = (
    re.compile(
        r"(?:for|за|price|цена|paid|оплатил|оплатила|оплачено|стоимость|amount|sum)\s*[:\-]?\s*"
        r"(?P<amount>\d+(?:[.,]\d{1,8})?)\s*(?P<currency>TON|USDT|USD|EUR|RUB)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bought|purchased|купил|купила|приобр[её]л|приобр[её]ла|acquired)[^\n]{0,80}?"
        r"(?P<amount>\d+(?:[.,]\d{1,8})?)\s*(?P<currency>TON|USDT|USD|EUR|RUB)",
        re.IGNORECASE,
    ),
)
_SALE_HINT_RE = re.compile(r"\b(has been sold|sold|продан|продана|продано)\b", re.IGNORECASE)
_SALE_RECEIPT_RE = re.compile(
    r"\b(you received|received|вы получили|получено|поступило|credited|zachisleno)\b",
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
_HTML_TITLE_PATTERNS = (
    re.compile(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](?P<title>[^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\'](?P<title>[^"\']+)["\']',
        re.IGNORECASE,
    ),
    re.compile(r"<title>\s*(?P<title>.*?)\s*</title>", re.IGNORECASE | re.DOTALL),
)
_NAME_PREFIX_RE = re.compile(
    r"^(?:you\s+)?(?:bought|purchased|купил|купила|куплено|приобр[её]л|приобр[её]ла)\s+",
    re.IGNORECASE,
)
_NAME_SUFFIX_RE = re.compile(
    r"\s*(?:has been sold|sold|продан|продана|продано)\s*$",
    re.IGNORECASE,
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
    """Parsed information about a gift reference."""

    gift_url: str | None
    item_name: str
    gift_number: str | None
    marketplace: str


@dataclass(slots=True)
class PurchasePricePayload:
    """Parsed price entered by the user or extracted from a notification."""

    amount: Decimal
    currency: Currency


@dataclass(slots=True)
class SaleFeePayload:
    """Parsed sale fee entered by the user."""

    amount: Decimal
    currency: Currency


@dataclass(slots=True)
class PurchaseInputPayload:
    """Parsed purchase notification or link payload."""

    gift: GiftLinkPayload
    price: PurchasePricePayload | None
    raw_text: str


@dataclass(slots=True)
class SaleNotificationDraft:
    """Parsed sale notification draft before the amount is fully known."""

    item_name: str
    gift_number: str | None
    amount: Decimal | None
    currency: Currency | None
    marketplace: str
    gift_url: str | None
    raw_text: str


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
    fee_prompt: str | None = None


@dataclass(slots=True)
class SaleCaptureResult:
    """Outcome of attempting to register a sale notification."""

    handled: bool
    success: bool
    message: str
    retry_stage: str | None = None


class TradeCaptureService:
    """Coordinates manual purchase intake and sale closing flows."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession] | None,
        settings: Settings,
    ) -> None:
        self._session_maker = session_maker
        self._settings = settings
        self._ton_client = TonClient(settings)

    def build_purchase_prompt(self) -> str:
        """Return instructions for starting purchase intake."""

        return (
            "<b>Добавление покупки</b>\n\n"
            "Перешли уведомление о покупке от маркетплейса одним сообщением.\n"
            "Если уведомление не содержит цену или ссылку, я спрошу недостающие данные отдельно.\n\n"
            "Поддерживается и запасной вариант: можно просто прислать ссылку на подарок."
        )

    def build_sale_prompt(self) -> str:
        """Return instructions for starting sale intake."""

        return (
            "<b>Добавление продажи</b>\n\n"
            "Перешли уведомление о продаже от маркетплейса одним сообщением.\n"
            "Я попробую определить подарок, сумму продажи и маркетплейс. Если суммы не будет, попрошу ее вручную."
        )

    def build_purchase_marketplace_request_text(self, payload: GiftLinkPayload) -> str:
        """Ask user to enter the purchase marketplace manually."""

        lines = [
            "<b>Покупка распознана частично</b>",
            "",
            f"Название: <b>{escape(payload.item_name)}</b>",
            f"Номер: <b>{escape(payload.gift_number or '—')}</b>",
        ]
        if payload.gift_url:
            lines.append(f'Ссылка: <a href="{escape(payload.gift_url)}">открыть подарок</a>')

        lines.extend(
            [
                "",
                "Маркетплейс покупки не удалось определить автоматически.",
                "Выбери его кнопкой ниже или отправь название вручную, например <code>PORTALS</code>.",
            ]
        )
        return "\n".join(lines)

    def build_sale_marketplace_request_text(self, draft: SaleNotificationDraft) -> str:
        """Ask user to enter the sale marketplace manually."""

        lines = [
            "<b>Продажа распознана частично</b>",
            "",
            f"Название: <b>{escape(draft.item_name)}</b>",
            f"Номер: <b>{escape(draft.gift_number or '—')}</b>",
        ]
        if draft.amount is not None and draft.currency is not None:
            lines.append(f"Сумма продажи: <b>{format_money(draft.amount, draft.currency.value)}</b>")
        if draft.gift_url:
            lines.append(f'Ссылка: <a href="{escape(draft.gift_url)}">открыть подарок</a>')

        lines.extend(
            [
                "",
                "Маркетплейс продажи не удалось определить автоматически.",
                "Выбери его кнопкой ниже или отправь название вручную, например <code>FRAGMENT</code>.",
            ]
        )
        return "\n".join(lines)

    def build_purchase_price_request_text(self, payload: GiftLinkPayload) -> str:
        """Return text asking user to provide a missing purchase price."""

        lines = [
            "<b>Покупка распознана</b>",
            "",
            f"Название: <b>{escape(payload.item_name)}</b>",
            f"Номер: <b>{escape(payload.gift_number or '—')}</b>",
            f"Маркет покупки: <b>{escape(payload.marketplace)}</b>",
        ]
        if payload.gift_url:
            lines.append(f'Ссылка: <a href="{escape(payload.gift_url)}">открыть подарок</a>')

        lines.extend(
            [
                "",
                "Цену в уведомлении не нашел.",
                "Теперь отправь цену покупки в формате <code>4.9522 TON</code>.",
                "Если валюту не указать, по умолчанию будет TON.",
            ]
        )
        return "\n".join(lines)

    def build_rate_prompt(self, payload: GiftLinkPayload, price: PurchasePricePayload) -> str:
        """Return TON rate selection prompt after price input."""

        lines = [
            "<b>Покупка распознана</b>",
            "",
            f"Название: <b>{escape(payload.item_name)}</b>",
            f"Номер: <b>{escape(payload.gift_number or '—')}</b>",
            f"Цена покупки: <b>{format_money(price.amount, price.currency.value)}</b>",
            f"Маркет покупки: <b>{escape(payload.marketplace)}</b>",
        ]
        if payload.gift_url:
            lines.append(f'Ссылка: <a href="{escape(payload.gift_url)}">открыть подарок</a>')

        lines.extend(
            [
                "",
                "Выбери, нужно ли сохранить курс TON/USD для этой покупки.",
            ]
        )
        return "\n".join(lines)

    def build_link_received_text(self, payload: GiftLinkPayload) -> str:
        """Backward-compatible wrapper for link-based purchase flow."""

        return self.build_purchase_price_request_text(payload)

    def build_sale_price_request_text(self, draft: SaleNotificationDraft) -> str:
        """Return text asking user to provide a missing sale amount."""

        lines = [
            "<b>Продажа распознана</b>",
            "",
            f"Название: <b>{escape(draft.item_name)}</b>",
            f"Номер: <b>{escape(draft.gift_number or '—')}</b>",
            f"Маркет продажи: <b>{escape(draft.marketplace)}</b>",
        ]
        if draft.gift_url:
            lines.append(f'Ссылка: <a href="{escape(draft.gift_url)}">открыть подарок</a>')

        lines.extend(
            [
                "",
                "Сумму продажи в уведомлении не нашел.",
                "Теперь отправь сумму продажи в формате <code>31.35 TON</code>.",
                "Если валюту не указать, по умолчанию будет TON.",
            ]
        )
        return "\n".join(lines)

    def build_sale_rate_prompt(self, deal: Deal, payload: SaleNotificationPayload) -> str:
        """Return TON-rate selection prompt for a matched sale."""

        return (
            "<b>Продажа найдена</b>\n\n"
            f"Название: <b>{escape(deal.item_name)}</b>\n"
            f"Номер: <b>{escape(deal.gift_number or payload.gift_number or '—')}</b>\n"
            f"Маркет покупки: <b>{escape(deal.marketplace or '—')}</b>\n"
            f"Маркет продажи: <b>{escape(payload.marketplace)}</b>\n"
            f"Покупка: <b>{format_money(deal.buy_price, deal.currency.value)}</b>\n"
            f"Сумма продажи: <b>{format_money(payload.amount, payload.currency.value)}</b>\n\n"
            "Выбери, нужно ли сохранить курс TON/USD для этой продажи."
        )

    def build_sale_fee_prompt(self, deal: Deal, payload: SaleNotificationPayload) -> str:
        """Return fee prompt after sale notification was matched."""

        return (
            "<b>Продажа найдена</b>\n\n"
            f"Название: <b>{escape(deal.item_name)}</b>\n"
            f"Номер: <b>{escape(deal.gift_number or payload.gift_number or '—')}</b>\n"
            f"Маркет покупки: <b>{escape(deal.marketplace or '—')}</b>\n"
            f"Маркет продажи: <b>{escape(payload.marketplace)}</b>\n"
            f"Цена покупки: <b>{format_money(deal.buy_price, deal.currency.value)}</b>\n"
            f"Сумма продажи: <b>{format_money(payload.amount, payload.currency.value)}</b>\n\n"
            "Теперь отправь комиссию продажи в формате <code>0.5 TON</code>.\n"
            "Если комиссии не было, нажми <b>Без комиссии</b>.\n"
            "Если отправишь только число, я возьму валюту из суммы продажи."
        )

    def parse_marketplace_input(self, raw_text: str) -> str | None:
        """Parse a manually entered marketplace label."""

        return _normalize_marketplace_label(raw_text)

    def should_request_manual_marketplace(
        self,
        *,
        raw_text: str,
        source_label: str | None,
        gift_url: str | None,
        marketplace: str | None,
    ) -> bool:
        """Return whether marketplace should be confirmed manually."""

        if _has_confident_marketplace_hint(gift_url or "", f"{source_label or ''} {raw_text}"):
            return False

        normalized = _normalize_marketplace_label(marketplace)
        stripped_text = _strip_urls_from_text(raw_text)
        is_link_only = bool(gift_url and not stripped_text)
        return is_link_only or normalized in {None, "TELEGRAM"}

    async def parse_purchase_input(
        self,
        raw_text: str,
        *,
        urls: list[str] | None = None,
        source_label: str | None = None,
    ) -> PurchaseInputPayload | None:
        """Parse purchase notification or fallback gift link."""

        normalized_text = (raw_text or "").strip()
        gift = _build_gift_reference(normalized_text, urls=urls, source_label=source_label)
        if gift is None:
            return None

        gift = await self.enrich_gift_reference(gift, raw_text=normalized_text)
        price = _parse_amount_by_patterns(normalized_text, _PURCHASE_AMOUNT_PATTERNS)

        return PurchaseInputPayload(
            gift=gift,
            price=PurchasePricePayload(amount=price.amount, currency=price.currency) if price else None,
            raw_text=normalized_text,
        )

    async def enrich_gift_reference(
        self,
        payload: GiftLinkPayload,
        *,
        raw_text: str = "",
    ) -> GiftLinkPayload:
        """Try to enrich gift data from page metadata when user only sent a raw link."""

        if payload.gift_url is None:
            return payload
        if _GIFT_NUMBER_RE.search(raw_text):
            return payload

        html = await self._fetch_page_html(payload.gift_url)
        if html is None:
            return payload

        page_name, page_number = _extract_name_and_number_from_html(html)
        if page_name is None and page_number is None:
            return payload

        return GiftLinkPayload(
            gift_url=payload.gift_url,
            item_name=page_name or payload.item_name,
            gift_number=page_number or payload.gift_number,
            marketplace=payload.marketplace,
        )

    def parse_gift_link(self, raw_text: str, urls: list[str] | None = None) -> GiftLinkPayload | None:
        """Parse a gift URL or text with an embedded gift reference."""

        normalized_text = (raw_text or "").strip()
        return _build_gift_reference(normalized_text, urls=urls)

    def parse_purchase_price(self, raw_text: str) -> PurchasePricePayload | None:
        """Parse purchase price entered by the user."""

        amount_payload = self._parse_amount(raw_text, default_currency=Currency.TON, allow_zero=False)
        if amount_payload is None:
            return None
        return PurchasePricePayload(amount=amount_payload.amount, currency=amount_payload.currency)

    def parse_sale_amount(self, raw_text: str, *, default_currency: Currency = Currency.TON) -> PurchasePricePayload | None:
        """Parse a manually entered sale amount."""

        amount_payload = self._parse_amount(raw_text, default_currency=default_currency, allow_zero=False)
        if amount_payload is None:
            return None
        return PurchasePricePayload(amount=amount_payload.amount, currency=amount_payload.currency)

    def parse_sale_fee(self, raw_text: str, *, default_currency: Currency) -> SaleFeePayload | None:
        """Parse sale fee entered by the user."""

        return self._parse_amount(raw_text, default_currency=default_currency, allow_zero=True)

    def parse_sale_notification_draft(
        self,
        raw_text: str,
        *,
        source_label: str | None = None,
        urls: list[str] | None = None,
    ) -> SaleNotificationDraft | None:
        """Parse sale notification details even when amount is missing."""

        normalized_text = (raw_text or "").strip()
        if not normalized_text and not urls:
            return None

        gift = _build_gift_reference(normalized_text, urls=urls, source_label=source_label)
        sale_amount = _parse_amount_by_patterns(normalized_text, _SALE_AMOUNT_PATTERNS)
        if gift is None and sale_amount is None:
            return None

        if gift is None:
            marketplace = _infer_marketplace("", f"{source_label or ''} {normalized_text}")
            item_name = _extract_title_like_name(normalized_text) or "Gift"
            gift_number = _extract_name_and_number(normalized_text)[1]
            gift_url = _extract_first_url(normalized_text, urls)
        else:
            marketplace = gift.marketplace
            item_name = gift.item_name
            gift_number = gift.gift_number
            gift_url = gift.gift_url

        return SaleNotificationDraft(
            item_name=item_name,
            gift_number=gift_number,
            amount=sale_amount.amount if sale_amount is not None else None,
            currency=sale_amount.currency if sale_amount is not None else None,
            marketplace=marketplace,
            gift_url=gift_url,
            raw_text=normalized_text,
        )

    def finalize_sale_draft(
        self,
        draft: SaleNotificationDraft,
        *,
        amount: PurchasePricePayload | None = None,
    ) -> SaleNotificationPayload | None:
        """Convert a sale draft into a complete payload."""

        resolved_amount = amount.amount if amount is not None else draft.amount
        resolved_currency = amount.currency if amount is not None else draft.currency
        if resolved_amount is None or resolved_currency is None:
            return None

        return SaleNotificationPayload(
            item_name=draft.item_name,
            gift_number=draft.gift_number,
            amount=resolved_amount,
            currency=resolved_currency,
            marketplace=draft.marketplace,
            raw_text=draft.raw_text,
        )

    def parse_sale_notification(
        self,
        raw_text: str,
        *,
        source_label: str | None = None,
    ) -> SaleNotificationPayload | None:
        """Parse a complete marketplace sale notification."""

        draft = self.parse_sale_notification_draft(raw_text, source_label=source_label)
        if draft is None:
            return None
        return self.finalize_sale_draft(draft)

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
        session_maker = self._require_session_maker()

        async with session_maker() as session:
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

    async def prepare_sale_payload(
        self,
        telegram_id: int,
        *,
        payload: SaleNotificationPayload,
    ) -> PreparedSaleCaptureResult:
        """Find an open deal for a fully parsed sale notification."""

        session_maker = self._require_session_maker()

        async with session_maker() as session:
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
            self.build_sale_rate_prompt(matched_deal, payload),
            matched_deal_id=matched_deal.id,
            payload=payload,
            fee_prompt=self.build_sale_fee_prompt(matched_deal, payload),
        )

    async def prepare_sale_notification(
        self,
        telegram_id: int,
        *,
        raw_text: str,
        source_label: str | None = None,
    ) -> PreparedSaleCaptureResult:
        """Backward-compatible entrypoint for a complete sale notification."""

        payload = self.parse_sale_notification(raw_text, source_label=source_label)
        if payload is None:
            return PreparedSaleCaptureResult(False, False, "")
        return await self.prepare_sale_payload(telegram_id, payload=payload)

    async def finalize_sale_notification(
        self,
        telegram_id: int,
        *,
        matched_deal_id: int,
        payload: SaleNotificationPayload,
        fee: SaleFeePayload | None,
        sale_ton_usd_rate: Decimal | None = None,
        closed_at: datetime | None = None,
    ) -> SaleCaptureResult:
        """Close a matched deal using provided sale fee."""

        normalized_fee = fee or SaleFeePayload(amount=Decimal("0"), currency=payload.currency)
        session_maker = self._require_session_maker()

        async with session_maker() as session:
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

                conversion_rate = sale_ton_usd_rate or matched_deal.sale_ton_usd_rate or matched_deal.ton_usd_rate
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
                        retry_stage="sale_rate",
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
                            "Попробуй ввести комиссию в валюте из суммы продажи."
                        ),
                    )

                matched_deal.sell_price = converted_sell_price
                matched_deal.status = DealStatus.CLOSED
                matched_deal.closed_at = self._ensure_utc(closed_at or self._now())
                matched_deal.fee = converted_fee
                matched_deal.net_profit = converted_sell_price - matched_deal.buy_price - converted_fee
                matched_deal.sale_marketplace = payload.marketplace
                matched_deal.sale_ton_usd_rate = conversion_rate
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

    async def _fetch_page_html(self, url: str) -> str | None:
        """Fetch page HTML for gift link metadata lookup."""

        try:
            async with httpx.AsyncClient(
                timeout=self._settings.http_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": f"{self._settings.app_name}/1.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except Exception:
            return None
        return response.text

    async def _store_ton_rate_snapshot(self, rate: Decimal, source: str) -> None:
        """Persist a TON/USD snapshot for later fallbacks and exports."""

        session_maker = self._require_session_maker()
        async with session_maker() as session:
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

        lines = [
            "<b>Покупка записана</b>",
            "",
            f"Название: <b>{escape(deal.item_name)}</b>",
            f"Номер: <b>{escape(deal.gift_number or '—')}</b>",
            f"Цена покупки: <b>{format_money(deal.buy_price, deal.currency.value)}</b>",
            f"Курс TON/USD: <b>{rate_text}</b>",
            f"Маркет покупки: <b>{escape(deal.marketplace or 'ручной ввод')}</b>",
            f"Дата покупки: <b>{self._format_datetime(deal.opened_at)}</b>",
            "Статус: <b>открыта</b>",
        ]
        if deal.gift_url:
            lines.append(f'Ссылка: <a href="{escape(deal.gift_url)}">открыть подарок</a>')

        lines.extend(
            [
                "",
                "Когда получишь уведомление о продаже, нажми «Добавить проданный подарок» и перешли его сюда.",
            ]
        )
        return "\n".join(lines)

    def _build_sale_saved_text(self, *, payload: SaleNotificationPayload, deal: Deal) -> str:
        """Build sale confirmation text."""

        margin = self._format_margin_percent(deal.net_profit, deal.buy_price)
        sale_rate = getattr(deal, "sale_ton_usd_rate", None)
        sale_rate_text = self._format_decimal(sale_rate) if sale_rate is not None else "—"
        return (
            "<b>Продажа записана</b>\n\n"
            f"Название: <b>{escape(deal.item_name)}</b>\n"
            f"Номер: <b>{escape(deal.gift_number or payload.gift_number or '—')}</b>\n"
            f"Маркет покупки: <b>{escape(deal.marketplace or '—')}</b>\n"
            f"Маркет продажи: <b>{escape(deal.sale_marketplace or payload.marketplace)}</b>\n"
            f"Покупка: <b>{format_money(deal.buy_price, deal.currency.value)}</b>\n"
            f"Продажа: <b>{format_money(deal.sell_price, deal.currency.value)}</b>\n"
            f"Комиссия: <b>{format_money(deal.fee, deal.currency.value)}</b>\n"
            f"Чистая прибыль: <b>{format_money(deal.net_profit, deal.currency.value)}</b>\n"
            f"Маржа: <b>{margin}</b>\n"
            f"Курс TON/USD продажи: <b>{sale_rate_text}</b>\n"
            f"Дата продажи: <b>{self._format_datetime(deal.closed_at)}</b>"
        )

    def _build_sale_not_found_text(self, payload: SaleNotificationPayload) -> str:
        """Build a not-found message when no matching purchase exists."""

        return (
            "<b>Продажу распознал, но покупку не нашел</b>\n\n"
            f"Подарок: <b>{escape(payload.item_name)}</b>\n"
            f"Номер: <b>{escape(payload.gift_number or '—')}</b>\n"
            f"Сумма продажи: <b>{format_money(payload.amount, payload.currency.value)}</b>\n\n"
            "Сначала добавь покупку через кнопку «Добавить купленный подарок», а потом повтори уведомление о продаже."
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
            if payload.gift_url and deal.gift_url and deal.gift_url == payload.gift_url:
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

    def _require_session_maker(self) -> async_sessionmaker[AsyncSession]:
        """Return configured session maker or fail loudly in unsupported contexts."""

        if self._session_maker is None:
            raise RuntimeError("TradeCaptureService requires a session maker for database operations.")
        return self._session_maker


def _build_gift_reference(
    raw_text: str,
    *,
    urls: list[str] | None = None,
    source_label: str | None = None,
) -> GiftLinkPayload | None:
    """Build a gift reference from text, preview links and source metadata."""

    normalized_text = (raw_text or "").strip()
    gift_url = _extract_first_url(normalized_text, urls)
    if gift_url is not None:
        gift_url = _normalize_gift_url(gift_url)

    text_name, text_number = _extract_name_and_number(normalized_text)
    url_name, url_number = _extract_name_and_number_from_url(gift_url) if gift_url else (None, None)

    item_name = text_name or _extract_title_like_name(normalized_text) or url_name
    gift_number = text_number or url_number
    marketplace = _infer_marketplace(gift_url or "", f"{source_label or ''} {normalized_text}")

    if item_name is None and gift_number is None and gift_url is None:
        return None

    return GiftLinkPayload(
        gift_url=gift_url,
        item_name=item_name or "Gift",
        gift_number=gift_number,
        marketplace=marketplace,
    )


def _extract_first_url(raw_text: str, urls: list[str] | None) -> str | None:
    """Return the first candidate URL from entities or plain text."""

    candidates = list(urls or [])
    candidates.extend(_URL_RE.findall(raw_text))
    return next(
        (
            candidate.rstrip(").,]>")
            for candidate in candidates
            if candidate.startswith(("http://", "https://"))
        ),
        None,
    )


def _parse_amount_by_patterns(
    raw_text: str,
    patterns: tuple[re.Pattern[str], ...],
) -> PurchasePricePayload | None:
    """Parse an amount using a list of contextual regexes."""

    for pattern in patterns:
        match = pattern.search(raw_text)
        if match is None:
            continue
        try:
            amount = Decimal(match.group("amount").replace(",", "."))
            currency = Currency(match.group("currency").upper())
        except Exception:
            continue
        if amount <= 0:
            continue
        return PurchasePricePayload(amount=amount, currency=currency)
    return None


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


def _extract_name_and_number_from_html(html: str) -> tuple[str | None, str | None]:
    """Extract gift title metadata from fetched HTML."""

    for pattern in _HTML_TITLE_PATTERNS:
        match = pattern.search(html)
        if match is None:
            continue
        title = unescape(re.sub(r"\s+", " ", match.group("title"))).strip()
        title = re.sub(r"\s*[-|]\s*Telegram.*$", "", title, flags=re.IGNORECASE)
        name, number = _extract_name_and_number(title)
        if name is not None or number is not None:
            return name, number
    return None, None


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


def _extract_title_like_name(text: str) -> str | None:
    """Extract a probable gift title from free-form notification text."""

    for raw_line in text.splitlines():
        line = _cleanup_item_name(_URL_RE.sub("", raw_line).strip())
        if not line:
            continue
        if _parse_amount_by_patterns(line, _SALE_AMOUNT_PATTERNS) is not None:
            continue
        if _parse_amount_by_patterns(line, _PURCHASE_AMOUNT_PATTERNS) is not None:
            continue
        if _SALE_RECEIPT_RE.search(line):
            continue
        if line.lower() in {"telegram"}:
            continue
        if len(line) > 80:
            continue
        return line
    return None


def _cleanup_item_name(raw_name: str | None) -> str | None:
    """Normalize item name for storing and matching."""

    if raw_name is None:
        return None

    clean = re.sub(r"[_\-]+", " ", raw_name).strip()
    clean = _NAME_PREFIX_RE.sub("", clean)
    clean = _NAME_SUFFIX_RE.sub("", clean)
    clean = re.sub(r"\s+", " ", clean)
    clean = clean.strip(" :,-")
    return clean or None


def _infer_marketplace(url: str, raw_text: str) -> str:
    """Infer marketplace label from URL or raw text."""

    haystack = f"{url} {raw_text}".lower()
    for alias, normalized in _MARKET_ALIASES.items():
        if alias in haystack:
            return normalized
    return "TELEGRAM"


def _has_confident_marketplace_hint(url: str, raw_text: str) -> bool:
    """Return whether we have a reliable non-generic marketplace hint."""

    haystack = f"{url} {raw_text}".lower()
    for alias, normalized in _MARKET_ALIASES.items():
        if normalized == "TELEGRAM":
            continue
        if alias in haystack:
            return True
    return False


def _normalize_marketplace_label(raw_text: str | None) -> str | None:
    """Normalize a manually entered marketplace label."""

    if raw_text is None:
        return None

    normalized = re.sub(r"\s+", " ", raw_text.strip())
    if not normalized:
        return None

    lowered = normalized.casefold()
    for alias, market in _MARKET_ALIASES.items():
        if alias in lowered:
            return market

    compact = re.sub(r"[^\w -]", "", normalized, flags=re.UNICODE).strip()
    if not compact:
        return None
    return compact.upper()


def _strip_urls_from_text(raw_text: str) -> str:
    """Remove URLs from message text and normalize surrounding whitespace."""

    cleaned = _URL_RE.sub("", raw_text or "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _normalize_matching_key(value: str | None) -> str | None:
    """Normalize item names for fuzzy matching."""

    if value is None:
        return None

    normalized = value.casefold()
    normalized = re.sub(r"[_\-\s]+", "", normalized)
    normalized = re.sub(r"[^a-zа-яё0-9]", "", normalized)
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
