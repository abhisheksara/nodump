from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import Story


def is_duplicate(db: Session, source_id: int, external_id: str, url: str) -> bool:
    return db.query(Story).filter(
        or_(
            (Story.source_id == source_id) & (Story.external_id == external_id),
            Story.url == url,
        )
    ).first() is not None
