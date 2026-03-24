"""Application entrypoint for Telegram bot polling."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.router import router as root_router
from src.config.logging import setup_logging
from src.config.settings import get_settings
from src.db.session import DatabaseSessionManager
from src.utils.helpers import get_bot_commands
from src.utils.process_lock import SingleInstanceLock

logger = logging.getLogger(__name__)


async def main() -> None:
    """Create application dependencies and start Telegram polling."""

    settings = get_settings()
    setup_logging(settings.log_level)
    process_lock = SingleInstanceLock("giftanalystmarkets-bot")
    if not process_lock.acquire():
        logger.error("Another GiftAnalystMarkets bot process is already running. Exiting.")
        return

    db_manager = DatabaseSessionManager(settings)
    bot = Bot(
        token=settings.bot_token_value,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(root_router)

    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_my_commands(get_bot_commands())
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)

    try:
        await dispatcher.start_polling(
            bot,
            settings=settings,
            session_maker=db_manager.session_maker,
            polling_timeout=settings.bot_polling_timeout,
        )
    finally:
        logger.info("Shutting down bot")
        await bot.session.close()
        await db_manager.dispose()
        process_lock.release()


if __name__ == "__main__":
    asyncio.run(main())
