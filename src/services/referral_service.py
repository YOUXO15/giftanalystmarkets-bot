"""Referral program workflows: links, rewards, balance, and withdrawals."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import Settings
from src.db.models.user_subscription import UserSubscription
from src.db.repositories.referral_profile_repo import ReferralProfileRepository
from src.db.repositories.referral_reward_repo import ReferralRewardRepository
from src.db.repositories.referral_transaction_repo import ReferralTransactionRepository
from src.db.repositories.subscription_repo import SubscriptionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.repositories.withdrawal_request_repo import WithdrawalRequestRepository
from src.utils.enums import ReferralTransactionType, SubscriptionStatus
from src.utils.helpers import build_registration_required_text


@dataclass(slots=True)
class ReferralActionResult:
    """Result of a user-triggered referral action."""

    success: bool
    message: str


class ReferralService:
    """Coordinates referral links, internal TON balance, and payouts."""

    _TON_QUANT = Decimal("0.00000001")

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._session_maker = session_maker
        self._settings = settings

    async def bind_referrer_from_deep_link(self, user_id: int, deep_link_payload: str | None) -> bool:
        """Bind referrer for a newly registered user from /start payload."""

        referral_code = self._extract_referral_code(deep_link_payload)
        if referral_code is None:
            return False

        async with self._session_maker() as session:
            profile_repo = ReferralProfileRepository(session)

            async with session.begin():
                user_profile = await self._ensure_profile(session, user_id)
                if user_profile.referrer_user_id is not None:
                    return False

                referrer_profile = await profile_repo.get_by_referral_code(referral_code)
                if referrer_profile is None:
                    return False
                if referrer_profile.user_id == user_id:
                    return False

                user_profile.referrer_user_id = referrer_profile.user_id
            return True

    async def build_referrals_overview(self, telegram_id: int) -> str:
        """Return referral dashboard with personal link and level progress."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            profile_repo = ReferralProfileRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return build_registration_required_text()

                profile = await self._ensure_profile(session, user.id)
                total_referrals = await profile_repo.count_total_referrals(user.id)
                paid_referrals = int(profile.paid_referrals_count)
                percent = self._calculate_referral_percent(paid_referrals)
                next_threshold = self._next_level_threshold(paid_referrals)

            link = self._build_referral_link(profile.referral_code)
            lines = [
                "<b>Реферальная программа</b>",
                "",
                f"Твоя ссылка: <code>{link}</code>",
                "",
                f"Всего приглашено: <b>{total_referrals}</b>",
                f"Оплативших подписку: <b>{paid_referrals}</b>",
                f"Текущий реф-процент: <b>{self._format_percent(percent)}%</b>",
            ]
            if next_threshold is None:
                lines.append("Максимальный уровень уже достигнут.")
            else:
                left = max(next_threshold - paid_referrals, 0)
                lines.append(f"До следующего уровня осталось: <b>{left}</b>")

            lines.extend(
                [
                    "",
                    "За каждого друга с оплаченной подпиской тебе начисляется TON на внутренний баланс.",
                    "Баланс можно использовать для своей подписки, подарка подписки или вывода.",
                ]
            )
            return "\n".join(lines)

    async def build_balance_overview(self, telegram_id: int) -> str:
        """Return current referral balance and recent transactions."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            profile_repo = ReferralProfileRepository(session)
            transaction_repo = ReferralTransactionRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return build_registration_required_text()

                profile = await self._ensure_profile(session, user.id)
                paid_referrals = int(profile.paid_referrals_count)
                percent = self._calculate_referral_percent(paid_referrals)
                recent_transactions = await transaction_repo.get_recent_for_user(user.id, limit=5)

            lines = [
                "<b>Внутренний баланс</b>",
                "",
                f"Доступно: <b>{self._format_ton(profile.available_balance_ton)} TON</b>",
                f"Всего заработано: <b>{self._format_ton(profile.total_earned_ton)} TON</b>",
                f"Текущий реф-процент: <b>{self._format_percent(percent)}%</b>",
                f"Минимальный вывод: <b>{self._format_ton(self._settings.referral_withdraw_min_ton)} TON</b>",
            ]

            if recent_transactions:
                lines.append("")
                lines.append("<b>Последние операции</b>")
                for transaction in recent_transactions:
                    sign = "+" if transaction.amount_ton >= Decimal("0") else ""
                    lines.append(
                        f"• {transaction.created_at.strftime('%d.%m %H:%M')} | "
                        f"{transaction.transaction_type.value}: "
                        f"{sign}{self._format_ton(transaction.amount_ton)} TON"
                    )

            return "\n".join(lines)

    async def pay_own_subscription_from_balance(self, telegram_id: int) -> ReferralActionResult:
        """Deduct balance and extend sender's own subscription period."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            profile_repo = ReferralProfileRepository(session)
            subscription_repo = SubscriptionRepository(session)
            transaction_repo = ReferralTransactionRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return ReferralActionResult(False, build_registration_required_text())

                profile = await self._ensure_profile(session, user.id)
                amount = self._quantize_ton(self._settings.subscription_monthly_price_ton)
                if profile.available_balance_ton < amount:
                    return ReferralActionResult(
                        False,
                        (
                            "<b>Недостаточно средств на балансе</b>\n\n"
                            f"Нужно: <b>{self._format_ton(amount)} TON</b>\n"
                            f"Сейчас: <b>{self._format_ton(profile.available_balance_ton)} TON</b>"
                        ),
                    )

                profile.available_balance_ton = self._quantize_ton(profile.available_balance_ton - amount)
                await transaction_repo.create_transaction(
                    user_id=user.id,
                    transaction_type=ReferralTransactionType.SUBSCRIPTION_PAYMENT,
                    amount_ton=-amount,
                    balance_after_ton=profile.available_balance_ton,
                    note="Оплата своей подписки внутренним балансом",
                )

                subscription = await subscription_repo.get_by_user_id(user.id)
                if subscription is None:
                    subscription = await subscription_repo.create_default(user.id)
                self._activate_subscription(subscription, paid_at=self._now())

            return ReferralActionResult(
                True,
                (
                    "<b>Подписка оплачена с баланса</b>\n\n"
                    f"Списано: <b>{self._format_ton(amount)} TON</b>\n"
                    f"Остаток: <b>{self._format_ton(profile.available_balance_ton)} TON</b>\n"
                    f"Доступ до: <b>{subscription.current_period_ends_at.strftime('%d.%m.%Y %H:%M UTC')}</b>"
                ),
            )

    async def gift_subscription_from_balance(
        self,
        sender_telegram_id: int,
        target_telegram_id: int,
    ) -> ReferralActionResult:
        """Pay another user's subscription from sender referral balance."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            profile_repo = ReferralProfileRepository(session)
            subscription_repo = SubscriptionRepository(session)
            transaction_repo = ReferralTransactionRepository(session)

            async with session.begin():
                sender = await user_repo.get_by_telegram_id(sender_telegram_id)
                if sender is None:
                    return ReferralActionResult(False, build_registration_required_text())
                target = await user_repo.get_by_telegram_id(target_telegram_id)
                if target is None:
                    return ReferralActionResult(
                        False,
                        "Друг пока не найден в базе. Пусть сначала нажмёт /start в боте.",
                    )
                if sender.id == target.id:
                    return ReferralActionResult(
                        False,
                        "Нельзя подарить подписку самому себе. Для себя используй «Оплатить с баланса».",
                    )

                sender_profile = await self._ensure_profile(session, sender.id)
                amount = self._quantize_ton(self._settings.subscription_monthly_price_ton)
                if sender_profile.available_balance_ton < amount:
                    return ReferralActionResult(
                        False,
                        (
                            "<b>Недостаточно средств для подарка</b>\n\n"
                            f"Нужно: <b>{self._format_ton(amount)} TON</b>\n"
                            f"Сейчас: <b>{self._format_ton(sender_profile.available_balance_ton)} TON</b>"
                        ),
                    )

                sender_profile.available_balance_ton = self._quantize_ton(sender_profile.available_balance_ton - amount)
                await transaction_repo.create_transaction(
                    user_id=sender.id,
                    transaction_type=ReferralTransactionType.GIFT_SUBSCRIPTION,
                    amount_ton=-amount,
                    balance_after_ton=sender_profile.available_balance_ton,
                    related_user_id=target.id,
                    note="Подарок подписки другому пользователю",
                )

                target_subscription = await subscription_repo.get_by_user_id(target.id)
                if target_subscription is None:
                    target_subscription = await subscription_repo.create_default(target.id)
                self._activate_subscription(target_subscription, paid_at=self._now())

            return ReferralActionResult(
                True,
                (
                    "<b>Подарочная подписка оформлена</b>\n\n"
                    f"Кому: <b>{target_telegram_id}</b>\n"
                    f"Списано: <b>{self._format_ton(amount)} TON</b>\n"
                    f"Твой остаток: <b>{self._format_ton(sender_profile.available_balance_ton)} TON</b>"
                ),
            )

    async def request_withdrawal(
        self,
        telegram_id: int,
        *,
        wallet_address: str,
        amount_ton: Decimal,
    ) -> ReferralActionResult:
        """Create withdrawal request and reserve TON from balance."""

        normalized_amount = self._quantize_ton(amount_ton)
        if normalized_amount <= Decimal("0"):
            return ReferralActionResult(False, "Сумма вывода должна быть больше нуля.")
        if normalized_amount < self._settings.referral_withdraw_min_ton:
            return ReferralActionResult(
                False,
                (
                    "Сумма меньше минимального вывода.\n"
                    f"Минимум: <b>{self._format_ton(self._settings.referral_withdraw_min_ton)} TON</b>."
                ),
            )

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            transaction_repo = ReferralTransactionRepository(session)
            withdrawal_repo = WithdrawalRequestRepository(session)

            async with session.begin():
                user = await user_repo.get_by_telegram_id(telegram_id)
                if user is None:
                    return ReferralActionResult(False, build_registration_required_text())

                profile = await self._ensure_profile(session, user.id)
                if profile.available_balance_ton < normalized_amount:
                    return ReferralActionResult(
                        False,
                        (
                            "<b>Недостаточно средств на балансе</b>\n\n"
                            f"Запрошено: <b>{self._format_ton(normalized_amount)} TON</b>\n"
                            f"Доступно: <b>{self._format_ton(profile.available_balance_ton)} TON</b>"
                        ),
                    )

                profile.available_balance_ton = self._quantize_ton(profile.available_balance_ton - normalized_amount)
                request = await withdrawal_repo.create_request(
                    user_id=user.id,
                    wallet_address=wallet_address,
                    amount_ton=normalized_amount,
                )
                await transaction_repo.create_transaction(
                    user_id=user.id,
                    transaction_type=ReferralTransactionType.WITHDRAWAL_REQUEST,
                    amount_ton=-normalized_amount,
                    balance_after_ton=profile.available_balance_ton,
                    note=f"Заявка на вывод #{request.id}",
                )

            return ReferralActionResult(
                True,
                (
                    "<b>Заявка на вывод создана</b>\n\n"
                    f"ID заявки: <b>{request.id}</b>\n"
                    f"Сумма: <b>{self._format_ton(normalized_amount)} TON</b>\n"
                    f"Кошелёк: <code>{wallet_address}</code>\n"
                    "Статус: <b>pending</b> (обработка вручную)."
                ),
            )

    async def apply_reward_for_paid_invoice(
        self,
        session: AsyncSession,
        *,
        paid_user_id: int,
        payment_invoice_id: int,
        invoice_amount_ton: Decimal,
    ) -> Decimal | None:
        """Credit inviter with referral reward for a newly paid invoice."""

        if invoice_amount_ton <= Decimal("0"):
            return None

        profile_repo = ReferralProfileRepository(session)
        reward_repo = ReferralRewardRepository(session)
        transaction_repo = ReferralTransactionRepository(session)

        existing_reward = await reward_repo.get_by_payment_invoice_id(payment_invoice_id)
        if existing_reward is not None:
            return None

        paid_user_profile = await self._ensure_profile(session, paid_user_id)
        referrer_user_id = paid_user_profile.referrer_user_id
        if referrer_user_id is None:
            return None

        referrer_profile = await self._ensure_profile(session, referrer_user_id)
        has_pair_reward = await reward_repo.has_reward_for_pair(referrer_user_id, paid_user_id)
        next_paid_referrals_count = referrer_profile.paid_referrals_count + (0 if has_pair_reward else 1)
        reward_percent = self._calculate_referral_percent(next_paid_referrals_count)
        if reward_percent <= Decimal("0"):
            return None

        reward_amount = self._quantize_ton(
            (invoice_amount_ton * reward_percent) / Decimal("100")
        )
        if reward_amount <= Decimal("0"):
            return None

        referrer_profile.available_balance_ton = self._quantize_ton(
            referrer_profile.available_balance_ton + reward_amount
        )
        referrer_profile.total_earned_ton = self._quantize_ton(
            referrer_profile.total_earned_ton + reward_amount
        )
        if not has_pair_reward:
            referrer_profile.paid_referrals_count = next_paid_referrals_count

        await reward_repo.create_reward(
            referrer_user_id=referrer_user_id,
            referred_user_id=paid_user_id,
            payment_invoice_id=payment_invoice_id,
            reward_percent=reward_percent,
            reward_amount_ton=reward_amount,
        )
        await transaction_repo.create_transaction(
            user_id=referrer_user_id,
            transaction_type=ReferralTransactionType.REWARD,
            amount_ton=reward_amount,
            balance_after_ton=referrer_profile.available_balance_ton,
            related_user_id=paid_user_id,
            payment_invoice_id=payment_invoice_id,
            note="Реферальное начисление за оплаченную подписку",
        )
        return reward_amount

    async def _ensure_profile(self, session: AsyncSession, user_id: int):
        """Load or create referral profile for user."""

        profile_repo = ReferralProfileRepository(session)
        profile = await profile_repo.get_by_user_id(user_id)
        if profile is not None:
            return profile

        referral_code = await self._generate_unique_code(session)
        return await profile_repo.create_profile(user_id=user_id, referral_code=referral_code)

    async def _generate_unique_code(self, session: AsyncSession) -> str:
        """Generate a unique human-friendly referral code."""

        profile_repo = ReferralProfileRepository(session)
        while True:
            candidate = f"gam{secrets.token_hex(4)}"
            exists = await profile_repo.get_by_referral_code(candidate)
            if exists is None:
                return candidate

    def _extract_referral_code(self, deep_link_payload: str | None) -> str | None:
        """Extract normalized referral code from /start payload."""

        if deep_link_payload is None:
            return None
        value = deep_link_payload.strip()
        if not value:
            return None
        match = re.fullmatch(r"ref_([A-Za-z0-9_-]{4,64})", value)
        if match:
            return match.group(1).lower()
        if re.fullmatch(r"[A-Za-z0-9_-]{4,64}", value):
            return value.lower()
        return None

    def _build_referral_link(self, referral_code: str) -> str:
        """Build user-facing referral deep link."""

        if self._settings.bot_username:
            return f"https://t.me/{self._settings.bot_username}?start=ref_{referral_code}"
        return f"/start ref_{referral_code}"

    def _calculate_referral_percent(self, paid_referrals_count: int) -> Decimal:
        """Calculate current referral percentage based on paid referrals."""

        percent = self._settings.referral_base_percent
        if paid_referrals_count >= self._settings.referral_level_3_threshold:
            percent = self._settings.referral_percent_after_level_3
        elif paid_referrals_count >= self._settings.referral_level_2_threshold:
            percent = self._settings.referral_percent_after_level_2
        elif paid_referrals_count >= self._settings.referral_level_1_threshold:
            percent = self._settings.referral_percent_after_level_1
        return Decimal(percent)

    def _next_level_threshold(self, paid_referrals_count: int) -> int | None:
        """Return next level threshold or None when max level reached."""

        levels = [
            self._settings.referral_level_1_threshold,
            self._settings.referral_level_2_threshold,
            self._settings.referral_level_3_threshold,
        ]
        for threshold in levels:
            if paid_referrals_count < threshold:
                return threshold
        return None

    def _activate_subscription(self, subscription: UserSubscription, *, paid_at: datetime) -> None:
        """Activate or extend subscription period in place."""

        paid_at_utc = self._ensure_utc(paid_at)
        period_start = paid_at_utc
        if subscription.current_period_ends_at is not None:
            current_end = self._ensure_utc(subscription.current_period_ends_at)
            if current_end > paid_at_utc:
                period_start = current_end
        subscription.current_period_started_at = period_start
        subscription.current_period_ends_at = period_start + timedelta(days=self._settings.subscription_period_days)
        subscription.last_paid_at = paid_at_utc
        if subscription.first_paid_at is None:
            subscription.first_paid_at = paid_at_utc
        subscription.discount_consumed = True
        subscription.status = SubscriptionStatus.ACTIVE

    @classmethod
    def _quantize_ton(cls, value: Decimal) -> Decimal:
        """Round TON value to 8 decimal places."""

        return value.quantize(cls._TON_QUANT, rounding=ROUND_HALF_UP)

    @classmethod
    def _format_ton(cls, value: Decimal) -> str:
        """Format TON amount for UI."""

        return format(cls._quantize_ton(value), "f")

    @staticmethod
    def _format_percent(value: Decimal) -> str:
        """Format percentage with up to 2 decimal digits."""

        normalized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        text = format(normalized, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        """Normalize datetime to timezone-aware UTC."""

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _now() -> datetime:
        """Return current UTC datetime."""

        return datetime.now(timezone.utc)
