"""Feed endpoint — returns today's top-3 ranked items."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db
from db.models import ContentItem

router = APIRouter(prefix="/feed", tags=["feed"])


class FeedItemResponse(BaseModel):
    id: str
    title: str
    summary: str
    why_it_matters: str
    what_to_do: str
    relevance_label: str
    source: str
    url: str
    author: str
    published_at: datetime
    relevance_score: float

    class Config:
        from_attributes = True


@router.get("/", response_model=list[FeedItemResponse])
def get_feed(
    days: int = Query(default=1, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Return today's top-3 items, excluding 'ignore' labels, ranked by score."""
    since = datetime.utcnow() - timedelta(days=days)

    stmt = select(ContentItem).where(
        ContentItem.processed == True,  # noqa: E712
        ContentItem.published_at >= since,
        ContentItem.relevance_label != "ignore",
    )
    items = db.execute(stmt).scalars().all()
    ranked = sorted(items, key=lambda i: i.relevance_score, reverse=True)[: settings.feed_limit]

    return [
        FeedItemResponse(**{c.key: getattr(item, c.key) for c in ContentItem.__table__.columns})
        for item in ranked
    ]


@router.post("/refresh")
def trigger_refresh(db: Session = Depends(get_db)):
    """Manually trigger an ingestion + digest run."""
    from ingestion.arxiv import fetch_arxiv_papers
    from processing.pipeline import process_and_store

    items = fetch_arxiv_papers()
    count = process_and_store(db, items)
    return {"stored": count}
