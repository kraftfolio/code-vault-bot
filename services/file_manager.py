"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — File Manager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Save and retrieve uploaded project files.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles

from bot.config import settings
from utils.validators import sanitize_filename
from utils.security import is_safe_path


async def save_uploaded_file(file_bytes: bytes, original_name: str) -> str:
    """
    Save raw bytes to ``data/files/<uuid>_<sanitized>.zip``.
    Returns the relative path from project root.
    """
    settings.FILES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(original_name)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    dest = settings.FILES_DIR / unique_name

    async with aiofiles.open(dest, "wb") as f:
        await f.write(file_bytes)

    # Store relative path in DB
    return str(dest.relative_to(settings.BASE_DIR))


def get_absolute_path(relative_path: str) -> Path | None:
    """
    Convert a DB-stored relative path to an absolute one.
    Returns None if the path is unsafe or doesn't exist.
    """
    full = settings.BASE_DIR / relative_path
    if not is_safe_path(full):
        return None
    if not full.exists():
        return None
    return full


async def delete_file(relative_path: str) -> bool:
    """Delete a file from disk. Returns True on success."""
    full = get_absolute_path(relative_path)
    if full and full.exists():
        full.unlink()
        return True
    return False
