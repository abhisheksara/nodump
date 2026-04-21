from datetime import datetime, timezone

from db.models import Story
from ingestion.dedup import is_duplicate


def _make_story(db, source, ext_id, url):
    s = Story(
        id=f"{source.id}:{ext_id}",
        source_id=source.id,
        external_id=ext_id,
        url=url,
        title="Test",
        published_at=datetime.now(timezone.utc),
    )
    db.add(s)
    db.commit()
    return s


def test_new_story_not_duplicate(db, arxiv_source):
    assert is_duplicate(db, arxiv_source.id, "ext001", "http://example.com/1") is False


def test_duplicate_by_external_id(db, arxiv_source):
    _make_story(db, arxiv_source, "ext001", "http://example.com/1")
    assert is_duplicate(db, arxiv_source.id, "ext001", "http://example.com/2") is True


def test_duplicate_by_url(db, arxiv_source):
    _make_story(db, arxiv_source, "ext001", "http://example.com/shared")
    assert is_duplicate(db, arxiv_source.id, "ext999", "http://example.com/shared") is True


def test_different_source_same_ext_id_not_duplicate(db, arxiv_source, hn_source):
    _make_story(db, arxiv_source, "ext001", "http://arxiv.com/1")
    assert is_duplicate(db, hn_source.id, "ext001", "http://hn.com/1") is False
