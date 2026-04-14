from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50))  # arxiv | twitter | blog
    url: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # LLM-enriched fields
    summary: Mapped[str] = mapped_column(Text, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    processed: Mapped[bool] = mapped_column(default=False)


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_item"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255))
    item_id: Mapped[str] = mapped_column(String(255))
    feedback: Mapped[str] = mapped_column(String(10))  # up | down
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
