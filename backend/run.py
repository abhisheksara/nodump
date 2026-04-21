"""Manual ingestion trigger. Usage: python run.py (from backend/ dir)"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def run():
    from db.database import SessionLocal, init_db, seed_sources
    from db.models import Source
    from ingestion.arxiv import fetch_arxiv_papers
    from ingestion.hn import fetch_hn_stories
    from processing.pipeline import process_and_store

    init_db()
    db = SessionLocal()
    try:
        seed_sources(db)

        arxiv_src = db.query(Source).filter_by(name="arxiv", active=True).first()
        if arxiv_src:
            items = fetch_arxiv_papers(arxiv_src.id)
            stats = process_and_store(db, items, arxiv_src)
            logger.info("arXiv done: %s", stats)

        hn_src = db.query(Source).filter_by(name="hackernews", active=True).first()
        if hn_src:
            items = fetch_hn_stories(hn_src.id)
            stats = process_and_store(db, items, hn_src)
            logger.info("HN done: %s", stats)

    except Exception as exc:
        logger.error("Run failed: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()
