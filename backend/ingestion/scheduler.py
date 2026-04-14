"""APScheduler job that fetches and processes new content periodically."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_ingestion():
    """Fetch new content, deduplicate, and run LLM processing."""
    from db.database import SessionLocal
    from ingestion.arxiv import fetch_arxiv_papers
    from ingestion.rss import fetch_rss_feeds
    from processing.pipeline import process_and_store

    logger.info("Starting ingestion run...")
    db = SessionLocal()
    try:
        items = fetch_arxiv_papers() + fetch_rss_feeds()
        process_and_store(db, items)
    except Exception as exc:
        logger.error("Ingestion run failed: %s", exc)
    finally:
        db.close()
    logger.info("Ingestion run complete.")


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_ingestion,
        trigger="interval",
        hours=settings.fetch_interval_hours,
        id="ingestion",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — interval: %dh", settings.fetch_interval_hours)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
