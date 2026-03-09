"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Loads environment variables and exposes
application-wide constants.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env from project root
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded once at startup."""

    # ── Telegram ──────────────────────────────────
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "CodeVaultBot")

    # ── OpenAI ────────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ── Paths ─────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    FILES_DIR: Path = DATA_DIR / "files"
    DB_PATH: Path = DATA_DIR / "vault.db"

    # ── Limits ────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    PREVIEW_MAX_CHARS: int = 3500          # Telegram message limit safety
    RATE_LIMIT_PER_MINUTE: int = 10        # Downloads per user per minute

    # ── Branding ──────────────────────────────────
    ADMIN_NAME: str = "Krish"
    ADMIN_TG: str = "@northframe"
    ATTRIBUTION: str = "Shared via Krish's Code Vault — @northframe"

    # ── UI separators ─────────────────────────────
    SEP: str = "━━━━━━━━━━━━━━"

    def validate(self) -> None:
        """Raise on missing critical env vars."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not set in .env")
        if not self.ADMIN_ID:
            raise ValueError("ADMIN_ID is not set in .env")


settings = Settings()
