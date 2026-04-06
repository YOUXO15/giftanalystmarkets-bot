"""Handlers for local export commands."""

from __future__ import annotations

from dataclasses import dataclass, field

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.keyboards.export_menu import (
    get_export_builder_keyboard,
    get_export_currency_keyboard,
    get_export_days_keyboard,
    get_export_fields_keyboard,
    get_export_format_keyboard,
    get_export_limit_keyboard,
    get_export_menu_keyboard,
    get_export_profit_keyboard,
    get_export_status_keyboard,
)
from src.bot.keyboards.main_menu import get_main_menu_keyboard
from src.bot.message_cleanup import replace_tracked_document, replace_tracked_text
from src.bot.subscription_guard import ensure_paid_access
from src.config.settings import Settings
from src.services.export_service import ExportFileResult, ExportQuery, ExportService
from src.services.user_service import UserService
from src.utils.enums import Language
from src.utils.enums import ExportFormat
from src.utils.helpers import (
    BUTTON_BACK_TO_MENU,
    BUTTON_EXPORT_BACK_TO_EXPORT,
    BUTTON_EXPORT_BACK_TO_PARAMS,
    BUTTON_EXPORT_CSV,
    BUTTON_EXPORT_CUSTOM,
    BUTTON_EXPORT_OPTION_CURRENCY_ALL,
    BUTTON_EXPORT_OPTION_CURRENCY_EUR,
    BUTTON_EXPORT_OPTION_CURRENCY_RUB,
    BUTTON_EXPORT_OPTION_CURRENCY_TON,
    BUTTON_EXPORT_OPTION_CURRENCY_USD,
    BUTTON_EXPORT_OPTION_CURRENCY_USDT,
    BUTTON_EXPORT_OPTION_DAYS_30,
    BUTTON_EXPORT_OPTION_DAYS_365,
    BUTTON_EXPORT_OPTION_DAYS_7,
    BUTTON_EXPORT_OPTION_DAYS_90,
    BUTTON_EXPORT_OPTION_DAYS_ALL,
    BUTTON_EXPORT_OPTION_FIELDS_ALL,
    BUTTON_EXPORT_OPTION_FIELDS_COMPACT,
    BUTTON_EXPORT_OPTION_FIELDS_FINANCE,
    BUTTON_EXPORT_OPTION_FIELDS_TIMELINE,
    BUTTON_EXPORT_OPTION_FORMAT_CSV,
    BUTTON_EXPORT_OPTION_FORMAT_XLSX,
    BUTTON_EXPORT_OPTION_LIMIT_100,
    BUTTON_EXPORT_OPTION_LIMIT_20,
    BUTTON_EXPORT_OPTION_LIMIT_200,
    BUTTON_EXPORT_OPTION_LIMIT_50,
    BUTTON_EXPORT_OPTION_LIMIT_500,
    BUTTON_EXPORT_OPTION_LIMIT_NONE,
    BUTTON_EXPORT_OPTION_PROFIT_ANY,
    BUTTON_EXPORT_OPTION_PROFIT_NEGATIVE,
    BUTTON_EXPORT_OPTION_PROFIT_NON_NEGATIVE,
    BUTTON_EXPORT_OPTION_PROFIT_NON_POSITIVE,
    BUTTON_EXPORT_OPTION_PROFIT_POSITIVE,
    BUTTON_EXPORT_OPTION_PROFIT_ZERO,
    BUTTON_EXPORT_OPTION_STATUS_ALL,
    BUTTON_EXPORT_OPTION_STATUS_CANCELLED,
    BUTTON_EXPORT_OPTION_STATUS_CLOSED,
    BUTTON_EXPORT_OPTION_STATUS_OPEN,
    BUTTON_EXPORT_PARAM_APPLY,
    BUTTON_EXPORT_PARAM_CURRENCY,
    BUTTON_EXPORT_PARAM_DAYS,
    BUTTON_EXPORT_PARAM_FIELDS,
    BUTTON_EXPORT_PARAM_FORMAT,
    BUTTON_EXPORT_PARAM_LIMIT,
    BUTTON_EXPORT_PARAM_PROFIT,
    BUTTON_EXPORT_PARAM_RESET,
    BUTTON_EXPORT_PARAM_STATUS,
    BUTTON_EXPORT_XLSX,
)
from src.utils.i18n import button_variants, t

router = Router(name="export")

_FORMAT_OPTIONS = {BUTTON_EXPORT_OPTION_FORMAT_CSV, BUTTON_EXPORT_OPTION_FORMAT_XLSX}
_STATUS_OPTIONS = {
    BUTTON_EXPORT_OPTION_STATUS_ALL,
    BUTTON_EXPORT_OPTION_STATUS_OPEN,
    BUTTON_EXPORT_OPTION_STATUS_CLOSED,
    BUTTON_EXPORT_OPTION_STATUS_CANCELLED,
}
_CURRENCY_OPTIONS = {
    BUTTON_EXPORT_OPTION_CURRENCY_ALL,
    BUTTON_EXPORT_OPTION_CURRENCY_USD,
    BUTTON_EXPORT_OPTION_CURRENCY_EUR,
    BUTTON_EXPORT_OPTION_CURRENCY_RUB,
    BUTTON_EXPORT_OPTION_CURRENCY_TON,
    BUTTON_EXPORT_OPTION_CURRENCY_USDT,
}
_PROFIT_OPTIONS = {
    BUTTON_EXPORT_OPTION_PROFIT_ANY,
    BUTTON_EXPORT_OPTION_PROFIT_POSITIVE,
    BUTTON_EXPORT_OPTION_PROFIT_NEGATIVE,
    BUTTON_EXPORT_OPTION_PROFIT_ZERO,
    BUTTON_EXPORT_OPTION_PROFIT_NON_NEGATIVE,
    BUTTON_EXPORT_OPTION_PROFIT_NON_POSITIVE,
}
_DAYS_OPTIONS = {
    BUTTON_EXPORT_OPTION_DAYS_ALL,
    BUTTON_EXPORT_OPTION_DAYS_7,
    BUTTON_EXPORT_OPTION_DAYS_30,
    BUTTON_EXPORT_OPTION_DAYS_90,
    BUTTON_EXPORT_OPTION_DAYS_365,
}
_LIMIT_OPTIONS = {
    BUTTON_EXPORT_OPTION_LIMIT_NONE,
    BUTTON_EXPORT_OPTION_LIMIT_20,
    BUTTON_EXPORT_OPTION_LIMIT_50,
    BUTTON_EXPORT_OPTION_LIMIT_100,
    BUTTON_EXPORT_OPTION_LIMIT_200,
    BUTTON_EXPORT_OPTION_LIMIT_500,
}
_FIELDS_OPTIONS = {
    BUTTON_EXPORT_OPTION_FIELDS_ALL,
    BUTTON_EXPORT_OPTION_FIELDS_COMPACT,
    BUTTON_EXPORT_OPTION_FIELDS_FINANCE,
    BUTTON_EXPORT_OPTION_FIELDS_TIMELINE,
}

_FIELD_PRESET_COMPACT = [
    "id",
    "item",
    "gift_number",
    "market",
    "sale_market",
    "buy",
    "sell",
    "profit",
    "margin",
    "currency",
    "status",
]
_FIELD_PRESET_FINANCE = [
    "id",
    "item",
    "gift_number",
    "market",
    "sale_market",
    "buy",
    "sell",
    "fee",
    "profit",
    "margin",
    "currency",
    "ton_rate",
    "status",
]
_FIELD_PRESET_TIMELINE = [
    "id",
    "item",
    "gift_number",
    "market",
    "sale_market",
    "status",
    "opened_at",
    "closed_at",
    "created_at",
    "updated_at",
]


@dataclass(slots=True)
class ExportBuilderState:
    """Current export builder selection for a user."""

    export_format: ExportFormat = ExportFormat.CSV
    query: ExportQuery = field(default_factory=ExportQuery)


_EXPORT_BUILDER_STATE_BY_USER: dict[int, ExportBuilderState] = {}


@router.message(Command("export"))
@router.message(F.text.in_(button_variants("export")))
async def export_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Show export options and validate that export can run for this user."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    user_service = UserService(session_maker)
    language = await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )
    _EXPORT_BUILDER_STATE_BY_USER.pop(message.from_user.id, None)

    export_service = ExportService(session_maker, settings)
    preview = await export_service.export_deals_file(message.from_user.id, ExportFormat.CSV)
    if not preview.success:
        await replace_tracked_text(
            message,
            preview.message,
            reply_markup=get_main_menu_keyboard(language),
        )
        return

    await replace_tracked_text(
        message,
        "Выбери быстрый формат выгрузки или открой конструктор параметров.",
        reply_markup=get_export_menu_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_CSV)
async def export_csv_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Export all available deals to CSV."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    _EXPORT_BUILDER_STATE_BY_USER.pop(message.from_user.id, None)
    await _send_export_file(message, session_maker, settings, ExportFormat.CSV)


@router.message(F.text == BUTTON_EXPORT_XLSX)
async def export_xlsx_command(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Export all available deals to XLSX."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    _EXPORT_BUILDER_STATE_BY_USER.pop(message.from_user.id, None)
    await _send_export_file(message, session_maker, settings, ExportFormat.XLSX)


@router.message(F.text == BUTTON_EXPORT_CUSTOM)
async def export_custom_prompt(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Open button-based export parameter constructor."""

    if message.from_user is None:
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return

    _EXPORT_BUILDER_STATE_BY_USER[message.from_user.id] = ExportBuilderState()
    await _render_builder_root(message, _EXPORT_BUILDER_STATE_BY_USER[message.from_user.id])


@router.message(F.text == BUTTON_EXPORT_BACK_TO_EXPORT)
async def export_back_to_export_menu(message: Message) -> None:
    """Return from parameter constructor to export entry menu."""

    if message.from_user is not None:
        _EXPORT_BUILDER_STATE_BY_USER.pop(message.from_user.id, None)
    await replace_tracked_text(
        message,
        "Меню экспорта открыто. Выбери нужное действие.",
        reply_markup=get_export_menu_keyboard(),
    )


@router.message(F.text == BUTTON_BACK_TO_MENU)
async def export_back_to_main_menu(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> None:
    """Return from export flow to main menu."""

    if message.from_user is not None:
        _EXPORT_BUILDER_STATE_BY_USER.pop(message.from_user.id, None)
    language = await _resolve_language_for_user(message, session_maker)
    await replace_tracked_text(
        message,
        t("back_to_main_menu", language),
        reply_markup=get_main_menu_keyboard(language),
    )


@router.message(F.text == BUTTON_EXPORT_BACK_TO_PARAMS)
async def export_back_to_params(message: Message) -> None:
    """Return from parameter sub-menu to constructor root."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return
    await _render_builder_root(message, state)


@router.message(F.text == BUTTON_EXPORT_PARAM_FORMAT)
async def export_param_format_menu(message: Message) -> None:
    """Open format options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери формат файла.",
        reply_markup=get_export_format_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_PARAM_STATUS)
async def export_param_status_menu(message: Message) -> None:
    """Open status filter options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери фильтр статуса сделок.",
        reply_markup=get_export_status_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_PARAM_CURRENCY)
async def export_param_currency_menu(message: Message) -> None:
    """Open report currency options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери валюту отчета.",
        reply_markup=get_export_currency_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_PARAM_PROFIT)
async def export_param_profit_menu(message: Message) -> None:
    """Open profit filter options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери фильтр по чистой прибыли.",
        reply_markup=get_export_profit_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_PARAM_DAYS)
async def export_param_days_menu(message: Message) -> None:
    """Open period filter options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери период сделок для экспорта.",
        reply_markup=get_export_days_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_PARAM_LIMIT)
async def export_param_limit_menu(message: Message) -> None:
    """Open row limit options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери лимит строк в файле.",
        reply_markup=get_export_limit_keyboard(),
    )


@router.message(F.text == BUTTON_EXPORT_PARAM_FIELDS)
async def export_param_fields_menu(message: Message) -> None:
    """Open field preset options."""

    if _get_builder_state(message) is None:
        await _prompt_open_constructor(message)
        return
    await replace_tracked_text(
        message,
        "Выбери набор колонок для таблицы.",
        reply_markup=get_export_fields_keyboard(),
    )


@router.message(F.text.in_(_FORMAT_OPTIONS))
async def export_param_format_choice(message: Message) -> None:
    """Save selected export format."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    state.export_format = (
        ExportFormat.CSV if message.text == BUTTON_EXPORT_OPTION_FORMAT_CSV else ExportFormat.XLSX
    )
    await _render_builder_root(message, state, prefix="Формат обновлен.")


@router.message(F.text.in_(_STATUS_OPTIONS))
async def export_param_status_choice(message: Message) -> None:
    """Save selected status filter."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    mapping: dict[str, set[str] | None] = {
        BUTTON_EXPORT_OPTION_STATUS_ALL: None,
        BUTTON_EXPORT_OPTION_STATUS_OPEN: {"open"},
        BUTTON_EXPORT_OPTION_STATUS_CLOSED: {"closed"},
        BUTTON_EXPORT_OPTION_STATUS_CANCELLED: {"cancelled"},
    }
    state.query.statuses = mapping.get(message.text or "", None)
    await _render_builder_root(message, state, prefix="Фильтр статуса обновлен.")


@router.message(F.text.in_(_CURRENCY_OPTIONS))
async def export_param_currency_choice(message: Message) -> None:
    """Save selected report currency."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    mapping: dict[str, str | None] = {
        BUTTON_EXPORT_OPTION_CURRENCY_ALL: None,
        BUTTON_EXPORT_OPTION_CURRENCY_USD: "USD",
        BUTTON_EXPORT_OPTION_CURRENCY_EUR: "EUR",
        BUTTON_EXPORT_OPTION_CURRENCY_RUB: "RUB",
        BUTTON_EXPORT_OPTION_CURRENCY_TON: "TON",
        BUTTON_EXPORT_OPTION_CURRENCY_USDT: "USDT",
    }
    state.query.report_currency = mapping.get(message.text or "", None)
    await _render_builder_root(message, state, prefix="Валюта отчета обновлена.")


@router.message(F.text.in_(_PROFIT_OPTIONS))
async def export_param_profit_choice(message: Message) -> None:
    """Save selected profit filter."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    mapping = {
        BUTTON_EXPORT_OPTION_PROFIT_ANY: "any",
        BUTTON_EXPORT_OPTION_PROFIT_POSITIVE: "positive",
        BUTTON_EXPORT_OPTION_PROFIT_NEGATIVE: "negative",
        BUTTON_EXPORT_OPTION_PROFIT_ZERO: "zero",
        BUTTON_EXPORT_OPTION_PROFIT_NON_NEGATIVE: "non_negative",
        BUTTON_EXPORT_OPTION_PROFIT_NON_POSITIVE: "non_positive",
    }
    state.query.profit_filter = mapping.get(message.text or "", "any")
    await _render_builder_root(message, state, prefix="Фильтр прибыли обновлен.")


@router.message(F.text.in_(_DAYS_OPTIONS))
async def export_param_days_choice(message: Message) -> None:
    """Save selected period filter."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    mapping: dict[str, int | None] = {
        BUTTON_EXPORT_OPTION_DAYS_ALL: None,
        BUTTON_EXPORT_OPTION_DAYS_7: 7,
        BUTTON_EXPORT_OPTION_DAYS_30: 30,
        BUTTON_EXPORT_OPTION_DAYS_90: 90,
        BUTTON_EXPORT_OPTION_DAYS_365: 365,
    }
    state.query.days = mapping.get(message.text or "", None)
    await _render_builder_root(message, state, prefix="Период обновлен.")


@router.message(F.text.in_(_LIMIT_OPTIONS))
async def export_param_limit_choice(message: Message) -> None:
    """Save selected row limit."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    mapping: dict[str, int | None] = {
        BUTTON_EXPORT_OPTION_LIMIT_NONE: None,
        BUTTON_EXPORT_OPTION_LIMIT_20: 20,
        BUTTON_EXPORT_OPTION_LIMIT_50: 50,
        BUTTON_EXPORT_OPTION_LIMIT_100: 100,
        BUTTON_EXPORT_OPTION_LIMIT_200: 200,
        BUTTON_EXPORT_OPTION_LIMIT_500: 500,
    }
    state.query.limit = mapping.get(message.text or "", None)
    await _render_builder_root(message, state, prefix="Лимит строк обновлен.")


@router.message(F.text.in_(_FIELDS_OPTIONS))
async def export_param_fields_choice(message: Message) -> None:
    """Save selected field preset."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return

    mapping: dict[str, list[str] | None] = {
        BUTTON_EXPORT_OPTION_FIELDS_ALL: None,
        BUTTON_EXPORT_OPTION_FIELDS_COMPACT: list(_FIELD_PRESET_COMPACT),
        BUTTON_EXPORT_OPTION_FIELDS_FINANCE: list(_FIELD_PRESET_FINANCE),
        BUTTON_EXPORT_OPTION_FIELDS_TIMELINE: list(_FIELD_PRESET_TIMELINE),
    }
    state.query.fields = mapping.get(message.text or "", None)
    await _render_builder_root(message, state, prefix="Набор колонок обновлен.")


@router.message(F.text == BUTTON_EXPORT_PARAM_RESET)
async def export_param_reset(message: Message) -> None:
    """Reset all constructor parameters to defaults."""

    if message.from_user is None:
        return

    state = ExportBuilderState()
    _EXPORT_BUILDER_STATE_BY_USER[message.from_user.id] = state
    await _render_builder_root(message, state, prefix="Параметры сброшены.")


@router.message(F.text == BUTTON_EXPORT_PARAM_APPLY)
async def export_param_apply(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    """Generate export file from selected constructor parameters."""

    state = _get_builder_state(message)
    if state is None:
        await _prompt_open_constructor(message)
        return
    if not await ensure_paid_access(message, session_maker, settings):
        return
    await _send_export_file_from_builder(message, session_maker, settings, state)


async def _send_export_file(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    export_format: ExportFormat,
    *,
    query: ExportQuery | None = None,
) -> None:
    """Generate and send an export file in the requested format."""

    if message.from_user is None:
        return

    language = await _resolve_language_for_user(message, session_maker)
    export_service = ExportService(session_maker, settings)
    result = await export_service.export_deals_file(message.from_user.id, export_format, query=query)
    if not result.success or result.content is None or result.filename is None:
        await replace_tracked_text(
            message,
            result.message,
            reply_markup=get_main_menu_keyboard(language),
        )
        return

    await replace_tracked_document(
        message,
        document=BufferedInputFile(result.content, filename=result.filename),
        caption=result.message,
        reply_markup=get_main_menu_keyboard(language),
    )


async def _send_export_file_from_builder(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    state: ExportBuilderState,
) -> None:
    """Generate and send export file from constructor state."""

    if message.from_user is None:
        return

    language = await _resolve_language_for_user(message, session_maker)
    export_service = ExportService(session_maker, settings)
    query = _copy_query(state.query)
    result = await export_service.export_deals_file(
        message.from_user.id,
        state.export_format,
        query=query,
    )
    if not _is_successful_file_result(result):
        await replace_tracked_text(
            message,
            f"{result.message}\n\n{_build_constructor_summary_text(state)}",
            reply_markup=get_export_builder_keyboard(),
        )
        return

    _EXPORT_BUILDER_STATE_BY_USER.pop(message.from_user.id, None)
    await replace_tracked_document(
        message,
        document=BufferedInputFile(result.content, filename=result.filename),
        caption=result.message,
        reply_markup=get_main_menu_keyboard(language),
    )


async def _render_builder_root(
    message: Message,
    state: ExportBuilderState,
    *,
    prefix: str | None = None,
) -> None:
    """Render constructor root with current parameter summary."""

    body = _build_constructor_summary_text(state)
    if prefix:
        body = f"{prefix}\n\n{body}"

    await replace_tracked_text(
        message,
        body,
        reply_markup=get_export_builder_keyboard(),
    )


async def _prompt_open_constructor(message: Message) -> None:
    """Prompt user to open the constructor before choosing parameters."""

    await replace_tracked_text(
        message,
        "Сначала открой конструктор через кнопку «Конструктор CSV/XLSX».",
        reply_markup=get_export_menu_keyboard(),
    )


def _get_builder_state(message: Message) -> ExportBuilderState | None:
    """Return current constructor state for this user, if present."""

    if message.from_user is None:
        return None
    return _EXPORT_BUILDER_STATE_BY_USER.get(message.from_user.id)


def _copy_query(query: ExportQuery) -> ExportQuery:
    """Create a copy of export query to avoid accidental mutation."""

    return ExportQuery(
        statuses=set(query.statuses) if query.statuses is not None else None,
        currencies=set(query.currencies) if query.currencies is not None else None,
        report_currency=query.report_currency,
        profit_filter=query.profit_filter,
        days=query.days,
        fields=list(query.fields) if query.fields is not None else None,
        limit=query.limit,
    )


async def _resolve_language_for_user(
    message: Message,
    session_maker: async_sessionmaker[AsyncSession],
) -> Language:
    """Resolve preferred UI language for current user."""

    if message.from_user is None:
        return Language.RU

    user_service = UserService(session_maker)
    return await user_service.get_user_language(
        message.from_user.id,
        fallback_telegram_language=message.from_user.language_code,
    )


def _is_successful_file_result(result: ExportFileResult) -> bool:
    """Return whether result contains a ready file payload."""

    return result.success and result.content is not None and result.filename is not None


def _build_constructor_summary_text(state: ExportBuilderState) -> str:
    """Build summary text with all selected constructor parameters."""

    query = state.query
    return (
        "<b>Конструктор CSV/XLSX</b>\n"
        f"Формат: <b>{state.export_format.value.upper()}</b>\n"
        f"Статусы: <b>{_format_status_summary(query.statuses)}</b>\n"
        f"Валюта отчета: <b>{_format_currency_summary(query.report_currency)}</b>\n"
        f"Прибыль: <b>{_format_profit_summary(query.profit_filter)}</b>\n"
        f"Период: <b>{_format_days_summary(query.days)}</b>\n"
        f"Лимит: <b>{_format_limit_summary(query.limit)}</b>\n"
        f"Колонки: <b>{_format_fields_summary(query.fields)}</b>\n\n"
        "Измени нужные параметры кнопками ниже и нажми «Сформировать файл»."
    )


def _format_status_summary(statuses: set[str] | None) -> str:
    """Format status selection for summary."""

    if statuses is None:
        return "Все"

    mapping = {
        "open": "Только открытые",
        "closed": "Только закрытые",
        "cancelled": "Только отмененные",
    }
    if len(statuses) == 1:
        only = next(iter(statuses))
        return mapping.get(only, only)

    return ", ".join(sorted(statuses))


def _format_currency_summary(report_currency: str | None) -> str:
    """Format report currency selection for summary."""

    if report_currency is None:
        return "Исходная валюта сделки"
    return report_currency


def _format_profit_summary(profit_filter: str) -> str:
    """Format profit filter selection for summary."""

    mapping = {
        "any": "Любая",
        "positive": "Только прибыльные",
        "negative": "Только убыточные",
        "zero": "Только нулевые",
        "non_negative": "Не ниже 0",
        "non_positive": "Не выше 0",
    }
    return mapping.get(profit_filter, profit_filter)


def _format_days_summary(days: int | None) -> str:
    """Format period selection for summary."""

    if days is None:
        return "За все время"
    return f"Последние {days} дней"


def _format_limit_summary(limit: int | None) -> str:
    """Format row limit selection for summary."""

    if limit is None:
        return "Без лимита"
    return f"{limit} строк"


def _format_fields_summary(fields: list[str] | None) -> str:
    """Format selected field preset for summary."""

    if fields is None:
        return "Все колонки"
    if fields == _FIELD_PRESET_COMPACT:
        return "Короткий отчет"
    if fields == _FIELD_PRESET_FINANCE:
        return "Финансовый отчет"
    if fields == _FIELD_PRESET_TIMELINE:
        return "Хронология"
    return f"Набор из {len(fields)} колонок"

