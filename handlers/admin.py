"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Admin Handlers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dashboard, statistics, favorites, pins,
shared links, activity log.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select, desc

from bot.config import settings
from bot.models import Activity, Project
from keyboards.admin_menu import admin_dashboard_kb, back_to_dashboard_kb
from keyboards.file_actions import project_actions_kb, confirm_delete_kb
from services.file_manager import get_absolute_path, delete_file
from services.preview_generator import generate_preview
from services.ai_summary import generate_summary

logger = logging.getLogger(__name__)
router = Router(name="admin")

SEP = settings.SEP
PAGE_SIZE = 5


# ── Helper: admin guard ──────────────────────────
def _admin_only(is_admin: bool) -> bool:
    return is_admin


# ── /start (admin) ───────────────────────────────
@router.message(Command("start"))
async def cmd_start(message: Message, is_admin: bool, session):
    if not is_admin:
        return  # handled by public router
    text = (
        f"{SEP}\n"
        f"⚡ <b>KRISH CODE VAULT</b>\n"
        f"{SEP}\n\n"
        f"Welcome back <b>{settings.ADMIN_NAME}</b>.\n"
        f"Your personal project archive is ready."
    )
    await message.answer(text, reply_markup=admin_dashboard_kb(), parse_mode="HTML")


# ── Dashboard callback ───────────────────────────
@router.callback_query(F.data == "dashboard")
async def cb_dashboard(cb: CallbackQuery, is_admin: bool, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    text = (
        f"{SEP}\n"
        f"⚡ <b>KRISH CODE VAULT</b>\n"
        f"{SEP}\n\n"
        f"Welcome back <b>{settings.ADMIN_NAME}</b>.\n"
        f"Your personal project archive is ready."
    )
    await cb.message.edit_text(text, reply_markup=admin_dashboard_kb(), parse_mode="HTML")
    await cb.answer()


# ── My Projects (paginated) ──────────────────────
@router.callback_query(F.data.startswith("my_projects:"))
async def cb_my_projects(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    offset = int(cb.data.split(":")[1])
    result = await session.execute(
        select(Project)
        .order_by(Project.pinned.desc(), Project.uploaded_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    projects = result.scalars().all()
    count_result = await session.execute(select(func.count(Project.id)))
    total = count_result.scalar() or 0

    if not projects:
        await cb.message.edit_text(
            f"{SEP}\n📂 <b>My Projects</b>\n{SEP}\n\nNo projects yet. Upload your first one!",
            reply_markup=back_to_dashboard_kb(),
            parse_mode="HTML",
        )
        await cb.answer()
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    buttons: list[list[InlineKeyboardButton]] = []
    for p in projects:
        emoji = p.status_emoji()
        pin = "📌 " if p.pinned else ""
        fav = "⭐ " if p.favorite else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{pin}{fav}{emoji} {p.title}",
                callback_data=f"project:{p.id}",
            )
        ])

    # Pagination
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"my_projects:{max(0, offset - PAGE_SIZE)}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"my_projects:{offset + PAGE_SIZE}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="dashboard")])

    text = f"{SEP}\n📂 <b>My Projects</b> ({total} total)\n{SEP}"
    await cb.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await cb.answer()


# ── Project Card ─────────────────────────────────
@router.callback_query(F.data.startswith("project:"))
async def cb_project_card(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Project not found", show_alert=True)
        return

    text = project.card_text()
    kb = project_actions_kb(project.id, project.favorite, project.pinned)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await cb.answer()


# ── Download (Admin) ─────────────────────────────
@router.callback_query(F.data.startswith("dl:"))
async def cb_download(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Project not found", show_alert=True)
        return

    file_path = get_absolute_path(project.file_path)
    if not file_path:
        await cb.answer("❌ File not found on disk", show_alert=True)
        return

    from aiogram.types import FSInputFile
    doc = FSInputFile(file_path, filename=f"{project.title}.zip")
    await cb.message.answer_document(doc, caption=f"📦 <b>{project.title}</b>", parse_mode="HTML")

    project.downloads_count += 1
    session.add(Activity(action="download", project_id=project.id, user_id=cb.from_user.id))
    await session.commit()
    await cb.answer()


# ── Preview (Admin) ──────────────────────────────
@router.callback_query(F.data.startswith("preview:"))
async def cb_preview(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Project not found", show_alert=True)
        return

    file_path = get_absolute_path(project.file_path)
    if not file_path:
        await cb.answer("❌ File not found", show_alert=True)
        return

    preview_text = generate_preview(file_path)
    await cb.message.answer(preview_text, parse_mode="HTML")
    await cb.answer()


# ── AI Summary (Admin) ───────────────────────────
@router.callback_query(F.data.startswith("ai:"))
async def cb_ai_summary(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Project not found", show_alert=True)
        return

    # Return cached if available
    if project.ai_summary:
        await cb.message.answer(project.ai_summary, parse_mode="HTML")
        await cb.answer()
        return

    await cb.answer("🧠 Generating AI summary… please wait.")

    file_path = get_absolute_path(project.file_path)
    if not file_path:
        await cb.message.answer("❌ File not found on disk.")
        return

    summary = await generate_summary(file_path)
    project.ai_summary = summary
    await session.commit()
    await cb.message.answer(summary, parse_mode="HTML")


# ── Favorite toggle ──────────────────────────────
@router.callback_query(F.data.startswith("fav:"))
async def cb_toggle_fav(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Not found", show_alert=True)
        return
    project.favorite = not project.favorite
    await session.commit()
    emoji = "⭐" if project.favorite else "☆"
    await cb.answer(f"{emoji} {'Added to' if project.favorite else 'Removed from'} favorites")
    # Refresh card
    text = project.card_text()
    kb = project_actions_kb(project.id, project.favorite, project.pinned)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ── Pin toggle ───────────────────────────────────
@router.callback_query(F.data.startswith("pin:"))
async def cb_toggle_pin(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Not found", show_alert=True)
        return
    project.pinned = not project.pinned
    await session.commit()
    emoji = "📌" if project.pinned else "📍"
    await cb.answer(f"{emoji} {'Pinned' if project.pinned else 'Unpinned'}")
    text = project.card_text()
    kb = project_actions_kb(project.id, project.favorite, project.pinned)
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ── Delete flow ──────────────────────────────────
@router.callback_query(F.data.startswith("del:"))
async def cb_delete_ask(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Not found", show_alert=True)
        return
    text = f"{SEP}\n🗑 <b>Delete Project?</b>\n{SEP}\n\n<b>{project.title}</b>\n\nThis action cannot be undone."
    await cb.message.edit_text(text, reply_markup=confirm_delete_kb(pid), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("confirm_del:"))
async def cb_confirm_delete(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    pid = cb.data.split(":")[1]
    result = await session.execute(select(Project).where(Project.id == pid))
    project = result.scalar_one_or_none()
    if not project:
        await cb.answer("❌ Not found", show_alert=True)
        return

    await delete_file(project.file_path)
    session.add(Activity(action="delete", project_id=None, user_id=cb.from_user.id))
    await session.delete(project)
    await session.commit()

    await cb.message.edit_text(
        f"✅ Project deleted successfully.",
        reply_markup=back_to_dashboard_kb(),
        parse_mode="HTML",
    )
    await cb.answer()


# ── Statistics ───────────────────────────────────
@router.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return

    total_result = await session.execute(select(func.count(Project.id)))
    total = total_result.scalar() or 0

    dl_result = await session.execute(select(func.sum(Project.downloads_count)))
    total_downloads = dl_result.scalar() or 0

    # Most downloaded
    top_result = await session.execute(
        select(Project).order_by(Project.downloads_count.desc()).limit(1)
    )
    top_project = top_result.scalar_one_or_none()

    # Recent uploads
    recent_result = await session.execute(
        select(Project).order_by(Project.uploaded_at.desc()).limit(3)
    )
    recent = recent_result.scalars().all()

    top_name = f"{top_project.title} ({top_project.downloads_count} downloads)" if top_project else "—"
    recent_lines = "\n".join(f"  • {r.title}" for r in recent) or "  • None"

    text = (
        f"{SEP}\n"
        f"📊 <b>Statistics</b>\n"
        f"{SEP}\n\n"
        f"📦 Total Projects: <b>{total}</b>\n"
        f"⬇ Total Downloads: <b>{total_downloads}</b>\n"
        f"🏆 Most Downloaded: <b>{top_name}</b>\n\n"
        f"🕐 Recent Uploads:\n{recent_lines}"
    )
    await cb.message.edit_text(text, reply_markup=back_to_dashboard_kb(), parse_mode="HTML")
    await cb.answer()


# ── Favorites list ───────────────────────────────
@router.callback_query(F.data.startswith("favorites:"))
async def cb_favorites(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    offset = int(cb.data.split(":")[1])
    result = await session.execute(
        select(Project)
        .where(Project.favorite == True)
        .order_by(Project.uploaded_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    projects = result.scalars().all()

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if not projects:
        await cb.message.edit_text(
            f"{SEP}\n⭐ <b>Favorites</b>\n{SEP}\n\nNo favorites yet.",
            reply_markup=back_to_dashboard_kb(), parse_mode="HTML",
        )
        await cb.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=f"⭐ {p.title}", callback_data=f"project:{p.id}")]
        for p in projects
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="dashboard")])
    await cb.message.edit_text(
        f"{SEP}\n⭐ <b>Favorites</b>\n{SEP}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await cb.answer()


# ── Pinned list ──────────────────────────────────
@router.callback_query(F.data.startswith("pinned:"))
async def cb_pinned(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    offset = int(cb.data.split(":")[1])
    result = await session.execute(
        select(Project)
        .where(Project.pinned == True)
        .order_by(Project.uploaded_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    projects = result.scalars().all()

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if not projects:
        await cb.message.edit_text(
            f"{SEP}\n📌 <b>Pinned Projects</b>\n{SEP}\n\nNo pinned projects.",
            reply_markup=back_to_dashboard_kb(), parse_mode="HTML",
        )
        await cb.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=f"📌 {p.title}", callback_data=f"project:{p.id}")]
        for p in projects
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="dashboard")])
    await cb.message.edit_text(
        f"{SEP}\n📌 <b>Pinned Projects</b>\n{SEP}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await cb.answer()


# ── Shared Links list ────────────────────────────
@router.callback_query(F.data.startswith("shared_links:"))
async def cb_shared_links(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    from services.share_service import list_shared_projects
    offset = int(cb.data.split(":")[1])
    projects = await list_shared_projects(session, offset, PAGE_SIZE)

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    if not projects:
        await cb.message.edit_text(
            f"{SEP}\n🔗 <b>Shared Links</b>\n{SEP}\n\nNo active share links.",
            reply_markup=back_to_dashboard_kb(), parse_mode="HTML",
        )
        await cb.answer()
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"🔗 {p.title}",
            callback_data=f"project:{p.id}",
        )]
        for p in projects
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Back to Dashboard", callback_data="dashboard")])
    await cb.message.edit_text(
        f"{SEP}\n🔗 <b>Shared Links</b>\n{SEP}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )
    await cb.answer()


# ── Activity Log ─────────────────────────────────
@router.callback_query(F.data == "activity_log")
async def cb_activity_log(cb: CallbackQuery, is_admin: bool, session, **kwargs):
    if not _admin_only(is_admin):
        await cb.answer("⛔ Access denied", show_alert=True)
        return

    result = await session.execute(
        select(Activity).order_by(Activity.timestamp.desc()).limit(15)
    )
    activities = result.scalars().all()

    if not activities:
        await cb.message.edit_text(
            f"{SEP}\n📋 <b>Activity Log</b>\n{SEP}\n\nNo activity recorded yet.",
            reply_markup=back_to_dashboard_kb(), parse_mode="HTML",
        )
        await cb.answer()
        return

    action_emoji = {"upload": "📤", "download": "⬇", "share": "🔗", "delete": "🗑"}
    lines: list[str] = []
    for a in activities:
        emoji = action_emoji.get(a.action, "📝")
        ts = a.timestamp.strftime("%Y-%m-%d %H:%M") if a.timestamp else "?"
        lines.append(f"{emoji} <b>{a.action.title()}</b> — {ts}")

    text = f"{SEP}\n📋 <b>Activity Log</b>\n{SEP}\n\n" + "\n".join(lines)
    await cb.message.edit_text(text, reply_markup=back_to_dashboard_kb(), parse_mode="HTML")
    await cb.answer()
