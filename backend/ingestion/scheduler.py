import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_source(source_name: str):
    from db.database import SessionLocal, seed_sources
    from db.models import Source
    from processing.pipeline import process_and_store

    if source_name == "arxiv":
        from ingestion.arxiv import fetch_arxiv_papers as fetcher
    else:
        from ingestion.hn import fetch_hn_stories as fetcher

    db = SessionLocal()
    try:
        seed_sources(db)
        source = db.query(Source).filter_by(name=source_name, active=True).first()
        if not source:
            logger.info("%s source inactive or missing, skipping", source_name)
            return
        items = fetcher(source.id)
        process_and_store(db, items, source)
    except Exception as exc:
        logger.error("%s ingestion failed: %s", source_name, exc)
    finally:
        db.close()


def _send_nudge():
    from db.database import SessionLocal
    from delivery.email import send_nudge

    db = SessionLocal()
    try:
        send_nudge(db)
    except Exception as exc:
        logger.error("Nudge failed: %s", exc)
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(lambda: _run_source("arxiv"), "interval", hours=6, id="fetch_arxiv")
    _scheduler.add_job(lambda: _run_source("hackernews"), "interval", hours=2, id="fetch_hn")
    _scheduler.add_job(
        _send_nudge, "cron",
        hour=settings.nudge_hour, minute=settings.nudge_minute,
        id="send_nudge",
    )
    _scheduler.start()
    logger.info("Scheduler started (arxiv 6h, hn 2h, nudge daily %02d:%02d)",
                settings.nudge_hour, settings.nudge_minute)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
