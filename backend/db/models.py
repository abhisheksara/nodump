from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # rss | api
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    authority_weight: Mapped[float] = mapped_column(Float, default=0.5)
    fetch_interval_mins: Mapped[int] = mapped_column(Integer, default=360)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    triage_label: Mapped[str | None] = mapped_column(String(10), nullable=True)
    triage_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    context_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    why_matters: Mapped[str] = mapped_column(Text, default="")
    what_to_do: Mapped[str] = mapped_column(Text, default="")
    relevance_label: Mapped[str | None] = mapped_column(String(10), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain: Mapped[str] = mapped_column(String(50), default="ai_ml")
    sub_domain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserStoryState(Base):
    __tablename__ = "user_story_state"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True, default="me")
    story_id: Mapped[str] = mapped_column(String(255), ForeignKey("stories.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(10), nullable=False)  # read | skipped | saved
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class NudgeLog(Base):
    __tablename__ = "nudge_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    stories_count: Mapped[int] = mapped_column(Integer, nullable=False)
    top_story_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("stories.id"), nullable=True)
