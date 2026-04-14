"""Orchestrates dedup → LLM enrichment → DB storage."""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from db.models import ContentItem
from processing.llm import enrich_item

logger = logging.getLogger(__name__)


def process_and_store(db: Session, raw_items: list[dict]) -> int:
    """Deduplicate, enrich with LLM, and persist new items. Returns count stored."""
    stored = 0
    for item in raw_items:
        # Deduplicate by id
        existing = db.get(ContentItem, item["id"])
        if existing:
            continue

        try:
            enriched = enrich_item(item)
        except Exception as exc:
            logger.error("Enrichment error for %s: %s", item.get("id"), exc)
            enriched = item
            enriched.setdefault("summary", "")
            enriched.setdefault("why_it_matters", "")
            enriched.setdefault("relevance_score", 0.0)

        record = ContentItem(
            id=enriched["id"],
            title=enriched["title"],
            content=enriched["content"],
            source=enriched["source"],
            url=enriched["url"],
            author=enriched.get("author", ""),
            published_at=enriched.get("published_at") or datetime.utcnow(),
            summary=enriched.get("summary", ""),
            why_it_matters=enriched.get("why_it_matters", ""),
            relevance_score=enriched.get("relevance_score", 0.0),
            processed=True,
        )
        db.add(record)
        stored += 1

    db.commit()
    logger.info("Stored %d new items", stored)
    return stored
