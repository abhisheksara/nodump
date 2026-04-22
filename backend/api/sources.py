from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Source

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceOut(BaseModel):
    id: int
    name: str
    kind: str
    active: bool
    fetch_interval_mins: int
    last_fetched_at: str | None

    class Config:
        from_attributes = True


class SourcePatch(BaseModel):
    active: bool


@router.get("/", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()


@router.patch("/{source_id}", response_model=SourceOut)
def toggle_source(source_id: int, body: SourcePatch, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.active = body.active
    db.commit()
    db.refresh(source)
    return source
