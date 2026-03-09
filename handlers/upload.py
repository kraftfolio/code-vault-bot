"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Upload Handler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FSM-driven multi-step upload flow.
"""

from __future__ import annotations

import logging
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models import Activity, Project
from keyboards.admin_menu import admin_dashboard_kb
from keyboards.status_buttons import confirm_upload_kb, status_selection_kb
from services.file_manager import save_uploaded_file
from utils.validators import validate_file_size, validate_zip_filename

logger = logging.getLogger(__name__)
router = Router(name="upload")

SEP = settings.SEP


# ── FSM states ───────────────────────────────────
class UploadStates(StatesGroup):
    waiting_file = State()
    waiting_title = State()
    waiting_tags = State()
    waiting_date = State()
    waiting_status = State()
    waiting_github = State()
    confirming = State()


# ── Step 0: Start upload ────────────────────────
@router.callback_query(F.data == "upload_start")
async def cb_upload_start(cb: CallbackQuery, is_admin: bool, state: FSMContext, **kwargs):
    if not is_admin:
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    await state.set_state(UploadStates.waiting_file)
    await cb.message.edit_text(
        f"{SEP}\n📤 <b>Upload Project</b>\n{SEP}\n\n"
        f"Send me a <b>.zip</b> file (max 20 MB).\n\n"
        f"<i>⚠️ Telegram limits bot downloads to 20 MB.</i>",
        parse_mode="HTML",
    )
    await cb.answer()


# ── Step 1: Receive ZIP ─────────────────────────
@router.message(UploadStates.waiting_file, F.document)
async def on_file_received(message: Message, is_admin: bool, state: FSMContext, **kwargs):
    if not is_admin:
        return

    doc = message.document

    if not validate_zip_filename(doc.file_name):
        await message.answer("❌ Please send a <b>.zip</b> file.", parse_mode="HTML")
        return

    # Telegram Bot API hard limit: 20 MB for getFile
    max_download = 20 * 1024 * 1024
    if doc.file_size and doc.file_size > max_download:
        await message.answer(
            "❌ File is too large.\n\n"
            "Telegram Bot API limits downloads to <b>20 MB</b>.\n"
            "Please compress your project further or split it.",
            parse_mode="HTML",
        )
        return

    if not validate_file_size(doc.file_size):
        await message.answer(
            f"❌ File is too large. Max size: <b>{settings.MAX_FILE_SIZE_MB} MB</b>.",
            parse_mode="HTML",
        )
        return

    await message.answer("⏳ Downloading file… (this may take a moment)")

    # Stream download via bot.download()
    from io import BytesIO
    buf = BytesIO()
    await message.bot.download(doc, destination=buf)
    content = buf.getvalue()

    # Save to disk
    relative_path = await save_uploaded_file(content, doc.file_name)
    await state.update_data(file_path=relative_path, original_name=doc.file_name)

    await message.answer(
        "✅ File received!\n\n1️⃣ Enter a <b>project title</b>:",
        parse_mode="HTML",
    )
    await state.set_state(UploadStates.waiting_title)


# ── Step 2: Title ────────────────────────────────
@router.message(UploadStates.waiting_title, F.text)
async def on_title(message: Message, state: FSMContext, **kwargs):
    title = message.text.strip()[:200]
    await state.update_data(title=title)
    await message.answer(
        "2️⃣ Enter <b>tags</b> (comma separated):\n\n"
        "<i>Example: telegram, python, ai</i>",
        parse_mode="HTML",
    )
    await state.set_state(UploadStates.waiting_tags)


# ── Step 3: Tags ─────────────────────────────────
@router.message(UploadStates.waiting_tags, F.text)
async def on_tags(message: Message, state: FSMContext, **kwargs):
    from utils.validators import validate_tags
    tags = validate_tags(message.text)
    await state.update_data(tags=", ".join(tags))
    today = date.today().isoformat()
    await message.answer(
        f"3️⃣ Enter <b>creation date</b> (YYYY-MM-DD):\n\n"
        f"Default: <code>{today}</code>\n"
        f"Send <b>today</b> to use the default.",
        parse_mode="HTML",
    )
    await state.set_state(UploadStates.waiting_date)


# ── Step 4: Date ─────────────────────────────────
@router.message(UploadStates.waiting_date, F.text)
async def on_date(message: Message, state: FSMContext, **kwargs):
    from utils.validators import validate_date
    raw = message.text.strip()
    if raw.lower() == "today":
        creation_date = date.today().isoformat()
    else:
        creation_date = validate_date(raw)
        if not creation_date:
            await message.answer("❌ Invalid date format. Use <b>YYYY-MM-DD</b> or type <b>today</b>.", parse_mode="HTML")
            return
    await state.update_data(creation_date=creation_date)
    await message.answer(
        "4️⃣ Select project <b>status</b>:",
        reply_markup=status_selection_kb(),
        parse_mode="HTML",
    )
    await state.set_state(UploadStates.waiting_status)


# ── Step 5: Status ───────────────────────────────
@router.callback_query(UploadStates.waiting_status, F.data.startswith("status:"))
async def on_status(cb: CallbackQuery, state: FSMContext, **kwargs):
    status = cb.data.split(":")[1]
    await state.update_data(status=status)
    await cb.message.edit_text(
        "5️⃣ Send a <b>GitHub repository URL</b> (optional).\n\n"
        "Type <b>skip</b> to skip.",
        parse_mode="HTML",
    )
    await state.set_state(UploadStates.waiting_github)
    await cb.answer()


# ── Step 6: GitHub URL ───────────────────────────
@router.message(UploadStates.waiting_github, F.text)
async def on_github(message: Message, state: FSMContext, **kwargs):
    raw = message.text.strip()
    github_url = None if raw.lower() == "skip" else raw
    await state.update_data(github_repo=github_url)

    data = await state.get_data()
    status_emoji = {"complete": "✅", "incomplete": "⚠️", "experimental": "🧪", "wip": "🚧"}.get(data["status"], "📦")

    text = (
        f"{SEP}\n📦 <b>Confirm Upload</b>\n{SEP}\n\n"
        f"<b>Title:</b> {data['title']}\n"
        f"<b>Tags:</b> {data.get('tags', '—')}\n"
        f"<b>Date:</b> {data.get('creation_date', '—')}\n"
        f"<b>Status:</b> {status_emoji} {data['status'].title()}\n"
        f"<b>GitHub:</b> {data.get('github_repo') or '—'}\n"
    )
    await message.answer(text, reply_markup=confirm_upload_kb(), parse_mode="HTML")
    await state.set_state(UploadStates.confirming)


# ── Confirm ──────────────────────────────────────
@router.callback_query(UploadStates.confirming, F.data == "upload_confirm")
async def on_confirm(cb: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    data = await state.get_data()

    project = Project(
        title=data["title"],
        tags=data.get("tags", ""),
        creation_date=data.get("creation_date", ""),
        status=data["status"],
        file_path=data["file_path"],
        github_repo=data.get("github_repo"),
    )
    session.add(project)
    session.add(Activity(action="upload", project_id=project.id, user_id=cb.from_user.id))
    await session.commit()

    await state.clear()
    await cb.message.edit_text(
        f"✅ <b>Project saved!</b>\n\n📦 {project.title}",
        reply_markup=admin_dashboard_kb(),
        parse_mode="HTML",
    )
    await cb.answer("✅ Saved!")


# ── Cancel ───────────────────────────────────────
@router.callback_query(UploadStates.confirming, F.data == "upload_cancel")
async def on_cancel(cb: CallbackQuery, state: FSMContext, **kwargs):
    data = await state.get_data()
    # Clean up the file if it was already saved
    if "file_path" in data:
        from services.file_manager import delete_file
        await delete_file(data["file_path"])
    await state.clear()
    await cb.message.edit_text(
        "❌ Upload cancelled.",
        reply_markup=admin_dashboard_kb(),
        parse_mode="HTML",
    )
    await cb.answer()
