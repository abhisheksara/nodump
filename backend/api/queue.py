from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Story, UserStoryState

router = APIRouter(prefix="/queue", tags=["queue"])

USER_ID = "me"


class StoryOut(BaseModel):
    id: str
    title: str
    url: str
    author: str
    published_at: datetime
    source_id: int
    summary: str
    why_matters: str
    what_to_do: str
    relevance_label: str | None
    relevance_score: float | None
    domain: str
    sub_domain: str | None
    triage_label: str | None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[StoryOut])
def get_queue(
    domain: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    q = (
        db.query(Story)
        .outerjoin(
            UserStoryState,
            (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == USER_ID),
        )
        .filter(
            Story.relevance_label.in_(["high", "medium"]),
            Story.processed_at.isnot(None),
            Story.published_at >= cutoff,
            UserStoryState.story_id.is_(None),
        )
    )
    if domain:
        q = q.filter(Story.sub_domain == domain)

    return q.order_by(Story.relevance_score.desc()).limit(5).all()
