"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Search Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ranked text search across project metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Project


@dataclass
class SearchResult:
    project: Project
    score: float


class SearchEngine:
    """Simple ranked search — matches query words against title, tags, status, creation_date."""

    @staticmethod
    async def search(
        session: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> list[SearchResult]:
        """
        Score every project against the query and return the top ``limit`` matches.

        Scoring:
        - Title exact containment → +3
        - Tag match               → +2 per matching tag
        - Status match            → +1
        - Date match              → +1
        """
        result = await session.execute(select(Project).order_by(Project.uploaded_at.desc()))
        projects = result.scalars().all()

        query_lower = query.lower().strip()
        words = query_lower.split()
        scored: list[SearchResult] = []

        for p in projects:
            score = 0.0
            title_l = (p.title or "").lower()
            tags_l = (p.tags or "").lower()
            status_l = (p.status or "").lower()
            date_l = (p.creation_date or "").lower()

            for w in words:
                if w in title_l:
                    score += 3.0
                if w in tags_l:
                    score += 2.0
                if w in status_l:
                    score += 1.0
                if w in date_l:
                    score += 1.0

            # Boost pinned / favourite
            if p.pinned:
                score += 0.5
            if p.favorite:
                score += 0.3

            if score > 0:
                scored.append(SearchResult(project=p, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]
