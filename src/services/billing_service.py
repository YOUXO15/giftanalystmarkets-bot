"""Subscription and billing workflows based on Crypto Pay invoices."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import Settings
from src.db.models.payment_invoice import PaymentInvoice
from src.db.models.user import User
from src.db.models.user_subscription import UserSubscription
from src.db.repositories.payment_invoice_repo import PaymentInvoiceRepository
from src.db.repositories.subscription_repo import SubscriptionRepository
from src.db.repositories.user_repo import UserRepository
from src.integrations.crypto_pay_client import CryptoPayApiError, CryptoPayClient, CryptoPayInvoice
from src.utils.enums import BillingPlanType, Currency, PaymentInvoiceStatus, SubscriptionStatus
from src.utils.helpers import build_registration_required_text

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SubscriptionQuote:
    """Calculated price and plan label for the next invoice."""

    amount: Decimal
    asset: Currency
    plan_type: BillingPlanType
    title: str


@dataclass(slots=True)
class BillingActionResult:
    """Result of a billing action initiated from the bot UI."""

    success: bool
    message: str
    reply_to_main_menu: bool = False


@dataclass(slots=True)
class SubscriptionAccessResult:
    """Outcome of access verification for a protected feature."""

    allowed: bool
    message: str


@dataclass(slots=True)
class BillingContext:
    """Snapshot of billing-related state for a specific user."""

    user: User
    subscription: UserSubscription
    latest_invoice: PaymentInvoice | None


class BillingService:
    """Coordinates subscription pricing, invoices, and access control."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._session_maker = session_maker
        self._settings = settings
        self._client = CryptoPayClient(settings) if settings.is_crypto_pay_configured else None

    async def build_subscription_overview(self, telegram_id: int) -> str:
        """Build the subscription status screen for the current user."""

        context = await self._load_context_by_telegram_id(telegram_id)
        if context is None:
            return build_registration_required_text()

        context = await self._refresh_active_invoice_if_needed(context)
        quote = self._build_quote(context.subscription)
        return self._build_subscription_overview_text(context, quote)

    async def ensure_analytics_access(self, telegram_id: int) -> SubscriptionAccessResult:
        """Check whether the user can access paid analytics features."""

        context = await self._load_context_by_telegram_id(telegram_id)
        if context is None:
            return SubscriptionAccessResult(False, build_registration_required_text())

        if self._is_subscription_active(context.subscription):
            return SubscriptionAccessResult(True, "")

        context = await self._refresh_active_invoice_if_needed(context)
        if self._is_subscription_active(context.subscription):
            return SubscriptionAccessResult(True, "")

        quote = self._build_quote(context.subscription)
        return SubscriptionAccessResult(
            False,
            self._build_paywall_text(context, quote),
        )

    async def create_or_reuse_invoice(self, telegram_id: int) -> BillingActionResult:
        """Create a new invoice or reuse an existing active one."""

        context = await self._load_context_by_telegram_id(telegram_id)
        if context is None:
            return BillingActionResult(False, build_registration_required_text())

        if self._is_subscription_active(context.subscription):
            quote = self._build_quote(context.subscription)
            return BillingActionResult(
                True,
                self._build_subscription_overview_text(context, quote),
                reply_to_main_menu=True,
            )

        if not self._settings.is_crypto_pay_configured or self._client is None:
            return BillingActionResult(
                False,
                (
                    "<b>Оплата пока не настроена</b>\n\n"
                    "Заполни `CRYPTO_PAY_API_TOKEN` и при необходимости `CRYPTO_PAY_BASE_URL`, "
                    "после чего перезапусти бота."
                ),
            )

        context = await self._refresh_active_invoice_if_needed(context)
        if self._is_subscription_active(context.subscription):
            quote = self._build_quote(context.subscription)
            return BillingActionResult(
                True,
                self._build_subscription_overview_text(context, quote),
                reply_to_main_menu=True,
            )

        quote = self._build_quote(context.subscription)
        if (
            context.latest_invoice is not None
            and context.latest_invoice.status == PaymentInvoiceStatus.ACTIVE
            and self._invoice_matches_quote(context.latest_invoice, quote)
        ):
            return BillingActionResult(
                True,
                self._build_invoice_ready_text(
                    context=context,
                    quote=quote,
                    invoice=context.latest_invoice,
                    reused=True,
                ),
            )
        if context.latest_invoice is not None and context.latest_invoice.status == PaymentInvoiceStatus.ACTIVE:
            await self._expire_invoice_locally(context.latest_invoice.provider_invoice_id)

        payload = self._build_invoice_payload(context.user.id, quote)

        try:
            remote_invoice = await self._client.create_invoice(
                amount=quote.amount,
                asset=quote.asset,
                description=self._build_invoice_description(quote),
                payload=payload,
            )
        except CryptoPayApiError as exc:
            logger.warning("Failed to create Crypto Pay invoice for user_id=%s: %s", context.user.id, exc)
            return BillingActionResult(
                False,
                (
                    "<b>Не удалось создать счёт</b>\n\n"
                    f"Crypto Pay вернул ошибку: <code>{escape(str(exc))}</code>"
                ),
            )

        local_invoice = await self._store_invoice(context.user.id, quote, remote_invoice)
        refreshed_context = await self._load_context_by_user_id(context.user.id)
        if refreshed_context is None:
            return BillingActionResult(False, "Не удалось загрузить состояние подписки после создания счёта.")

        return BillingActionResult(
            True,
            self._build_invoice_ready_text(
                context=refreshed_context,
                quote=quote,
                invoice=local_invoice,
                reused=False,
            ),
        )

    async def refresh_payment_status(self, telegram_id: int) -> BillingActionResult:
        """Refresh the latest active invoice and activate subscription if paid."""

        context = await self._load_context_by_telegram_id(telegram_id)
        if context is None:
            return BillingActionResult(False, build_registration_required_text())

        if self._is_subscription_active(context.subscription):
            quote = self._build_quote(context.subscription)
            return BillingActionResult(
                True,
                self._build_subscription_overview_text(context, quote),
                reply_to_main_menu=True,
            )

        if context.latest_invoice is None:
            quote = self._build_quote(context.subscription)
            return BillingActionResult(
                False,
                (
                    "<b>Активных счетов пока нет</b>\n\n"
                    f"Текущая цена для тебя: <b>{self._format_amount(quote.amount, quote.asset)}</b>.\n"
                    "Нажми «Оплатить подписку», чтобы создать новый счёт."
                ),
            )

        if not self._settings.is_crypto_pay_configured or self._client is None:
            return BillingActionResult(
                False,
                (
                    "<b>Невозможно проверить оплату</b>\n\n"
                    "Crypto Pay API не настроен в конфиге приложения."
                ),
            )

        refreshed_context = await self._refresh_active_invoice_if_needed(context)
        quote = self._build_quote(refreshed_context.subscription)

        if self._is_subscription_active(refreshed_context.subscription):
            return BillingActionResult(
                True,
                self._build_subscription_overview_text(refreshed_context, quote),
                reply_to_main_menu=True,
            )

        latest_invoice = refreshed_context.latest_invoice
        if latest_invoice is None:
            return BillingActionResult(
                False,
                "Счёт больше не найден локально. Создай новый через кнопку «Оплатить подписку».",
            )

        if latest_invoice.status == PaymentInvoiceStatus.ACTIVE and self._invoice_matches_quote(
            latest_invoice,
            quote,
        ):
            return BillingActionResult(
                True,
                self._build_invoice_ready_text(
                    context=refreshed_context,
                    quote=quote,
                    invoice=latest_invoice,
                    reused=True,
                ),
            )
        if latest_invoice.status == PaymentInvoiceStatus.ACTIVE:
            return BillingActionResult(
                False,
                (
                    "<b>Старый счёт больше не актуален</b>\n\n"
                    "Он был создан по прежнему тарифу. Нажми «Оплатить подписку», "
                    "и я создам новый счёт по текущей цене."
                ),
            )

        return BillingActionResult(
            False,
            (
                f"<b>Счёт {self._format_invoice_status(latest_invoice.status).lower()}</b>\n\n"
                "Если оплата ещё не производилась, создай новый счёт и повтори попытку."
            ),
        )

    @staticmethod
    def calculate_next_period(
        now: datetime,
        current_period_ends_at: datetime | None,
        period_days: int,
    ) -> tuple[datetime, datetime]:
        """Calculate the next subscription period bounds."""

        period_start = now
        if current_period_ends_at is not None and current_period_ends_at > now:
            period_start = current_period_ends_at
        period_end = period_start + timedelta(days=period_days)
        return period_start, period_end

    def _build_quote(self, subscription: UserSubscription) -> SubscriptionQuote:
        """Return the current monthly price for a user."""

        return SubscriptionQuote(
            amount=self._settings.subscription_monthly_price_ton,
            asset=self._settings.crypto_pay_asset,
            plan_type=BillingPlanType.MONTHLY,
            title="Ежемесячная подписка",
        )

    @staticmethod
    def _invoice_matches_quote(invoice: PaymentInvoice, quote: SubscriptionQuote) -> bool:
        """Return whether an active invoice still matches the current pricing rules."""

        return (
            invoice.asset == quote.asset
            and invoice.plan_type == quote.plan_type
            and Decimal(str(invoice.amount)) == Decimal(str(quote.amount))
        )

    async def _load_context_by_telegram_id(self, telegram_id: int) -> BillingContext | None:
        """Load billing context by Telegram identifier."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            subscription_repo = SubscriptionRepository(session)
            invoice_repo = PaymentInvoiceRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return None

                subscription = await subscription_repo.get_by_user_id(user.id)
                if subscription is None:
                    subscription = await subscription_repo.create_default(user.id)

                self._sync_subscription_status(subscription)
                latest_invoice = await invoice_repo.get_latest_for_user(user.id)

            return BillingContext(user=user, subscription=subscription, latest_invoice=latest_invoice)

    async def _load_context_by_user_id(self, user_id: int) -> BillingContext | None:
        """Load billing context by internal user identifier."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            subscription_repo = SubscriptionRepository(session)
            invoice_repo = PaymentInvoiceRepository(session)

            async with session.begin():
                user = await user_repo.get_by_id(user_id)
                if user is None:
                    return None

                subscription = await subscription_repo.get_by_user_id(user.id)
                if subscription is None:
                    subscription = await subscription_repo.create_default(user.id)

                self._sync_subscription_status(subscription)
                latest_invoice = await invoice_repo.get_latest_for_user(user.id)

            return BillingContext(user=user, subscription=subscription, latest_invoice=latest_invoice)

    async def _refresh_active_invoice_if_needed(self, context: BillingContext) -> BillingContext:
        """Refresh the latest invoice if it is still active."""

        latest_invoice = context.latest_invoice
        if latest_invoice is None or latest_invoice.status != PaymentInvoiceStatus.ACTIVE:
            return context
        if not self._settings.is_crypto_pay_configured or self._client is None:
            return context

        try:
            remote_invoice = await self._client.get_invoice(latest_invoice.provider_invoice_id)
        except CryptoPayApiError as exc:
            logger.warning(
                "Failed to refresh Crypto Pay invoice for user_id=%s invoice_id=%s: %s",
                context.user.id,
                latest_invoice.provider_invoice_id,
                exc,
            )
            return context

        await self._apply_remote_invoice_state(
            user_id=context.user.id,
            provider_invoice_id=latest_invoice.provider_invoice_id,
            remote_invoice=remote_invoice,
        )
        refreshed_context = await self._load_context_by_user_id(context.user.id)
        return refreshed_context or context

    async def _apply_remote_invoice_state(
        self,
        *,
        user_id: int,
        provider_invoice_id: int,
        remote_invoice: CryptoPayInvoice | None,
    ) -> None:
        """Persist remote invoice status and activate subscription if it was paid."""

        async with self._session_maker() as session:
            invoice_repo = PaymentInvoiceRepository(session)
            subscription_repo = SubscriptionRepository(session)

            async with session.begin():
                invoice = await invoice_repo.get_by_provider_invoice_id(provider_invoice_id)
                if invoice is None:
                    return

                subscription = await subscription_repo.get_by_user_id(user_id)
                if subscription is None:
                    subscription = await subscription_repo.create_default(user_id)

                self._sync_subscription_status(subscription)

                if remote_invoice is None:
                    invoice.status = PaymentInvoiceStatus.EXPIRED
                    invoice.expires_at = self._now()
                    return

                invoice.status = remote_invoice.status
                invoice.invoice_hash = remote_invoice.invoice_hash
                invoice.pay_url = remote_invoice.bot_invoice_url
                invoice.description = remote_invoice.description
                invoice.payload = remote_invoice.payload
                invoice.expires_at = remote_invoice.expires_at
                invoice.paid_at = remote_invoice.paid_at

                if invoice.status == PaymentInvoiceStatus.PAID and invoice.processed_at is None:
                    self._activate_subscription(
                        subscription=subscription,
                        invoice=invoice,
                        paid_at=remote_invoice.paid_at or self._now(),
                    )

    async def _store_invoice(
        self,
        user_id: int,
        quote: SubscriptionQuote,
        remote_invoice: CryptoPayInvoice,
    ) -> PaymentInvoice:
        """Store a just-created remote invoice in the local database."""

        async with self._session_maker() as session:
            invoice_repo = PaymentInvoiceRepository(session)

            async with session.begin():
                invoice = await invoice_repo.create_invoice(
                    user_id=user_id,
                    provider_invoice_id=remote_invoice.invoice_id,
                    invoice_hash=remote_invoice.invoice_hash,
                    asset=remote_invoice.asset or quote.asset,
                    amount=remote_invoice.amount,
                    plan_type=quote.plan_type,
                    status=remote_invoice.status,
                    pay_url=remote_invoice.bot_invoice_url,
                    description=remote_invoice.description,
                    payload=remote_invoice.payload,
                    expires_at=remote_invoice.expires_at,
                    paid_at=remote_invoice.paid_at,
                )

            return invoice

    async def _expire_invoice_locally(self, provider_invoice_id: int) -> None:
        """Mark a stale local invoice as expired so it is not reused again."""

        async with self._session_maker() as session:
            invoice_repo = PaymentInvoiceRepository(session)

            async with session.begin():
                invoice = await invoice_repo.get_by_provider_invoice_id(provider_invoice_id)
                if invoice is None or invoice.status != PaymentInvoiceStatus.ACTIVE:
                    return
                invoice.status = PaymentInvoiceStatus.EXPIRED
                invoice.expires_at = self._now()

    def _activate_subscription(
        self,
        *,
        subscription: UserSubscription,
        invoice: PaymentInvoice,
        paid_at: datetime,
    ) -> None:
        """Apply a paid invoice to the user's subscription record."""

        paid_at_utc = self._ensure_utc(paid_at)
        period_start, period_end = self.calculate_next_period(
            paid_at_utc,
            subscription.current_period_ends_at,
            self._settings.subscription_period_days,
        )
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_started_at = period_start
        subscription.current_period_ends_at = period_end
        subscription.last_paid_at = paid_at_utc
        if subscription.first_paid_at is None:
            subscription.first_paid_at = paid_at_utc
        subscription.discount_consumed = True
        invoice.paid_at = paid_at_utc
        invoice.processed_at = self._now()

    def _sync_subscription_status(self, subscription: UserSubscription) -> None:
        """Update local subscription status using current UTC time."""

        now = self._now()
        if subscription.current_period_ends_at is None:
            if subscription.status == SubscriptionStatus.ACTIVE:
                subscription.status = SubscriptionStatus.INACTIVE
            return

        if self._ensure_utc(subscription.current_period_ends_at) <= now:
            subscription.status = SubscriptionStatus.EXPIRED
        elif subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.ACTIVE

    def _is_subscription_active(self, subscription: UserSubscription) -> bool:
        """Return whether access should currently be granted."""

        self._sync_subscription_status(subscription)
        if subscription.status != SubscriptionStatus.ACTIVE:
            return False
        if subscription.current_period_ends_at is None:
            return False
        return self._ensure_utc(subscription.current_period_ends_at) > self._now()

    def _build_subscription_overview_text(
        self,
        context: BillingContext,
        quote: SubscriptionQuote,
    ) -> str:
        """Build the main subscription status screen."""

        subscription = context.subscription
        latest_invoice = context.latest_invoice

        lines = [
            "<b>Подписка GiftAnalystMarkets</b>",
            "",
            f"Статус: <b>{self._format_subscription_status(subscription)}</b>",
        ]

        if subscription.current_period_ends_at is not None and self._is_subscription_active(subscription):
            lines.append(
                f"Доступ открыт до: <b>{self._format_datetime(subscription.current_period_ends_at)}</b>"
            )
        elif subscription.current_period_ends_at is not None:
            lines.append(
                f"Последний оплаченный период закончился: "
                f"<b>{self._format_datetime(subscription.current_period_ends_at)}</b>"
            )

        lines.extend(
            [
                f"Текущий тариф: <b>{self._format_amount(self._settings.subscription_monthly_price_ton, quote.asset)}</b> / "
                f"{self._settings.subscription_period_days} дней",
                f"Следующая оплата: <b>{self._format_amount(quote.amount, quote.asset)}</b>",
            ]
        )

        if latest_invoice is not None:
            lines.extend(
                [
                    "",
                    "<b>Последний счёт</b>",
                    f"Статус счёта: <b>{self._format_invoice_status(latest_invoice.status)}</b>",
                    f"Сумма: <b>{self._format_amount(latest_invoice.amount, latest_invoice.asset)}</b>",
                ]
            )
            if latest_invoice.expires_at is not None and latest_invoice.status == PaymentInvoiceStatus.ACTIVE:
                lines.append(f"Действителен до: <b>{self._format_datetime(latest_invoice.expires_at)}</b>")
            if latest_invoice.status == PaymentInvoiceStatus.ACTIVE:
                lines.append(
                    f'Ссылка на оплату: <a href="{escape(latest_invoice.pay_url)}">Открыть счёт в Crypto Bot</a>'
                )

        if not self._settings.is_crypto_pay_configured:
            lines.extend(
                [
                    "",
                    "Оплата ещё не настроена в конфиге приложения.",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "Используй кнопки ниже, чтобы создать счёт или проверить уже совершённую оплату.",
                ]
            )

        return "\n".join(lines)

    def _build_paywall_text(self, context: BillingContext, quote: SubscriptionQuote) -> str:
        """Build access denial text with billing instructions."""

        lines = [
            "<b>Доступ к аналитике по подписке</b>",
            "",
            "Синхронизация, статистика, сделки, экспорт и курс TON доступны только после оплаты.",
            f"Текущий тариф: <b>{self._format_amount(quote.amount, quote.asset)}</b> "
            f"за {self._settings.subscription_period_days} дней "
            f"({escape(quote.title.lower())}).",
        ]

        latest_invoice = context.latest_invoice
        if latest_invoice is not None and latest_invoice.status == PaymentInvoiceStatus.ACTIVE:
            lines.extend(
                [
                    "",
                    "У тебя уже есть активный счёт.",
                    f'Оплатить можно здесь: <a href="{escape(latest_invoice.pay_url)}">Открыть счёт</a>',
                ]
            )

        lines.extend(
            [
                "",
                "Нажми «Оплатить подписку», чтобы получить ссылку на счёт, "
                "или «Проверить оплату», если уже оплатил.",
            ]
        )
        return "\n".join(lines)

    def _build_invoice_ready_text(
        self,
        *,
        context: BillingContext,
        quote: SubscriptionQuote,
        invoice: PaymentInvoice,
        reused: bool,
    ) -> str:
        """Build a message with a ready-to-pay invoice."""

        header = "Активный счёт уже готов" if reused else "Счёт на оплату создан"
        lines = [
            f"<b>{header}</b>",
            "",
            f"Тариф: <b>{escape(quote.title)}</b>",
            f"Сумма: <b>{self._format_amount(invoice.amount, invoice.asset)}</b>",
        ]

        if invoice.expires_at is not None:
            lines.append(f"Счёт действует до: <b>{self._format_datetime(invoice.expires_at)}</b>")

        if self._is_subscription_active(context.subscription):
            lines.append(
                f"Текущая подписка активна до: <b>{self._format_datetime(context.subscription.current_period_ends_at)}</b>"
            )

        lines.extend(
            [
                f'Ссылка на оплату: <a href="{escape(invoice.pay_url)}">Открыть счёт в Crypto Bot</a>',
                "",
                "После оплаты нажми «Проверить оплату». Если оплата уже прошла, доступ обновится сразу.",
            ]
        )
        return "\n".join(lines)

    def _build_invoice_description(self, quote: SubscriptionQuote) -> str:
        """Build invoice description visible in Crypto Bot."""

        return "GiftAnalystMarkets: ежемесячная подписка"

    @staticmethod
    def _build_invoice_payload(user_id: int, quote: SubscriptionQuote) -> str:
        """Build a compact JSON payload for the provider invoice."""

        return json.dumps(
            {
                "user_id": user_id,
                "plan_type": quote.plan_type.value,
                "amount": format(quote.amount, "f"),
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )

    def _format_subscription_status(self, subscription: UserSubscription) -> str:
        """Convert internal subscription status into UI text."""

        if self._is_subscription_active(subscription):
            return "Активна"

        mapping = {
            SubscriptionStatus.INACTIVE: "Не активирована",
            SubscriptionStatus.EXPIRED: "Истекла",
            SubscriptionStatus.ACTIVE: "Активна",
        }
        return mapping.get(subscription.status, subscription.status.value)

    @staticmethod
    def _format_invoice_status(status: PaymentInvoiceStatus) -> str:
        """Convert invoice status into UI text."""

        mapping = {
            PaymentInvoiceStatus.ACTIVE: "Ожидает оплату",
            PaymentInvoiceStatus.PAID: "Оплачен",
            PaymentInvoiceStatus.EXPIRED: "Истёк",
        }
        return mapping.get(status, status.value)

    @staticmethod
    def _format_amount(amount: Decimal, asset: Currency) -> str:
        """Format a TON-denominated subscription amount."""

        return f"{format(amount.normalize(), 'f')} {asset.value}"

    def _format_datetime(self, value: datetime | None) -> str:
        """Format UTC timestamp for user-facing messages."""

        if value is None:
            return "—"
        normalized = self._ensure_utc(value)
        return normalized.strftime("%d.%m.%Y %H:%M UTC")

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        """Normalize datetimes to timezone-aware UTC."""

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _now() -> datetime:
        """Return the current UTC timestamp."""

        return datetime.now(timezone.utc)

