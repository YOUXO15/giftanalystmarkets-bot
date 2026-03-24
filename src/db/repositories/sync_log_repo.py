"""Repository for synchronization logs."""

from __future__ import annotations

from sqlalchemy import select

from src.db.models.sync_log import SyncLog
from src.db.repositories.base import BaseRepository
from src.utils.enums import SyncStatus


class SyncLogRepository(BaseRepository[SyncLog]):
    """Data access for sync logs."""

    async def get_by_id(self, sync_log_id: int) -> SyncLog | None:
        """Fetch a sync log by primary key."""

        return await self.session.get(SyncLog, sync_log_id)

    async def create_log(
        self,
        user_id: int,
        sync_type: str,
        status: SyncStatus,
        message: str | None = None,
    ) -> SyncLog:
        """Create a new sync log entry."""

        sync_log = SyncLog(
            user_id=user_id,
            sync_type=sync_type,
            status=status,
            message=message,
        )
        return await self.add(sync_log)

    async def update_status(self, sync_log: SyncLog, status: SyncStatus, message: str | None = None) -> SyncLog:
        """Update status and message for an existing sync log instance."""

        sync_log.status = status
        sync_log.message = message
        await self.session.flush()
        return sync_log

    async def update_status_by_id(
        self,
        sync_log_id: int,
        status: SyncStatus,
        message: str | None = None,
    ) -> SyncLog | None:
        """Update status and message using a fresh ORM instance from the current session."""

        sync_log = await self.get_by_id(sync_log_id)
        if sync_log is None:
            return None
        return await self.update_status(sync_log, status, message)

    async def get_latest_for_user(self, user_id: int) -> SyncLog | None:
        """Fetch the most recent sync log for a user."""

        stmt = (
            select(SyncLog)
            .where(SyncLog.user_id == user_id)
            .order_by(SyncLog.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)
