"""Fetch posts from curated RSS feeds (OpenAI, Anthropic, HuggingFace, etc.)."""
import hashlib
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"url": "https://openai.com/blog/rss.xml", "source": "blog", "author": "OpenAI"},
    {"url": "https://www.anthropic.com/rss.xml", "source": "blog", "author": "Anthropic"},
    {"url": "https://huggingface.co/blog/feed.xml", "source": "blog", "author": "HuggingFace"},
    {"url": "https://bair.berkeley.edu/blog/feed.xml", "source": "blog", "author": "BAIR"},
    {"url": "https://lilianweng.github.io/index.xml", "source": "blog", "author": "Lilian Weng"},
    {"url": "https://www.deepmind.com/blog/rss.xml", "source": "blog", "author": "DeepMind"},
]


def _parse_date(entry) -> datetime:
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                pass
    return datetime.utcnow()


def fetch_rss_feeds() -> list[dict]:
    """Return normalized content items from RSS feeds."""
    items: list[dict] = []

    for feed_cfg in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_cfg["url"])
            for entry in parsed.entries[:10]:
                url = entry.get("link", "")
                if not url:
                    continue
                item_id = "rss_" + hashlib.sha256(url.encode()).hexdigest()[:16]
                content = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                    or entry.get("title", "")
                )
                # Strip basic HTML tags
                import re
                content = re.sub(r"<[^>]+>", "", content).strip()

                items.append(
                    {
                        "id": item_id,
                        "title": entry.get("title", "Untitled"),
                        "content": content[:2000],
                        "source": feed_cfg["source"],
                        "url": url,
                        "author": entry.get("author", feed_cfg["author"]),
                        "published_at": _parse_date(entry),
                    }
                )
        except Exception as exc:
            logger.error("RSS fetch failed for %s: %s", feed_cfg["url"], exc)

    logger.info("RSS: fetched %d items", len(items))
    return items
