"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Share Handler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate and manage share links.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import settings
from bot.models import Activity, Project
from services.share_service import create_share_link, revoke_share
from sqlalchemy import select

router = Router(name="share")
SEP = settings.SEP


@router.callback_query(F.data.startswith("share:"))
async def cb_share(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not is_admin:
        await cb.answer("⛔ Access denied", show_alert=True)
        return

    pid = cb.data.split(":")[1]
    try:
        token = await create_share_link(session, pid)
    except ValueError:
        await cb.answer("❌ Project not found", show_alert=True)
        return

    link = f"https://t.me/{settings.BOT_USERNAME}?start={token}"

    session.add(Activity(action="share", project_id=pid, user_id=cb.from_user.id))
    await session.commit()

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Copy Link", url=link)],
        [InlineKeyboardButton(text="🚫 Revoke Link", callback_data=f"revoke:{pid}")],
        [InlineKeyboardButton(text="◀️ Back", callback_data=f"project:{pid}")],
    ])

    await cb.message.edit_text(
        f"{SEP}\n🔗 <b>Share Link Generated</b>\n{SEP}\n\n"
        f"<code>{link}</code>\n\n"
        f"Send this link to anyone. They can download the project directly.",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await cb.answer()


@router.callback_query(F.data.startswith("revoke:"))
async def cb_revoke(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not is_admin:
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    ok = await revoke_share(session, pid)
    if ok:
        await cb.answer("✅ Share link revoked", show_alert=True)
    else:
        await cb.answer("ℹ️ No active share link", show_alert=True)

    # Redirect back to project card
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if project:
        from keyboards.file_actions import project_actions_kb
        await cb.message.edit_text(
            project.card_text(),
            reply_markup=project_actions_kb(project.id, project.favorite, project.pinned),
            parse_mode="HTML",
        )
