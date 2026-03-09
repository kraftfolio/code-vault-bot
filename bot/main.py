"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Bot Entry Point
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creates the Bot & Dispatcher, registers
all routers and middlewares, and starts
long-polling.

Run with:
    python -m bot.main
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database import init_db
from bot.middlewares import AdminFlagMiddleware, DatabaseMiddleware, RateLimitMiddleware

# ── Logging setup ─────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-22s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("vault")


async def main() -> None:
    """Bootstrap the bot and start polling."""
    # Validate config
    settings.validate()

    # Ensure data dirs exist
    settings.FILES_DIR.mkdir(parents=True, exist_ok=True)

    # Initialise database
    await init_db()
    logger.info("Database initialised at %s", settings.DB_PATH)

    # Create bot instance
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Create dispatcher with in-memory FSM storage
    dp = Dispatcher(storage=MemoryStorage())

    # ── Register middlewares (order matters) ──────
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AdminFlagMiddleware())
    dp.update.middleware(RateLimitMiddleware())

    # ── Register routers ─────────────────────────
    #  Admin router MUST be included before public
    #  so that admin /start takes priority.
    from handlers.admin import router as admin_router
    from handlers.upload import router as upload_router
    from handlers.search import router as search_router
    from handlers.share import router as share_router
    from handlers.github import router as github_router
    from handlers.public import router as public_router

    dp.include_routers(
        admin_router,
        upload_router,
        search_router,
        share_router,
        github_router,
        public_router,
    )

    # ── Start polling ────────────────────────────
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  ⚡ KRISH CODE VAULT — Online")
    logger.info("  Admin: %s (%s)", settings.ADMIN_NAME, settings.ADMIN_TG)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
