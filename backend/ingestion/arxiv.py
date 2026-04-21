import logging
from datetime import datetime, timezone

import arxiv

logger = logging.getLogger(__name__)

CATEGORIES = ["cs.AI", "cs.LG", "cs.CL"]
MAX_RESULTS_PER_CATEGORY = 25


def fetch_arxiv_papers(source_id: int) -> list[dict]:
    """Return raw story dicts for pipeline. external_id = arxiv paper ID."""
    items: list[dict] = []
    seen: set[str] = set()
    client = arxiv.Client()

    for category in CATEGORIES:
        try:
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=MAX_RESULTS_PER_CATEGORY,
                sort_by=arxiv.SortCriterion.SubmittedDate,
            )
            for result in client.results(search):
                arxiv_id = result.entry_id.split("/")[-1].split("v")[0]
                if arxiv_id in seen:
                    continue
                seen.add(arxiv_id)
                items.append({
                    "source_id": source_id,
                    "external_id": arxiv_id,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "title": result.title.strip(),
                    "raw_content": result.summary.replace("\n", " ").strip(),
                    "author": ", ".join(a.name for a in result.authors[:3]),
                    "published_at": result.published or datetime.now(timezone.utc),
                    "source_name": "arxiv",
                })
        except Exception as exc:
            logger.error("arXiv fetch failed for %s: %s", category, exc)

    logger.info("arXiv: fetched %d papers", len(items))
    return items
