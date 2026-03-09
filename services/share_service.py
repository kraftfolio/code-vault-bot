"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — Share Service
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create, validate, and revoke share tokens.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Project
from utils.security import generate_share_token


async def create_share_link(session: AsyncSession, project_id: str) -> str:
    """
    Generate a unique share token for the project.
    Returns the token string (e.g. ``file_k92Js8f3PqL``).
    """
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    # Reuse existing token if present
    if project.share_token:
        return project.share_token

    token = generate_share_token()
    project.share_token = token
    await session.commit()
    return token


async def resolve_token(session: AsyncSession, token: str) -> Project | None:
    """Look up a project by share token. Returns None if invalid."""
    result = await session.execute(
        select(Project).where(Project.share_token == token)
    )
    return result.scalar_one_or_none()


async def revoke_share(session: AsyncSession, project_id: str) -> bool:
    """Remove the share token from a project."""
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project and project.share_token:
        project.share_token = None
        await session.commit()
        return True
    return False


async def list_shared_projects(session: AsyncSession, offset: int = 0, limit: int = 10):
    """Return projects that currently have a share token."""
    result = await session.execute(
        select(Project)
        .where(Project.share_token.isnot(None))
        .order_by(Project.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()
