from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from db import models  # noqa: F401 — ensure models registered
    Base.metadata.create_all(bind=engine)


def seed_sources(db):
    from db.models import Source
    defaults = [
        Source(name="arxiv", kind="api", tags=["ai_ml", "research"],
               authority_weight=0.8, fetch_interval_mins=360),
        Source(name="hackernews", kind="api", tags=["ai_ml", "industry"],
               authority_weight=0.6, fetch_interval_mins=120),
    ]
    for src in defaults:
        if not db.query(Source).filter_by(name=src.name).first():
            db.add(src)
    db.commit()
