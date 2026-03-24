"""Root router configuration."""

from __future__ import annotations

from aiogram import Router

from src.bot.handlers import billing, deals, export, help, settings, start, stats, sync, ton

router = Router(name="root")
router.include_router(start.router)
router.include_router(help.router)
router.include_router(billing.router)
router.include_router(sync.router)
router.include_router(deals.router)
router.include_router(stats.router)
router.include_router(ton.router)
router.include_router(export.router)
router.include_router(settings.router)
