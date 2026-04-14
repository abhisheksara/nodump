"""Fetch recent papers from arXiv cs.AI and cs.LG."""
import hashlib
import logging
from datetime import datetime, timezone

import arxiv

logger = logging.getLogger(__name__)

CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]
MAX_RESULTS_PER_CATEGORY = 20


def fetch_arxiv_papers() -> list[dict]:
    """Return normalized content items from arXiv."""
    items: list[dict] = []
    seen_ids: set[str] = set()

    client = arxiv.Client()

    for category in CATEGORIES:
        try:
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=MAX_RESULTS_PER_CATEGORY,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/")[-1]
                item_id = f"arxiv_{arxiv_id}"
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                abstract = result.summary.replace("\n", " ").strip()
                items.append(
                    {
                        "id": item_id,
                        "title": result.title,
                        "content": abstract,
                        "source": "arxiv",
                        "url": result.entry_id,
                        "author": ", ".join(a.name for a in result.authors[:3]),
                        "published_at": result.published or datetime.now(timezone.utc),
                    }
                )
        except Exception as exc:
            logger.error("arXiv fetch failed for %s: %s", category, exc)

    logger.info("arXiv: fetched %d papers", len(items))
    return items
