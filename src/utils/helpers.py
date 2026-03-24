"""Small shared helpers and bot constants."""

from __future__ import annotations

from html import escape

from aiogram.types import BotCommand


BUTTON_SYNC = "Добавить подарок"
BUTTON_DEALS = "Сделки"
BUTTON_STATS = "Статистика"
BUTTON_TON = "Курс TON"
BUTTON_EXPORT = "Экспорт"
BUTTON_EXPORT_CSV = "Экспорт CSV"
BUTTON_EXPORT_XLSX = "Экспорт XLSX"
BUTTON_EXPORT_CUSTOM = "Конструктор CSV/XLSX"
BUTTON_SUBSCRIPTION = "Подписка"
BUTTON_SUBSCRIPTION_CREATE = "Оплатить подписку"
BUTTON_SUBSCRIPTION_CHECK = "Проверить оплату"
BUTTON_SETTINGS = "Настройки"
BUTTON_NOTIFICATIONS = "Уведомления"
BUTTON_AUTOSYNC = "Автосинхронизация"
BUTTON_BACK = "Назад"
BUTTON_BACK_TO_MENU = "В меню"
BUTTON_CANCEL = "Отмена"

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


def get_main_menu_buttons() -> list[list[str]]:
    """Return button labels for the main reply keyboard."""

    return [
        [BUTTON_SYNC],
        [BUTTON_DEALS, BUTTON_STATS],
        [BUTTON_TON, BUTTON_EXPORT],
        [BUTTON_SUBSCRIPTION],
    ]


def get_settings_menu_buttons() -> list[list[str]]:
    """Return button labels for the settings reply keyboard."""

    return [
        [BUTTON_NOTIFICATIONS, BUTTON_AUTOSYNC],
        [BUTTON_BACK],
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


def get_subscription_menu_buttons() -> list[list[str]]:
    """Return buttons for the billing and subscription screen."""

    return [
        [BUTTON_SUBSCRIPTION_CREATE, BUTTON_SUBSCRIPTION_CHECK],
        [BUTTON_BACK_TO_MENU],
    ]


def get_purchase_flow_buttons() -> list[list[str]]:
    """Return buttons for the manual purchase flow."""

    return [
        [BUTTON_CANCEL, BUTTON_BACK_TO_MENU],
    ]


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


def get_known_button_texts() -> set[str]:
    """Return a flat set of all known reply button labels."""

    groups = [
        get_main_menu_buttons(),
        get_settings_menu_buttons(),
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
        get_ton_rate_choice_buttons(),
        get_sale_fee_buttons(),
    ]
    return {button for group in groups for row in group for button in row}


def get_bot_commands() -> list[BotCommand]:
    """Return Telegram command definitions."""

    return [
        BotCommand(command="start", description="Регистрация и главное меню"),
        BotCommand(command="help", description="Справка по боту"),
        BotCommand(command="sync", description="Добавить подарок"),
        BotCommand(command="deals", description="Показать сделки"),
        BotCommand(command="stats", description="Показать статистику"),
        BotCommand(command="ton", description="Показать курс TON"),
        BotCommand(command="export", description="Экспорт CSV/XLSX"),
        BotCommand(command="pay", description="Подписка и оплата"),
        BotCommand(command="settings", description="Открыть настройки"),
    ]


def build_welcome_text(first_name: str | None, is_new_user: bool) -> str:
    """Build welcome text for the /start command."""

    safe_name = escape(first_name or "друг")
    title = "Регистрация завершена" if is_new_user else "С возвращением"
    return (
        f"<b>{title}, {safe_name}!</b>\n\n"
        "Я помогаю вести учет Telegram-подарков: сохраняю покупки по ссылке, "
        "пытаюсь автоматически фиксировать продажи по уведомлениям маркетплейсов, "
        "считаю статистику и готовлю CSV/XLSX-экспорт.\n\n"
        "Как начать:\n"
        "1. Оплати подписку через кнопку <b>Подписка</b> или команду /pay.\n"
        "2. Нажми <b>Добавить подарок</b> и отправь ссылку на подарок.\n"
        "3. Введи цену покупки и при необходимости сохрани курс TON/USD.\n"
        "4. Когда подарок продастся, просто перешли сюда уведомление о продаже.\n\n"
        "Подписка работает так: <b>0.1 TON</b> за первый месяц, затем <b>3 TON</b> каждые 30 дней."
    )


def build_help_text() -> str:
    """Build help text for the /help command."""

    return (
        "<b>Что умеет бот</b>\n"
        "/start - регистрация и открытие главного меню\n"
        "/help - показать эту справку\n"
        "/sync - добавить подарок вручную\n"
        "/deals - последние сделки из локальной БД\n"
        "/stats - краткая статистика по сделкам\n"
        "/ton - курс TON\n"
        "/export - экспорт в CSV/XLSX с конструктором параметров\n"
        "/pay - подписка и создание счета на оплату\n"
        "/settings - пользовательские настройки\n\n"
        "<b>Новый поток учета</b>\n"
        "Добавить подарок: отправляешь ссылку на подарок, потом цену покупки.\n"
        "Продажа: пересылаешь текстовое уведомление маркетплейса, бот пытается найти открытую сделку и закрыть её.\n\n"
        "<b>Подписка</b>\n"
        "Пробного периода нет. Первый месяц стоит <b>0.1 TON</b>, затем действует базовый тариф "
        "<b>3 TON</b> за 30 дней доступа."
    )


def build_registration_required_text() -> str:
    """Return a standard message for users not yet registered in the bot."""

    return "Похоже, ты еще не зарегистрирован. Сначала запусти /start."


def build_feature_stub_text(feature_name: str) -> str:
    """Return a standard placeholder text for a future feature."""

    return (
        f"<b>{feature_name}</b>\n\n"
        "Этот раздел уже зарезервирован в архитектуре, но полная бизнес-логика "
        "будет добавлена на следующем этапе."
    )
