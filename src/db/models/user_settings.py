"""User settings database model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, TimestampMixin
from src.utils.enums import Currency, Language

if TYPE_CHECKING:
    from src.db.models.user import User


class UserSettings(TimestampMixin, Base):
    """Stores per-user preferences for analytics reports."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    notifications_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    report_currency: Mapped[Currency] = mapped_column(
        SAEnum(
            Currency,
            name="user_report_currency_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=Currency.USD,
        nullable=False,
    )
    auto_sync_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    preferred_language: Mapped[Language] = mapped_column(
        SAEnum(
            Language,
            name="user_language_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=Language.RU,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="settings")
