from ingestion.hn import _parse_hits

HN_HITS_FIXTURE = [
    {
        "objectID": "12345",
        "title": "Show HN: New LLM framework",
        "url": "https://example.com/llm",
        "points": 250,
        "author": "user1",
        "created_at": "2026-04-22T08:00:00.000Z",
    },
    {
        "objectID": "99999",
        "title": "Ask HN: something unrelated",
        "url": None,
        "points": 150,
        "author": "user2",
        "created_at": "2026-04-22T07:00:00.000Z",
    },
]


def test_parse_hits_returns_correct_shape():
    items = _parse_hits(HN_HITS_FIXTURE, source_id=2)
    assert len(items) == 2
    assert items[0]["external_id"] == "12345"
    assert items[0]["source_id"] == 2
    assert items[0]["url"] == "https://example.com/llm"
    assert items[1]["url"] == "https://news.ycombinator.com/item?id=99999"


def test_parse_hits_has_required_keys():
    items = _parse_hits(HN_HITS_FIXTURE, source_id=2)
    required = {"source_id", "external_id", "url", "title", "raw_content", "author", "published_at", "source_name"}
    for item in items:
        assert required.issubset(item.keys())
