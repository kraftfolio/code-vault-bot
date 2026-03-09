"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Security Utils
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token generation and path-traversal
guard utilities.
"""

from __future__ import annotations

import secrets
import string
from pathlib import Path

from bot.config import settings


def generate_share_token(length: int = 12) -> str:
    """
    Generate a URL-safe random token prefixed with ``file_``.

    Example output: ``file_k92Js8f3PqL7``
    """
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"file_{random_part}"


def is_safe_path(requested_path: str | Path) -> bool:
    """
    Return True only if *requested_path* resolves inside FILES_DIR.
    Prevents path-traversal attacks.
    """
    try:
        resolved = Path(requested_path).resolve()
        return str(resolved).startswith(str(settings.FILES_DIR.resolve()))
    except (ValueError, OSError):
        return False
