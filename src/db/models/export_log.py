"""User export history used for daily rate limiting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, CreatedAtMixin
from src.utils.enums import ExportFormat

if TYPE_CHECKING:
    from src.db.models.user import User


class ExportLog(CreatedAtMixin, Base):
    """Stores successful export events for per-day quotas."""

    __tablename__ = "export_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    export_format: Mapped[ExportFormat] = mapped_column(
        SAEnum(
            ExportFormat,
            name="export_log_format_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    rows_exported: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["User"] = relationship(back_populates="export_logs")
