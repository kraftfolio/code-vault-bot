"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Search Handler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Smart search with ranked results.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from keyboards.admin_menu import back_to_dashboard_kb
from services.search_engine import SearchEngine

router = Router(name="search")
SEP = settings.SEP


class SearchStates(StatesGroup):
    waiting_query = State()


# ── Start search ─────────────────────────────────
@router.callback_query(F.data == "search_start")
async def cb_search_start(cb: CallbackQuery, is_admin: bool, state: FSMContext, **kwargs):
    if not is_admin:
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    await state.set_state(SearchStates.waiting_query)
    await cb.message.edit_text(
        f"{SEP}\n🔎 <b>Smart Search</b>\n{SEP}\n\n"
        "Type your search query.\n\n"
        "<i>Examples: telegram bot, ai, complete, 2026</i>",
        parse_mode="HTML",
    )
    await cb.answer()


# ── Process query ────────────────────────────────
@router.message(SearchStates.waiting_query, F.text)
async def on_search_query(message: Message, is_admin: bool, state: FSMContext, session, **kwargs):
    if not is_admin:
        return
    query = message.text.strip()
    if not query:
        await message.answer("❌ Please enter a search term.")
        return

    results = await SearchEngine.search(session, query)
    await state.clear()

    if not results:
        await message.answer(
            f"{SEP}\n🔎 <b>Search Results</b>\n{SEP}\n\n"
            f"No results for: <i>{query}</i>",
            reply_markup=back_to_dashboard_kb(),
            parse_mode="HTML",
        )
        return

    buttons: list[list[InlineKeyboardButton]] = []
    for r in results:
        p = r.project
        emoji = p.status_emoji()
        score_bar = "●" * min(int(r.score), 5)
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {p.title}  ({score_bar})",
                callback_data=f"project:{p.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="dashboard")])

    await message.answer(
        f"{SEP}\n🔎 <b>Search Results</b>\n{SEP}\n\n"
        f"Found <b>{len(results)}</b> result(s) for: <i>{query}</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
