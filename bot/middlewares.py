"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Middlewares
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• DatabaseMiddleware  — injects async session
• AdminFlagMiddleware — injects is_admin bool
• RateLimitMiddleware  — per-user download throttle
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from bot.config import settings
from bot.database import async_session


# ── Database Session Injection ────────────────────
class DatabaseMiddleware(BaseMiddleware):
    """Provides ``session`` in handler data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)


# ── Admin Flag ────────────────────────────────────
class AdminFlagMiddleware(BaseMiddleware):
    """Sets ``is_admin: bool`` in handler kwargs."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        data["is_admin"] = bool(user and user.id == settings.ADMIN_ID)
        return await handler(event, data)


# ── Rate Limiter (in-memory token bucket) ─────────
class RateLimitMiddleware(BaseMiddleware):
    """
    Limits requests per user per minute.
    Stored in-memory — resets on restart (acceptable for single-process bot).
    """

    def __init__(self) -> None:
        super().__init__()
        self._buckets: Dict[int, list[float]] = defaultdict(list)
        self._limit = settings.RATE_LIMIT_PER_MINUTE

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            uid = user.id
            now = time.monotonic()
            # Purge entries older than 60 s
            self._buckets[uid] = [t for t in self._buckets[uid] if now - t < 60]
            if len(self._buckets[uid]) >= self._limit and uid != settings.ADMIN_ID:
                # Silently drop — or we could send a message
                if isinstance(event, Update) and event.callback_query:
                    await event.callback_query.answer(
                        "⏳ Rate limit reached. Please wait a moment.",
                        show_alert=True,
                    )
                return None
            self._buckets[uid].append(now)
        return await handler(event, data)
