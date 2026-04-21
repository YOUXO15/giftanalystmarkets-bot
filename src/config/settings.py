from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.enums import Currency


class Settings(BaseSettings):
    """Centralized application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GiftAnalystMarkets"
    app_env: str = Field("development", validation_alias="APP_ENV")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    bot_username: str = Field("", validation_alias="BOT_USERNAME")
    bot_token: SecretStr = Field(..., validation_alias="BOT_TOKEN")
    start_notify_telegram_id: int | None = Field(1200208898, validation_alias="START_NOTIFY_TELEGRAM_ID")
    bot_polling_timeout: int = Field(30, validation_alias="BOT_POLLING_TIMEOUT")
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    database_echo: bool = Field(False, validation_alias="DATABASE_ECHO")
    gift_analyst_markets_base_url: str = Field(
        "",
        validation_alias=AliasChoices("GIFT_ANALYST_MARKETS_BASE_URL", "GIFTSATELLITE_BASE_URL"),
    )
    gift_analyst_markets_api_key: SecretStr | None = Field(
        None,
        validation_alias=AliasChoices("GIFT_ANALYST_MARKETS_API_KEY", "GIFTSATELLITE_API_KEY"),
    )
    gift_analyst_markets_use_mock_data: bool = Field(
        False,
        validation_alias=AliasChoices("GIFT_ANALYST_MARKETS_USE_MOCK_DATA", "GIFTSATELLITE_USE_MOCK_DATA"),
    )
    gift_analyst_markets_mock_deals_count: int = Field(
        5,
        validation_alias=AliasChoices("GIFT_ANALYST_MARKETS_MOCK_DEALS_COUNT", "GIFTSATELLITE_MOCK_DEALS_COUNT"),
    )
    ton_api_base_url: str = Field("https://tonapi.io", validation_alias="TON_API_BASE_URL")
    ton_api_key: SecretStr | None = Field(None, validation_alias="TON_API_KEY")
    crypto_pay_base_url: str = Field("https://pay.crypt.bot", validation_alias="CRYPTO_PAY_BASE_URL")
    crypto_pay_api_token: SecretStr | None = Field(None, validation_alias="CRYPTO_PAY_API_TOKEN")
    crypto_pay_asset: Currency = Field(Currency.TON, validation_alias="CRYPTO_PAY_ASSET")
    crypto_pay_invoice_expires_in: int = Field(3600, validation_alias="CRYPTO_PAY_INVOICE_EXPIRES_IN")
    free_access_mode: bool = Field(False, validation_alias="FREE_ACCESS_MODE")
    subscription_intro_price_ton: Decimal = Field(
        Decimal("3"),
        validation_alias="SUBSCRIPTION_INTRO_PRICE_TON",
    )
    subscription_monthly_price_ton: Decimal = Field(
        Decimal("3"),
        validation_alias="SUBSCRIPTION_MONTHLY_PRICE_TON",
    )
    subscription_period_days: int = Field(30, validation_alias="SUBSCRIPTION_PERIOD_DAYS")
    referral_base_percent: Decimal = Field(Decimal("10"), validation_alias="REFERRAL_BASE_PERCENT")
    referral_percent_after_level_1: Decimal = Field(
        Decimal("5"),
        validation_alias="REFERRAL_PERCENT_AFTER_LEVEL_1",
    )
    referral_percent_after_level_2: Decimal = Field(
        Decimal("13"),
        validation_alias="REFERRAL_PERCENT_AFTER_LEVEL_2",
    )
    referral_percent_after_level_3: Decimal = Field(
        Decimal("15"),
        validation_alias="REFERRAL_PERCENT_AFTER_LEVEL_3",
    )
    referral_level_1_threshold: int = Field(3, validation_alias="REFERRAL_LEVEL_1_THRESHOLD")
    referral_level_2_threshold: int = Field(10, validation_alias="REFERRAL_LEVEL_2_THRESHOLD")
    referral_level_3_threshold: int = Field(25, validation_alias="REFERRAL_LEVEL_3_THRESHOLD")
    referral_withdraw_min_ton: Decimal = Field(Decimal("1"), validation_alias="REFERRAL_WITHDRAW_MIN_TON")
    daily_export_limit: int = Field(25, validation_alias="DAILY_EXPORT_LIMIT")
    business_timezone: str = Field("Europe/Moscow", validation_alias="BUSINESS_TIMEZONE")
    http_timeout_seconds: float = Field(15.0, validation_alias="HTTP_TIMEOUT_SECONDS")

    @computed_field  # type: ignore[misc]
    @property
    def sqlalchemy_async_database_url(self) -> str:
        """Return a SQLAlchemy-compatible async database URL."""

        normalized = self.database_url.strip()
        if normalized.startswith("postgres://"):
            normalized = normalized.replace("postgres://", "postgresql+asyncpg://", 1)
        elif normalized.startswith("postgresql://"):
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
        return normalized

    @property
    def bot_token_value(self) -> str:
        """Expose the plain Telegram bot token."""

        return self.bot_token.get_secret_value()

    @property
    def gift_analyst_markets_api_key_value(self) -> str | None:
        """Expose the plain external market API key."""

        return (
            self.gift_analyst_markets_api_key.get_secret_value()
            if self.gift_analyst_markets_api_key
            else None
        )

    @property
    def ton_api_key_value(self) -> str | None:
        """Expose the plain TON API key."""

        return self.ton_api_key.get_secret_value() if self.ton_api_key else None

    @property
    def crypto_pay_api_token_value(self) -> str | None:
        """Expose the plain Crypto Pay API token."""

        return self.crypto_pay_api_token.get_secret_value() if self.crypto_pay_api_token else None

    @property
    def is_gift_analyst_markets_configured(self) -> bool:
        """Check whether external market sync is configured or mock mode is enabled."""

        return self.gift_analyst_markets_use_mock_data or bool(
            self.gift_analyst_markets_base_url and self.gift_analyst_markets_api_key_value
        )

    @property
    def is_ton_configured(self) -> bool:
        """Check whether TON API endpoint is configured."""

        return bool(self.ton_api_base_url)

    @property
    def is_crypto_pay_configured(self) -> bool:
        """Check whether Crypto Pay API is configured."""

        return bool(self.crypto_pay_base_url and self.crypto_pay_api_token_value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
