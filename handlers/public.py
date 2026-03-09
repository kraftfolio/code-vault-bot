"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Public Handlers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Non-admin routes: start screen, deep-link
download, preview, AI summary.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models import Activity, Project, User
from keyboards.file_actions import public_project_kb
from services.file_manager import get_absolute_path
from services.preview_generator import generate_preview
from services.ai_summary import generate_summary
from services.share_service import resolve_token

logger = logging.getLogger(__name__)
router = Router(name="public")
SEP = settings.SEP


# ── Register user helper ─────────────────────────
async def _ensure_user(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    if not result.scalar_one_or_none():
        session.add(User(telegram_id=telegram_id))
        await session.commit()


# ── /start (public + deep link) ──────────────────
@router.message(CommandStart(deep_link=True))
async def cmd_start_deep(message: Message, is_admin: bool, session: AsyncSession, **kwargs):
    """Handle /start with a deep-link token (e.g. /start file_abc123)."""
    if is_admin:
        return  # admin handler takes precedence for bare /start

    await _ensure_user(session, message.from_user.id)

    token = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if not token:
        await _show_public_home(message)
        return

    project = await resolve_token(session, token)
    if not project:
        await message.answer("❌ Invalid or expired link.", parse_mode="HTML")
        return

    text = (
        f"{SEP}\n📦 <b>SHARED PROJECT</b>\n{SEP}\n\n"
        f"<b>Title:</b> {project.title}\n"
        f"<b>Status:</b> {project.status_emoji()} {project.status.title()}\n"
        f"<b>Uploaded by:</b> {settings.ADMIN_NAME} ({settings.ADMIN_TG})\n"
    )
    await message.answer(text, reply_markup=public_project_kb(project.id), parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start_public(message: Message, is_admin: bool, session: AsyncSession, **kwargs):
    """Public /start — shown to non-admin users."""
    if is_admin:
        return  # admin router handles /start
    await _ensure_user(session, message.from_user.id)
    await _show_public_home(message)


async def _show_public_home(message: Message) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Download via Link", callback_data="pub_paste_link")],
    ])
    text = (
        f"{SEP}\n📦 <b>CODE DOWNLOAD</b>\n{SEP}\n\n"
        f"Hello 👋\n\n"
        f"This bot is used to download shared code archives.\n\n"
        f"If someone sent you a link, paste it here."
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Paste link prompt ────────────────────────────
@router.callback_query(F.data == "pub_paste_link")
async def cb_paste_link(cb: CallbackQuery, **kwargs):
    await cb.message.edit_text(
        f"{SEP}\n📥 <b>Download via Link</b>\n{SEP}\n\n"
        "Paste the share link or token you received.\n\n"
        "<i>Example: file_k92Js8f3PqL</i>",
        parse_mode="HTML",
    )
    await cb.answer()


# ── Handle pasted tokens (plain text) ────────────
@router.message(F.text.startswith("file_"))
async def on_token_paste(message: Message, is_admin: bool, session: AsyncSession, **kwargs):
    if is_admin:
        return  # admin uses the admin router

    token = message.text.strip().split("/")[-1].split("?start=")[-1]
    project = await resolve_token(session, token)
    if not project:
        await message.answer("❌ Invalid or expired link.", parse_mode="HTML")
        return

    text = (
        f"{SEP}\n📦 <b>SHARED PROJECT</b>\n{SEP}\n\n"
        f"<b>Title:</b> {project.title}\n"
        f"<b>Status:</b> {project.status_emoji()} {project.status.title()}\n"
        f"<b>Uploaded by:</b> {settings.ADMIN_NAME} ({settings.ADMIN_TG})\n"
    )
    await message.answer(text, reply_markup=public_project_kb(project.id), parse_mode="HTML")


# ── Public Download ──────────────────────────────
@router.callback_query(F.data.startswith("pub_dl:"))
async def cb_pub_download(cb: CallbackQuery, session: AsyncSession, **kwargs):
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project or not project.share_token:
        await cb.answer("❌ This file is no longer available.", show_alert=True)
        return

    file_path = get_absolute_path(project.file_path)
    if not file_path:
        await cb.answer("❌ File not found.", show_alert=True)
        return

    doc = FSInputFile(file_path, filename=f"{project.title}.zip")
    await cb.message.answer_document(
        doc,
        caption=(
            f"📦 <b>{project.title}</b>\n\n"
            f"✨ File provided by {settings.ADMIN_NAME}\n"
            f"Telegram: {settings.ADMIN_TG}\n\n"
            f"<i>{settings.ATTRIBUTION}</i>"
        ),
        parse_mode="HTML",
    )

    project.downloads_count += 1
    session.add(Activity(action="download", project_id=project.id, user_id=cb.from_user.id))
    await session.commit()
    await cb.answer()


# ── Public Preview ───────────────────────────────
@router.callback_query(F.data.startswith("pub_preview:"))
async def cb_pub_preview(cb: CallbackQuery, session: AsyncSession, **kwargs):
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project or not project.share_token:
        await cb.answer("❌ Not available.", show_alert=True)
        return

    file_path = get_absolute_path(project.file_path)
    if not file_path:
        await cb.answer("❌ File not found.", show_alert=True)
        return

    preview = generate_preview(file_path)
    await cb.message.answer(preview, parse_mode="HTML")
    await cb.answer()


# ── Public AI Summary ────────────────────────────
@router.callback_query(F.data.startswith("pub_ai:"))
async def cb_pub_ai(cb: CallbackQuery, session: AsyncSession, **kwargs):
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project or not project.share_token:
        await cb.answer("❌ Not available.", show_alert=True)
        return

    if project.ai_summary:
        await cb.message.answer(project.ai_summary, parse_mode="HTML")
        await cb.answer()
        return

    await cb.answer("🧠 Generating summary… please wait.")
    file_path = get_absolute_path(project.file_path)
    if not file_path:
        await cb.message.answer("❌ File not found.")
        return

    summary = await generate_summary(file_path)
    project.ai_summary = summary
    await session.commit()
    await cb.message.answer(summary, parse_mode="HTML")
