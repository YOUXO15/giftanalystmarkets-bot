"""Project-wide enumerations."""

from __future__ import annotations

from enum import StrEnum


class DealStatus(StrEnum):
    """Supported deal lifecycle statuses."""

    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class SyncStatus(StrEnum):
    """Possible synchronization execution statuses."""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class Currency(StrEnum):
    """Supported reporting and deal currencies."""

    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    TON = "TON"
    USDT = "USDT"


class ExportFormat(StrEnum):
    """Supported local file export formats."""

    CSV = "csv"
    XLSX = "xlsx"


class SubscriptionStatus(StrEnum):
    """Lifecycle of a paid analytics subscription."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    EXPIRED = "expired"


class PaymentInvoiceStatus(StrEnum):
    """Known statuses of a Crypto Pay invoice tracked locally."""

    ACTIVE = "active"
    PAID = "paid"
    EXPIRED = "expired"


class BillingPlanType(StrEnum):
    """Supported subscription pricing variants."""

    INTRO = "intro"
    MONTHLY = "monthly"
