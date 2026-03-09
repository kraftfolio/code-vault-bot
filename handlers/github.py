"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — GitHub Handler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Import projects directly from GitHub.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.models import Activity, Project
from keyboards.admin_menu import admin_dashboard_kb, back_to_dashboard_kb
from services.github_service import clone_and_zip, fetch_repo_metadata, parse_github_url

logger = logging.getLogger(__name__)
router = Router(name="github")
SEP = settings.SEP


class GitHubStates(StatesGroup):
    waiting_url = State()


@router.callback_query(F.data == "github_import")
async def cb_github_start(cb: CallbackQuery, is_admin: bool, state: FSMContext, **kwargs):
    if not is_admin:
        await cb.answer("⛔ Access denied", show_alert=True)
        return
    await state.set_state(GitHubStates.waiting_url)
    await cb.message.edit_text(
        f"{SEP}\n🌐 <b>Import from GitHub</b>\n{SEP}\n\n"
        "Send a public GitHub repository URL.\n\n"
        "<i>Example: https://github.com/user/repo</i>",
        parse_mode="HTML",
    )
    await cb.answer()


@router.message(GitHubStates.waiting_url, F.text)
async def on_github_url(message: Message, is_admin: bool, state: FSMContext, session, **kwargs):
    if not is_admin:
        return

    parsed = parse_github_url(message.text)
    if not parsed:
        await message.answer("❌ Invalid GitHub URL. Please send a valid repository URL.", parse_mode="HTML")
        return

    owner, repo = parsed
    await message.answer(f"⏳ Fetching repository info for <b>{owner}/{repo}</b>…", parse_mode="HTML")

    # Fetch metadata
    meta = await fetch_repo_metadata(owner, repo)

    await message.answer(f"📥 Cloning repository… this may take a moment.")

    # Clone & zip
    zip_path = await clone_and_zip(owner, repo)
    if not zip_path:
        await state.clear()
        await message.answer(
            "❌ Failed to download the repository.\n\n"
            "Make sure the repo is <b>public</b> and the URL is correct.",
            reply_markup=back_to_dashboard_kb(),
            parse_mode="HTML",
        )
        return

    # Store as project
    relative_path = str(zip_path.relative_to(settings.BASE_DIR))
    project = Project(
        title=meta["name"] if meta else repo,
        tags=meta.get("language", "").lower() if meta else "",
        creation_date="",
        status="complete",
        file_path=relative_path,
        github_repo=f"https://github.com/{owner}/{repo}",
    )
    session.add(project)
    session.add(Activity(action="upload", project_id=project.id, user_id=message.from_user.id))
    await session.commit()
    await state.clear()

    # Show result
    desc = meta.get("description", "") if meta else ""
    stars = meta.get("stars", 0) if meta else 0
    lang = meta.get("language", "Unknown") if meta else "Unknown"

    text = (
        f"{SEP}\n✅ <b>GitHub Import Complete</b>\n{SEP}\n\n"
        f"📦 <b>{project.title}</b>\n"
        f"⭐ Stars: {stars}\n"
        f"💻 Language: {lang}\n"
    )
    if desc:
        text += f"📝 {desc}\n"

    await message.answer(text, reply_markup=admin_dashboard_kb(), parse_mode="HTML")
