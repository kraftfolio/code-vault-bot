"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — AI Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate project summaries using an
OpenAI-compatible API.
"""

from __future__ import annotations

import logging
import zipfile
from io import BytesIO
from pathlib import Path

from bot.config import settings

logger = logging.getLogger(__name__)

# Key filenames to look for inside a zip
_KEY_FILES = [
    "README.md", "README.txt", "readme.md",
    "main.py", "app.py", "index.py", "server.py", "bot.py",
    "index.js", "index.ts", "app.js", "main.js",
    "Makefile", "Dockerfile", "docker-compose.yml",
    "setup.py", "pyproject.toml", "package.json",
    "requirements.txt",
]


def _extract_key_content(zip_path: Path, max_chars: int = 6000) -> str:
    """Extract text from key files inside a ZIP for AI analysis."""
    collected: list[str] = []
    total = 0

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            # Prioritise key files
            ordered = sorted(
                names,
                key=lambda n: next(
                    (i for i, kf in enumerate(_KEY_FILES) if n.endswith(kf)),
                    len(_KEY_FILES),
                ),
            )
            for name in ordered:
                if total >= max_chars:
                    break
                if zf.getinfo(name).file_size > 50_000:
                    continue
                if zf.getinfo(name).is_dir():
                    continue
                try:
                    raw = zf.read(name).decode("utf-8", errors="ignore")
                    snippet = raw[:max_chars - total]
                    collected.append(f"--- {name} ---\n{snippet}")
                    total += len(snippet)
                except Exception:
                    continue
    except zipfile.BadZipFile:
        return "(Could not read zip contents)"

    return "\n\n".join(collected) or "(No readable files found)"


async def generate_summary(zip_path: Path) -> str:
    """
    Call OpenAI to produce a structured project summary.
    Returns a formatted string ready to send in Telegram.
    """
    if not settings.OPENAI_API_KEY:
        return "🧠 <b>AI Summary unavailable</b>\n\nSet OPENAI_API_KEY in .env to enable this feature."

    code_context = _extract_key_content(zip_path)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=600,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior software engineer. Analyse the following source code "
                        "snippets and produce a concise project summary. Include:\n"
                        "• Project purpose (1-2 sentences)\n"
                        "• Main technologies/frameworks\n"
                        "• Key components/files\n"
                        "• Complexity level (Simple / Moderate / Complex)\n"
                        "Keep it under 200 words. Use plain text, no markdown headers."
                    ),
                },
                {"role": "user", "content": code_context},
            ],
        )

        summary_text = resp.choices[0].message.content or "No summary generated."
        return f"🧠 <b>AI Project Summary</b>\n\n{summary_text}"

    except Exception as exc:
        logger.error("AI summary failed: %s", exc)
        return f"🧠 <b>AI Summary</b>\n\n⚠️ Generation failed: {exc.__class__.__name__}"
