"""Small shared helpers and bot constants."""

from __future__ import annotations

from html import escape

from aiogram.types import BotCommand

from src.utils.enums import Language
from src.utils.i18n import button_text, button_variants, t


BUTTON_ADD_PURCHASE = button_text("add_purchase", Language.RU)
BUTTON_ADD_SALE = button_text("add_sale", Language.RU)
BUTTON_SYNC = BUTTON_ADD_PURCHASE
BUTTON_DEALS = button_text("deals", Language.RU)
BUTTON_STATS = button_text("stats", Language.RU)
BUTTON_TON = button_text("ton", Language.RU)
BUTTON_EXPORT = button_text("export", Language.RU)
BUTTON_EXPORT_CSV = "Экспорт CSV"
BUTTON_EXPORT_XLSX = "Экспорт XLSX"
BUTTON_EXPORT_CUSTOM = "Конструктор CSV/XLSX"
BUTTON_SUBSCRIPTION = button_text("subscription", Language.RU)
BUTTON_SUBSCRIPTION_CREATE = button_text("subscription_create", Language.RU)
BUTTON_SUBSCRIPTION_CHECK = button_text("subscription_check", Language.RU)
BUTTON_SUBSCRIPTION_BALANCE_PAY = button_text("subscription_balance_pay", Language.RU)
BUTTON_BALANCE = button_text("balance", Language.RU)
BUTTON_REFERRALS = button_text("referrals", Language.RU)
BUTTON_GIFT_SUBSCRIPTION = button_text("gift_subscription", Language.RU)
BUTTON_WITHDRAW = button_text("withdraw", Language.RU)
BUTTON_SETTINGS = button_text("settings", Language.RU)
BUTTON_NOTIFICATIONS = button_text("notifications", Language.RU)
BUTTON_AUTOSYNC = button_text("autosync", Language.RU)
BUTTON_LANGUAGE = button_text("language", Language.RU)
BUTTON_BACK = button_text("back", Language.RU)
BUTTON_BACK_TO_MENU = button_text("back_to_menu", Language.RU)
BUTTON_CANCEL = button_text("cancel", Language.RU)
BUTTON_LANG_RU = button_text("language_ru", Language.RU)
BUTTON_LANG_EN = button_text("language_en", Language.RU)
BUTTON_LANG_ZH = button_text("language_zh", Language.RU)

BUTTON_RATE_TODAY = "Сегодня"
BUTTON_RATE_DATE = "Выбрать дату"
BUTTON_RATE_SKIP = "Пропустить"
BUTTON_SALE_FEE_SKIP = "Без комиссии"

BUTTON_EXPORT_PARAM_FORMAT = "Формат файла"
BUTTON_EXPORT_PARAM_STATUS = "Статус сделок"
BUTTON_EXPORT_PARAM_CURRENCY = "Валюта отчета"
BUTTON_EXPORT_PARAM_PROFIT = "Фильтр прибыли"
BUTTON_EXPORT_PARAM_DAYS = "Период"
BUTTON_EXPORT_PARAM_LIMIT = "Лимит строк"
BUTTON_EXPORT_PARAM_FIELDS = "Набор колонок"
BUTTON_EXPORT_PARAM_APPLY = "Сформировать файл"
BUTTON_EXPORT_PARAM_RESET = "Сбросить параметры"
BUTTON_EXPORT_BACK_TO_PARAMS = "Назад к параметрам"
BUTTON_EXPORT_BACK_TO_EXPORT = "Назад к экспорту"

BUTTON_EXPORT_OPTION_FORMAT_CSV = "CSV"
BUTTON_EXPORT_OPTION_FORMAT_XLSX = "XLSX"

BUTTON_EXPORT_OPTION_STATUS_ALL = "Все статусы"
BUTTON_EXPORT_OPTION_STATUS_OPEN = "Только открытые"
BUTTON_EXPORT_OPTION_STATUS_CLOSED = "Только закрытые"
BUTTON_EXPORT_OPTION_STATUS_CANCELLED = "Только отмененные"

BUTTON_EXPORT_OPTION_CURRENCY_ALL = "Исходная валюта"
BUTTON_EXPORT_OPTION_CURRENCY_USD = "USD"
BUTTON_EXPORT_OPTION_CURRENCY_EUR = "EUR"
BUTTON_EXPORT_OPTION_CURRENCY_RUB = "RUB"
BUTTON_EXPORT_OPTION_CURRENCY_TON = "TON"
BUTTON_EXPORT_OPTION_CURRENCY_USDT = "USDT"

BUTTON_EXPORT_OPTION_PROFIT_ANY = "Любая прибыль"
BUTTON_EXPORT_OPTION_PROFIT_POSITIVE = "Только прибыльные"
BUTTON_EXPORT_OPTION_PROFIT_NEGATIVE = "Только убыточные"
BUTTON_EXPORT_OPTION_PROFIT_ZERO = "Только нулевые"
BUTTON_EXPORT_OPTION_PROFIT_NON_NEGATIVE = "Не ниже 0"
BUTTON_EXPORT_OPTION_PROFIT_NON_POSITIVE = "Не выше 0"

BUTTON_EXPORT_OPTION_DAYS_ALL = "За все время"
BUTTON_EXPORT_OPTION_DAYS_7 = "Последние 7 дней"
BUTTON_EXPORT_OPTION_DAYS_30 = "Последние 30 дней"
BUTTON_EXPORT_OPTION_DAYS_90 = "Последние 90 дней"
BUTTON_EXPORT_OPTION_DAYS_365 = "Последние 365 дней"

BUTTON_EXPORT_OPTION_LIMIT_NONE = "Без лимита"
BUTTON_EXPORT_OPTION_LIMIT_20 = "20 строк"
BUTTON_EXPORT_OPTION_LIMIT_50 = "50 строк"
BUTTON_EXPORT_OPTION_LIMIT_100 = "100 строк"
BUTTON_EXPORT_OPTION_LIMIT_200 = "200 строк"
BUTTON_EXPORT_OPTION_LIMIT_500 = "500 строк"

BUTTON_EXPORT_OPTION_FIELDS_ALL = "Все колонки"
BUTTON_EXPORT_OPTION_FIELDS_COMPACT = "Короткий отчет"
BUTTON_EXPORT_OPTION_FIELDS_FINANCE = "Финансовый отчет"
BUTTON_EXPORT_OPTION_FIELDS_TIMELINE = "Хронология"

BUTTON_MARKETPLACE_PORTALS = "PORTALS"
BUTTON_MARKETPLACE_FRAGMENT = "FRAGMENT"
BUTTON_MARKETPLACE_GETGEMS = "GETGEMS"
BUTTON_MARKETPLACE_MRKT = "MRKT"
BUTTON_MARKETPLACE_MARKET = "MARKET"
BUTTON_MARKETPLACE_TELEGRAM = "TELEGRAM"


def get_main_menu_buttons(language: Language | str | None = None) -> list[list[str]]:
    """Return button labels for the main reply keyboard."""

    return [
        [button_text("add_purchase", language)],
        [button_text("add_sale", language)],
        [button_text("deals", language), button_text("stats", language)],
        [button_text("ton", language), button_text("export", language)],
        [button_text("subscription", language)],
        [button_text("balance", language), button_text("referrals", language)],
        [button_text("gift_subscription", language), button_text("withdraw", language)],
        [button_text("settings", language)],
    ]


def get_settings_menu_buttons(language: Language | str | None = None) -> list[list[str]]:
    """Return button labels for the settings reply keyboard."""

    return [
        [button_text("language", language)],
        [button_text("back", language)],
    ]


def get_export_menu_buttons() -> list[list[str]]:
    """Return button labels for the export entry keyboard."""

    return [
        [BUTTON_EXPORT_CSV, BUTTON_EXPORT_XLSX],
        [BUTTON_EXPORT_CUSTOM],
        [BUTTON_BACK_TO_MENU],
    ]


def get_export_builder_buttons() -> list[list[str]]:
    """Return button labels for the export parameter constructor root."""

    return [
        [BUTTON_EXPORT_PARAM_FORMAT],
        [BUTTON_EXPORT_PARAM_STATUS, BUTTON_EXPORT_PARAM_CURRENCY],
        [BUTTON_EXPORT_PARAM_PROFIT, BUTTON_EXPORT_PARAM_DAYS],
        [BUTTON_EXPORT_PARAM_LIMIT, BUTTON_EXPORT_PARAM_FIELDS],
        [BUTTON_EXPORT_PARAM_APPLY, BUTTON_EXPORT_PARAM_RESET],
        [BUTTON_EXPORT_BACK_TO_EXPORT, BUTTON_BACK_TO_MENU],
    ]


def get_export_format_buttons() -> list[list[str]]:
    """Return format option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_FORMAT_CSV, BUTTON_EXPORT_OPTION_FORMAT_XLSX],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_export_status_buttons() -> list[list[str]]:
    """Return status option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_STATUS_ALL],
        [BUTTON_EXPORT_OPTION_STATUS_OPEN, BUTTON_EXPORT_OPTION_STATUS_CLOSED],
        [BUTTON_EXPORT_OPTION_STATUS_CANCELLED],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_export_currency_buttons() -> list[list[str]]:
    """Return currency option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_CURRENCY_ALL],
        [BUTTON_EXPORT_OPTION_CURRENCY_USD, BUTTON_EXPORT_OPTION_CURRENCY_EUR, BUTTON_EXPORT_OPTION_CURRENCY_RUB],
        [BUTTON_EXPORT_OPTION_CURRENCY_TON, BUTTON_EXPORT_OPTION_CURRENCY_USDT],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_export_profit_buttons() -> list[list[str]]:
    """Return profit filter option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_PROFIT_ANY],
        [BUTTON_EXPORT_OPTION_PROFIT_POSITIVE, BUTTON_EXPORT_OPTION_PROFIT_NEGATIVE],
        [BUTTON_EXPORT_OPTION_PROFIT_ZERO],
        [BUTTON_EXPORT_OPTION_PROFIT_NON_NEGATIVE, BUTTON_EXPORT_OPTION_PROFIT_NON_POSITIVE],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_export_days_buttons() -> list[list[str]]:
    """Return period option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_DAYS_ALL],
        [BUTTON_EXPORT_OPTION_DAYS_7, BUTTON_EXPORT_OPTION_DAYS_30],
        [BUTTON_EXPORT_OPTION_DAYS_90, BUTTON_EXPORT_OPTION_DAYS_365],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_export_limit_buttons() -> list[list[str]]:
    """Return row limit option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_LIMIT_NONE],
        [BUTTON_EXPORT_OPTION_LIMIT_20, BUTTON_EXPORT_OPTION_LIMIT_50, BUTTON_EXPORT_OPTION_LIMIT_100],
        [BUTTON_EXPORT_OPTION_LIMIT_200, BUTTON_EXPORT_OPTION_LIMIT_500],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_export_fields_buttons() -> list[list[str]]:
    """Return field preset option buttons."""

    return [
        [BUTTON_EXPORT_OPTION_FIELDS_ALL],
        [BUTTON_EXPORT_OPTION_FIELDS_COMPACT, BUTTON_EXPORT_OPTION_FIELDS_FINANCE],
        [BUTTON_EXPORT_OPTION_FIELDS_TIMELINE],
        [BUTTON_EXPORT_BACK_TO_PARAMS, BUTTON_BACK_TO_MENU],
    ]


def get_subscription_menu_buttons(language: Language | str | None = None) -> list[list[str]]:
    """Return buttons for the billing and subscription screen."""

    return [
        [button_text("subscription_create", language), button_text("subscription_check", language)],
        [button_text("subscription_balance_pay", language)],
        [button_text("back_to_menu", language)],
    ]


def get_purchase_flow_buttons() -> list[list[str]]:
    """Return buttons for purchase capture flow."""

    return [[BUTTON_CANCEL, BUTTON_BACK_TO_MENU]]


def get_sale_flow_buttons() -> list[list[str]]:
    """Return buttons for sale capture flow."""

    return [[BUTTON_CANCEL, BUTTON_BACK_TO_MENU]]


def get_ton_rate_choice_buttons() -> list[list[str]]:
    """Return buttons for TON/USD rate selection during purchase intake."""

    return [
        [BUTTON_RATE_TODAY, BUTTON_RATE_DATE],
        [BUTTON_RATE_SKIP],
        [BUTTON_CANCEL, BUTTON_BACK_TO_MENU],
    ]


def get_sale_fee_buttons() -> list[list[str]]:
    """Return buttons for the sale commission step."""

    return [
        [BUTTON_SALE_FEE_SKIP],
        [BUTTON_CANCEL, BUTTON_BACK_TO_MENU],
    ]


def get_marketplace_choice_buttons() -> list[list[str]]:
    """Return buttons for manual marketplace selection."""

    return [
        [BUTTON_MARKETPLACE_PORTALS, BUTTON_MARKETPLACE_FRAGMENT],
        [BUTTON_MARKETPLACE_GETGEMS, BUTTON_MARKETPLACE_MRKT],
        [BUTTON_MARKETPLACE_MARKET, BUTTON_MARKETPLACE_TELEGRAM],
        [BUTTON_CANCEL, BUTTON_BACK_TO_MENU],
    ]


def get_language_menu_buttons() -> list[list[str]]:
    """Return buttons for language selection."""

    return [
        [BUTTON_LANG_RU, BUTTON_LANG_EN, BUTTON_LANG_ZH],
        [BUTTON_BACK],
    ]


def get_main_menu_button_variants() -> set[str]:
    """Return all language variants for top-level main menu buttons."""

    semantic_keys = (
        "add_purchase",
        "add_sale",
        "deals",
        "stats",
        "ton",
        "export",
        "subscription",
        "balance",
        "referrals",
        "gift_subscription",
        "withdraw",
        "settings",
        "notifications",
        "autosync",
        "language",
        "subscription_create",
        "subscription_check",
        "subscription_balance_pay",
        "back",
        "back_to_menu",
        "cancel",
    )
    variants: set[str] = set()
    for key in semantic_keys:
        variants.update(button_variants(key))
    return variants


def get_known_button_texts() -> set[str]:
    """Return a flat set of all known reply button labels."""

    groups = [
        get_main_menu_buttons(),
        get_settings_menu_buttons(),
        get_language_menu_buttons(),
        get_export_menu_buttons(),
        get_export_builder_buttons(),
        get_export_format_buttons(),
        get_export_status_buttons(),
        get_export_currency_buttons(),
        get_export_profit_buttons(),
        get_export_days_buttons(),
        get_export_limit_buttons(),
        get_export_fields_buttons(),
        get_subscription_menu_buttons(),
        get_purchase_flow_buttons(),
        get_sale_flow_buttons(),
        get_ton_rate_choice_buttons(),
        get_sale_fee_buttons(),
        get_marketplace_choice_buttons(),
    ]
    known = {button for group in groups for row in group for button in row}
    known.update(get_main_menu_button_variants())
    return known


def get_bot_commands() -> list[BotCommand]:
    """Return Telegram command definitions."""

    return [
        BotCommand(command="start", description="Регистрация и главное меню"),
        BotCommand(command="help", description="Справка по боту"),
        BotCommand(command="sync", description="Добавить купленный подарок"),
        BotCommand(command="sale", description="Добавить проданный подарок"),
        BotCommand(command="deals", description="Показать сделки"),
        BotCommand(command="stats", description="Показать статистику"),
        BotCommand(command="ton", description="Показать курс TON"),
        BotCommand(command="export", description="Экспорт CSV/XLSX"),
        BotCommand(command="pay", description="Подписка и оплата"),
        BotCommand(command="balance", description="Баланс и рефералы"),
        BotCommand(command="referrals", description="Реферальная ссылка"),
        BotCommand(command="gift", description="Подарить подписку"),
        BotCommand(command="withdraw", description="Вывод TON"),
        BotCommand(command="settings", description="Открыть настройки"),
    ]


def build_welcome_text(
    first_name: str | None,
    is_new_user: bool,
    *,
    language: Language | str | None = None,
    subscription_price_ton: str = "3",
) -> str:
    """Build localized welcome text for the /start command."""

    safe_name = escape(first_name or "friend")
    key = "welcome_new" if is_new_user else "welcome_returning"
    return t(key, language, first_name=safe_name, price_ton=subscription_price_ton)


def build_help_text(*, language: Language | str | None = None) -> str:
    """Build localized help text for the /help command."""

    return t("help_text", language)


def build_registration_required_text(*, language: Language | str | None = None) -> str:
    """Return a localized message for users not yet registered in the bot."""

    return t("registration_required", language)


def build_feature_stub_text(feature_name: str) -> str:
    """Return a standard placeholder text for a future feature."""

    return (
        f"<b>{feature_name}</b>\n\n"
        "Этот раздел уже зарезервирован в архитектуре, "
        "но полная бизнес-логика будет добавлена на следующем этапе."
    )
