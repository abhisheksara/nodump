from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from db.models import Story, UserStoryState


@pytest.fixture
def client(db):
    import main as main_module
    from db.database import get_db

    def override():
        yield db

    main_module.app.dependency_overrides[get_db] = override
    # skip scheduler/init_db on startup for tests
    with TestClient(main_module.app, raise_server_exceptions=True) as c:
        yield c
    main_module.app.dependency_overrides.clear()


def _add_story(db, source, ext_id, score, label="high", days_ago=0, sub="agents"):
    now = datetime.now(timezone.utc)
    s = Story(
        id=f"{source.id}:{ext_id}",
        source_id=source.id,
        external_id=ext_id,
        url=f"http://example.com/{ext_id}",
        title=f"Story {ext_id}",
        published_at=now - timedelta(days=days_ago),
        relevance_label=label,
        relevance_score=score,
        processed_at=now,
        domain="ai_ml",
        sub_domain=sub,
    )
    db.add(s)
    db.commit()
    return s


def test_queue_returns_up_to_5(client, db, arxiv_source):
    for i in range(7):
        _add_story(db, arxiv_source, f"p{i}", score=float(i) / 7)
    resp = client.get("/queue/")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_queue_ordered_by_score(client, db, arxiv_source):
    _add_story(db, arxiv_source, "low", score=0.3)
    _add_story(db, arxiv_source, "high", score=0.9)
    _add_story(db, arxiv_source, "mid", score=0.6)
    resp = client.get("/queue/")
    scores = [s["relevance_score"] for s in resp.json()]
    assert scores == sorted(scores, reverse=True)


def test_queue_excludes_read_stories(client, db, arxiv_source):
    s = _add_story(db, arxiv_source, "read_me", score=0.99)
    db.add(UserStoryState(user_id="me", story_id=s.id, state="read"))
    db.commit()
    resp = client.get("/queue/")
    ids = [x["id"] for x in resp.json()]
    assert s.id not in ids


def test_queue_domain_filter(client, db, arxiv_source):
    _add_story(db, arxiv_source, "a1", score=0.9, sub="agents")
    _add_story(db, arxiv_source, "l1", score=0.8, sub="llms")
    resp = client.get("/queue/?domain=agents")
    assert all(s["sub_domain"] == "agents" for s in resp.json())


def test_queue_excludes_old_stories(client, db, arxiv_source):
    _add_story(db, arxiv_source, "old", score=0.99, days_ago=31)
    resp = client.get("/queue/")
    assert len(resp.json()) == 0
