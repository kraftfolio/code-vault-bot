"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Preview Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extract key files from a ZIP and produce
syntax-highlighted code snippets for Telegram.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter  # noqa — kept for reference
from pygments.lexers import get_lexer_for_filename, TextLexer

from bot.config import settings

logger = logging.getLogger(__name__)

# Files we prefer to preview
_PRIORITY_NAMES = [
    "README.md", "README.txt", "readme.md",
    "main.py", "app.py", "index.py",
    "index.js", "index.ts", "app.js",
    "server.py", "bot.py", "manage.py",
    "Dockerfile", "docker-compose.yml",
    "package.json", "requirements.txt",
]

_MAX_PREVIEW = settings.PREVIEW_MAX_CHARS


def _pick_files(zf: zipfile.ZipFile, limit: int = 3) -> list[str]:
    """Pick the most interesting files to preview."""
    names = [n for n in zf.namelist() if not zf.getinfo(n).is_dir()]
    chosen: list[str] = []

    # Priority files first
    for pname in _PRIORITY_NAMES:
        for n in names:
            if n.endswith(pname) and n not in chosen:
                chosen.append(n)
                if len(chosen) >= limit:
                    return chosen

    # Fill remaining slots with small text files
    for n in names:
        if n in chosen:
            continue
        info = zf.getinfo(n)
        ext = Path(n).suffix.lower()
        if ext in {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".sh", ".yml", ".yaml", ".toml", ".json", ".md", ".txt", ".html", ".css"}:
            if info.file_size < 30_000:
                chosen.append(n)
                if len(chosen) >= limit:
                    return chosen

    return chosen


def generate_preview(zip_path: Path) -> str:
    """
    Return a Telegram-ready preview string with code snippets.
    Uses <code> blocks (HTML parse mode).
    """
    if not zip_path.exists():
        return "❌ File not found on disk."

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            chosen = _pick_files(zf)
            if not chosen:
                return "👁 <b>Preview</b>\n\nNo previewable files found in archive."

            parts: list[str] = ["👁 <b>Code Preview</b>\n"]
            remaining = _MAX_PREVIEW

            for name in chosen:
                if remaining <= 0:
                    break
                try:
                    raw = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue

                snippet = raw[: min(800, remaining)]
                # Escape HTML entities for Telegram
                snippet = (
                    snippet.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                short_name = Path(name).name
                part = f"\n📄 <b>{short_name}</b>\n<pre>{snippet}</pre>"
                parts.append(part)
                remaining -= len(part)

            return "\n".join(parts)

    except zipfile.BadZipFile:
        return "❌ Corrupt or invalid ZIP file."
    except Exception as exc:
        logger.error("Preview generation failed: %s", exc)
        return "❌ Preview generation failed."
