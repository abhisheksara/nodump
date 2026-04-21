import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from config import settings
from db.models import Source, Story
from ingestion.dedup import is_duplicate
from processing.extractor import extract_arxiv_content, extract_hn_content
from processing.llm import enrich, triage
from processing.runlog import RunLogger

logger = logging.getLogger(__name__)


def process_and_store(db: Session, raw_items: list[dict], source: Source) -> dict:
    """Dedup → triage → extract → enrich → store. Returns stats dict."""
    stats = {"total": len(raw_items), "duplicate": 0, "ignored": 0, "stored": 0, "failed": 0}
    run_log = RunLogger()

    for item in raw_items:
        item.setdefault("source_name", source.name)

        if is_duplicate(db, source.id, item["external_id"], item["url"]):
            stats["duplicate"] += 1
            run_log.record(item, action="skipped_duplicate")
            continue

        try:
            triaged = triage(item)
        except Exception as exc:
            logger.error("Triage error for '%s': %s", item.get("title"), exc)
            stats["failed"] += 1
            run_log.record(item, action="triage_failed", error=str(exc))
            continue

        if triaged["triage_label"] == "ignore":
            stats["ignored"] += 1
            run_log.record(triaged, action="dropped_ignore")
            continue

        if source.name == "arxiv":
            extracted = extract_arxiv_content(
                item["external_id"], fallback=item.get("raw_content", "")
            )
        else:
            extracted = extract_hn_content(
                item["url"], item.get("hn_item_id", item["external_id"])
            ) or item.get("raw_content", "")

        context_used = {
            "source": source.name,
            "title": item["title"],
            "extracted_content": extracted[:3000],
        }

        try:
            enriched = enrich(triaged, extracted)
        except Exception as exc:
            logger.error("Enrich error for '%s': %s", item.get("title"), exc)
            stats["failed"] += 1
            run_log.record(triaged, action="enrich_failed", error=str(exc))
            continue

        story_id = f"{source.id}:{item['external_id']}"
        story = Story(
            id=story_id,
            source_id=source.id,
            external_id=item["external_id"],
            url=item["url"],
            title=item["title"],
            raw_content=item.get("raw_content", "")[:2000],
            author=item.get("author", ""),
            published_at=item["published_at"],
            triage_label=triaged["triage_label"],
            triage_score=triaged.get("triage_score"),
            context_used=context_used,
            summary=enriched.get("summary", ""),
            why_matters=enriched.get("why_matters", ""),
            what_to_do=enriched.get("what_to_do", ""),
            relevance_label=enriched.get("relevance_label"),
            relevance_score=enriched.get("relevance_score"),
            domain="ai_ml",
            sub_domain=enriched.get("sub_domain") or triaged.get("sub_domain"),
            llm_model=enriched.get("llm_model"),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(story)
        try:
            db.commit()
            stats["stored"] += 1
            run_log.record(enriched, action="stored")
        except Exception as exc:
            db.rollback()
            logger.error("DB store failed for '%s': %s", item.get("title"), exc)
            stats["failed"] += 1
            run_log.record(enriched, action="store_failed", error=str(exc))

    run_log.save(settings.runs_dir)
    logger.info("Pipeline done for %s: %s", source.name, stats)
    return stats
