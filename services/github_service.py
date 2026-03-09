"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — GitHub Service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fetch repo metadata & clone-to-zip.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

# Pattern to extract owner/repo from GitHub URL
_GH_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/\s?#]+)", re.IGNORECASE
)


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL. Returns None on failure."""
    m = _GH_PATTERN.search(url.strip().rstrip("/").rstrip(".git"))
    if m:
        return m.group(1), m.group(2).removesuffix(".git")
    return None


async def fetch_repo_metadata(owner: str, repo: str) -> dict | None:
    """Hit the GitHub REST API to get repo metadata (no auth required for public repos)."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return {
                    "name": data.get("name", repo),
                    "description": data.get("description", ""),
                    "stars": data.get("stargazers_count", 0),
                    "language": data.get("language", "Unknown"),
                    "html_url": data.get("html_url", ""),
                }
    except Exception as exc:
        logger.warning("GitHub API error: %s", exc)
        return None


async def clone_and_zip(owner: str, repo: str) -> Path | None:
    """
    Clone a public GitHub repo into a temp dir, zip it, then
    move the zip into FILES_DIR.
    Requires ``git`` on the host.
    """
    clone_url = f"https://github.com/{owner}/{repo}.git"
    tmp_dir = Path(tempfile.mkdtemp())

    try:
        # Shallow clone via subprocess (non-blocking)
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", clone_url, str(tmp_dir / repo),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.error("git clone failed: %s", stderr.decode())
            return None

        # Zip the cloned dir
        settings.FILES_DIR.mkdir(parents=True, exist_ok=True)
        zip_name = f"{uuid.uuid4().hex[:8]}_{repo}.zip"
        zip_path = settings.FILES_DIR / zip_name

        repo_dir = tmp_dir / repo
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in repo_dir.rglob("*"):
                if ".git" in file.parts:
                    continue
                if file.is_file():
                    zf.write(file, file.relative_to(repo_dir))

        return zip_path

    except asyncio.TimeoutError:
        logger.error("Git clone timed out for %s/%s", owner, repo)
        return None
    except Exception as exc:
        logger.error("clone_and_zip error: %s", exc)
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
