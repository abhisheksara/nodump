from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from config import settings
        _engine = create_engine(settings.database_url)
    return _engine


def _get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())
    return _SessionLocal


def get_db():
    db = _get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from db import models  # noqa: F401 — ensure models registered
    Base.metadata.create_all(bind=_get_engine())


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
