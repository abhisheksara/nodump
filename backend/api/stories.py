from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.queue import StoryOut, USER_ID
from db.database import get_db
from db.models import Story, UserStoryState

router = APIRouter(prefix="/stories", tags=["stories"])


def _set_state(story_id: str, state: str, db: Session) -> dict:
    if not db.get(Story, story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    existing = db.get(UserStoryState, (USER_ID, story_id))
    if existing:
        existing.state = state
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(UserStoryState(user_id=USER_ID, story_id=story_id, state=state,
                              updated_at=datetime.now(timezone.utc)))
    db.commit()
    return {"ok": True}


@router.post("/{story_id}/read")
def mark_read(story_id: str, db: Session = Depends(get_db)):
    return _set_state(story_id, "read", db)


@router.post("/{story_id}/skip")
def mark_skip(story_id: str, db: Session = Depends(get_db)):
    return _set_state(story_id, "skipped", db)


@router.post("/{story_id}/save")
def mark_save(story_id: str, db: Session = Depends(get_db)):
    return _set_state(story_id, "saved", db)


@router.get("/saved", response_model=list[StoryOut])
def get_saved(db: Session = Depends(get_db)):
    return (
        db.query(Story)
        .join(UserStoryState,
              (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == USER_ID))
        .filter(UserStoryState.state == "saved")
        .order_by(UserStoryState.updated_at.desc())
        .all()
    )


@router.get("/history", response_model=list[StoryOut])
def get_history(q: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = (
        db.query(Story)
        .join(UserStoryState,
              (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == USER_ID))
        .filter(UserStoryState.state.in_(["read", "skipped"]))
    )
    if q:
        query = query.filter(Story.title.ilike(f"%{q}%"))
    return query.order_by(UserStoryState.updated_at.desc()).limit(100).all()
