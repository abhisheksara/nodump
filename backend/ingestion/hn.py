import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

HN_ALGOLIA_URL = (
    "https://hn.algolia.com/api/v1/search"
    "?tags=story&numericFilters=points%3E100&hitsPerPage=60"
)


def _parse_hits(hits: list[dict], source_id: int) -> list[dict]:
    items = []
    for hit in hits:
        hn_id = hit.get("objectID", "")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"
        try:
            published_at = datetime.fromisoformat(
                hit["created_at"].replace("Z", "+00:00")
            )
        except (KeyError, ValueError):
            published_at = datetime.now(timezone.utc)

        items.append({
            "source_id": source_id,
            "external_id": hn_id,
            "url": url,
            "title": hit.get("title", ""),
            "raw_content": hit.get("title", ""),
            "author": hit.get("author", ""),
            "published_at": published_at,
            "source_name": "hackernews",
            "hn_item_id": hn_id,
        })
    return items


def fetch_hn_stories(source_id: int) -> list[dict]:
    """Fetch HN stories with score > 100 from Algolia API."""
    try:
        resp = httpx.get(HN_ALGOLIA_URL, timeout=15.0)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        items = _parse_hits(hits, source_id)
        logger.info("HN: fetched %d stories", len(items))
        return items
    except Exception as exc:
        logger.error("HN fetch failed: %s", exc)
        return []
