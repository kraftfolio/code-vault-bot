"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Validators
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Input validation & filename sanitization.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from bot.config import settings


def sanitize_filename(name: str) -> str:
    """Strip dangerous characters, keep letters/digits/dots/underscores/hyphens."""
    name = PurePosixPath(name).name          # remove directory parts
    name = re.sub(r"[^\w.\-]", "_", name)    # safe chars only
    return name[:120] or "unnamed"


def validate_zip_filename(filename: str | None) -> bool:
    """Return True if the filename ends with .zip (case-insensitive)."""
    if not filename:
        return False
    return filename.lower().endswith(".zip")


def validate_file_size(size: int | None) -> bool:
    """Check that the file size is within the configured limit."""
    if size is None:
        return False
    return 0 < size <= settings.MAX_FILE_SIZE_BYTES


def validate_tags(raw: str) -> list[str]:
    """Parse comma-separated tags string into a clean list."""
    tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return tags[:20]  # cap at 20 tags

def validate_date(raw: str) -> str | None:
    """
    Accept dates in YYYY-MM-DD format.
    Returns the date string or None if invalid.
    """
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    return raw.strip() if re.match(pattern, raw.strip()) else None
