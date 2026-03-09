"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KRISH CODE VAULT — ORM Models
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SQLAlchemy declarative models for
Project, User, and Activity tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Base ──────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Project ───────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="")               # comma-separated
    creation_date: Mapped[str] = mapped_column(String(20), default="")  # user-supplied date
    status: Mapped[str] = mapped_column(String(30), default="complete")
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    github_repo: Mapped[str | None] = mapped_column(Text, default=None)
    ai_summary: Mapped[str | None] = mapped_column(Text, default=None)
    share_token: Mapped[str | None] = mapped_column(String(20), unique=True, default=None)
    downloads_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def status_emoji(self) -> str:
        return {
            "complete": "✅",
            "incomplete": "⚠️",
            "experimental": "🧪",
            "wip": "🚧",
        }.get(self.status, "📦")

    def card_text(self) -> str:
        """Render a beautiful project card."""
        sep = "━━━━━━━━━━━━━━"
        lines = [
            sep,
            f"📦 <b>{self.title}</b>",
            sep,
            "",
            f"Status: {self.status_emoji()} {self.status.title()}",
        ]
        if self.tags:
            lines.append(f"Tags: {self.tags}")
        if self.creation_date:
            lines.append(f"Created: {self.creation_date}")
        lines.append(f"Downloads: {self.downloads_count}")
        if self.github_repo:
            lines.append(f"GitHub: {self.github_repo}")
        return "\n".join(lines)


# ── User ──────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ── Activity ─────────────────────────────────────
class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)  # upload/download/share/delete
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="SET NULL"), default=None
    )
    user_id: Mapped[int | None] = mapped_column(Integer, default=None)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project | None] = relationship(back_populates="activities")
