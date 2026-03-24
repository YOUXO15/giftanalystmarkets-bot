"""Synchronization log model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from src.db.base import Base, CreatedAtMixin
from src.utils.enums import SyncStatus

if TYPE_CHECKING:
    from src.db.models.user import User


class SyncLog(CreatedAtMixin, Base):
    """Tracks sync executions for observability and debugging."""

    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    sync_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(
        SAEnum(
            SyncStatus,
            name="sync_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="sync_logs")
