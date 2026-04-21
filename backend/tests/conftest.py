import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base
from db.models import Source


@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add_all([
        Source(name="arxiv", kind="api", tags=[], fetch_interval_mins=360),
        Source(name="hackernews", kind="api", tags=[], fetch_interval_mins=120),
    ])
    session.commit()

    yield session
    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def arxiv_source(db):
    return db.query(Source).filter_by(name="arxiv").first()


@pytest.fixture(scope="function")
def hn_source(db):
    return db.query(Source).filter_by(name="hackernews").first()
