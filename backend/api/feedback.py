"""Feedback endpoints — thumbs up / down per item."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import UserFeedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    user_id: str = "default"
    item_id: str
    feedback: str  # "up" | "down"


@router.post("/")
def submit_feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    if body.feedback not in ("up", "down"):
        raise HTTPException(status_code=422, detail="feedback must be 'up' or 'down'")

    existing = db.execute(
        select(UserFeedback).where(
            UserFeedback.user_id == body.user_id,
            UserFeedback.item_id == body.item_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.feedback = body.feedback
    else:
        db.add(UserFeedback(user_id=body.user_id, item_id=body.item_id, feedback=body.feedback))

    db.commit()
    return {"status": "ok"}


@router.delete("/")
def remove_feedback(user_id: str, item_id: str, db: Session = Depends(get_db)):
    existing = db.execute(
        select(UserFeedback).where(
            UserFeedback.user_id == user_id,
            UserFeedback.item_id == item_id,
        )
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        db.commit()
    return {"status": "ok"}
