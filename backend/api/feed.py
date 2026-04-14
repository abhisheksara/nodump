"""Feed endpoints — returns ranked top-N items for the day."""
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db
from db.models import ContentItem, UserFeedback

router = APIRouter(prefix="/feed", tags=["feed"])


class FeedItemResponse(BaseModel):
    id: str
    title: str
    summary: str
    why_it_matters: str
    source: str
    url: str
    author: str
    published_at: datetime
    relevance_score: float
    user_feedback: str | None = None  # "up" | "down" | None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[FeedItemResponse])
def get_feed(
    user_id: str = Query(default="default"),
    source: str | None = Query(default=None, description="Filter by source: arxiv|blog"),
    days: int = Query(default=3, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Return top-N ranked items, optionally filtered by source and recency."""
    since = datetime.utcnow() - timedelta(days=days)

    stmt = select(ContentItem).where(
        ContentItem.processed == True,  # noqa: E712
        ContentItem.published_at >= since,
    )
    if source:
        stmt = stmt.where(ContentItem.source == source)

    items = db.execute(stmt).scalars().all()

    # Fetch user feedback for these items
    item_ids = [i.id for i in items]
    feedback_rows = (
        db.execute(
            select(UserFeedback).where(
                UserFeedback.user_id == user_id,
                UserFeedback.item_id.in_(item_ids),
            )
        )
        .scalars()
        .all()
    )
    feedback_map = {f.item_id: f.feedback for f in feedback_rows}

    # Rank: penalise downvoted items, boost upvoted
    def rank_score(item: ContentItem) -> float:
        base = item.relevance_score
        fb = feedback_map.get(item.id)
        if fb == "up":
            base = min(base + 0.15, 1.0)
        elif fb == "down":
            base = max(base - 0.3, 0.0)
        return base

    ranked = sorted(items, key=rank_score, reverse=True)[: settings.feed_limit]

    return [
        FeedItemResponse(
            **{c.key: getattr(item, c.key) for c in ContentItem.__table__.columns},
            user_feedback=feedback_map.get(item.id),
        )
        for item in ranked
    ]


@router.post("/refresh")
def trigger_refresh(db: Session = Depends(get_db)):
    """Manually trigger an ingestion run (useful for dev/demo)."""
    from ingestion.arxiv import fetch_arxiv_papers
    from ingestion.rss import fetch_rss_feeds
    from processing.pipeline import process_and_store

    items = fetch_arxiv_papers() + fetch_rss_feeds()
    count = process_and_store(db, items)
    return {"stored": count}
