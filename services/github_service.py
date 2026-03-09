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
    m = _GH_PATTERN.search(url.strip().rstrip("/").removesuffix(".git"))
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
    Download a public GitHub repo as a ZIP via the GitHub API,
    then re-package it with a clean folder structure into FILES_DIR.
    No ``git`` CLI required.
    """
    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    tmp_dir = Path(tempfile.mkdtemp())
    logger.info("[clone_and_zip] Starting download for %s/%s from %s", owner, repo, zip_url)
    print(f"[DEBUG] clone_and_zip: downloading {zip_url}")

    try:
        # Download the ZIP archive from GitHub API
        async with aiohttp.ClientSession() as cs:
            async with cs.get(
                zip_url,
                timeout=aiohttp.ClientTimeout(total=120),
                headers={"Accept": "application/vnd.github+json"},
                allow_redirects=True,
            ) as resp:
                logger.info("[clone_and_zip] Response status: %s", resp.status)
                print(f"[DEBUG] clone_and_zip: response status = {resp.status}")
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(
                        "GitHub ZIP download failed (HTTP %s) for %s/%s — body: %s",
                        resp.status, owner, repo, body[:500],
                    )
                    print(f"[DEBUG] clone_and_zip FAILED: HTTP {resp.status}, body={body[:500]}")
                    return None

                # Stream to a temp file
                tmp_zip = tmp_dir / "download.zip"
                with open(tmp_zip, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
                print(f"[DEBUG] clone_and_zip: downloaded {tmp_zip.stat().st_size} bytes")

        # Extract, then re-zip with a clean directory name
        extract_dir = tmp_dir / "extracted"
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(extract_dir)

        # GitHub wraps everything in a folder like "owner-repo-sha/"
        top_dirs = list(extract_dir.iterdir())
        repo_dir = top_dirs[0] if len(top_dirs) == 1 and top_dirs[0].is_dir() else extract_dir

        settings.FILES_DIR.mkdir(parents=True, exist_ok=True)
        zip_name = f"{uuid.uuid4().hex[:8]}_{repo}.zip"
        zip_path = settings.FILES_DIR / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in repo_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(repo_dir))

        logger.info("[clone_and_zip] Success! ZIP at %s (%d bytes)", zip_path, zip_path.stat().st_size)
        print(f"[DEBUG] clone_and_zip: SUCCESS -> {zip_path}")
        return zip_path

    except asyncio.TimeoutError:
        logger.error("GitHub ZIP download timed out for %s/%s", owner, repo)
        return None
    except Exception as exc:
        logger.error("clone_and_zip error: %s", exc, exc_info=True)
        print(f"[DEBUG] clone_and_zip EXCEPTION: {exc}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
