"""Legacy external market synchronization business logic."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import Settings
from src.db.repositories.deal_repo import DealRepository
from src.db.repositories.sync_log_repo import SyncLogRepository
from src.db.repositories.user_repo import UserRepository
from src.integrations.giftsatellite_client import GiftAnalystMarketsClient
from src.utils.enums import SyncStatus
from src.utils.helpers import build_registration_required_text

logger = logging.getLogger(__name__)


class SyncService:
    """Application service for the legacy GiftAnalystMarkets sync flow."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self._session_maker = session_maker
        self._client = GiftAnalystMarketsClient(settings)

    async def run_manual_sync(self, telegram_id: int) -> str:
        """Run a manual sync for the current Telegram user."""

        user_id = await self._get_user_id(telegram_id)
        if user_id is None:
            return build_registration_required_text()

        sync_log_id = await self._create_sync_log(user_id)

        try:
            payload = await self._client.fetch_user_deals(telegram_id)
            if not payload.is_configured or not payload.success:
                await self._update_sync_log(sync_log_id, SyncStatus.FAILED, payload.message)
                return payload.message

            synced_count = await self._save_deals_and_complete_log(user_id, sync_log_id, payload.items)
            return (
                "<b>Синхронизация завершена</b>\n"
                f"{payload.message}\n"
                f"Получено сделок: {len(payload.items)}\n"
                f"Сохранено или обновлено: {synced_count}"
            )
        except Exception as exc:
            logger.exception("Sync failed for telegram_id=%s", telegram_id)
            await self._update_sync_log(
                sync_log_id,
                SyncStatus.FAILED,
                f"Внутренняя ошибка синхронизации: {exc}",
            )
            return "Во время синхронизации произошла внутренняя ошибка. Проверь логи приложения."

    async def _get_user_id(self, telegram_id: int) -> int | None:
        """Return the internal user id for a Telegram account."""

        async with self._session_maker() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(telegram_id)
            return user.id if user is not None else None

    async def _create_sync_log(self, user_id: int) -> int:
        """Create an in-progress sync log and return its identifier."""

        async with self._session_maker() as session:
            sync_log_repo = SyncLogRepository(session)
            async with session.begin():
                sync_log = await sync_log_repo.create_log(
                    user_id=user_id,
                    sync_type="manual",
                    status=SyncStatus.IN_PROGRESS,
                    message="Синхронизация запущена.",
                )
            return sync_log.id

    async def _update_sync_log(self, sync_log_id: int, status: SyncStatus, message: str) -> None:
        """Update a sync log in a fresh async session."""

        async with self._session_maker() as session:
            sync_log_repo = SyncLogRepository(session)
            async with session.begin():
                await sync_log_repo.update_status_by_id(sync_log_id, status, message)

    async def _save_deals_and_complete_log(
        self,
        user_id: int,
        sync_log_id: int,
        payload_items: list[dict[str, object]],
    ) -> int:
        """Persist synced deals and mark the sync log as successful in one transaction."""

        async with self._session_maker() as session:
            deal_repo = DealRepository(session)
            sync_log_repo = SyncLogRepository(session)
            async with session.begin():
                synced_count = await deal_repo.upsert_many(user_id, payload_items)
                await sync_log_repo.update_status_by_id(
                    sync_log_id,
                    SyncStatus.SUCCESS,
                    f"Синхронизировано сделок: {synced_count}.",
                )
            return synced_count
