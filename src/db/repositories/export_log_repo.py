"""Repository for export history and quotas."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from src.db.models.export_log import ExportLog
from src.db.repositories.base import BaseRepository
from src.utils.enums import ExportFormat


class ExportLogRepository(BaseRepository[ExportLog]):
    """Data access for user export logs."""

    async def count_between(
        self,
        user_id: int,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        """Count export events for a user in the provided time window."""

        stmt = select(func.count(ExportLog.id)).where(
            ExportLog.user_id == user_id,
            ExportLog.created_at >= start_at,
            ExportLog.created_at < end_at,
        )
        count = await self.session.scalar(stmt)
        return int(count or 0)

    async def create(
        self,
        *,
        user_id: int,
        export_format: ExportFormat,
        rows_exported: int,
    ) -> ExportLog:
        """Persist a successful export event."""

        export_log = ExportLog(
            user_id=user_id,
            export_format=export_format,
            rows_exported=rows_exported,
        )
        return await self.add(export_log)
