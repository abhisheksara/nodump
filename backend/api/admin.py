"""Admin API — stats, scheduler status, run logs, and manual triggers."""
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db
from db.models import NudgeLog, Source, Story, UserStoryState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class AdminStats(BaseModel):
    total_stories: int
    stories_last_24h: int
    stories_last_7d: int
    by_relevance: dict[str, int]
    by_sub_domain: dict[str, int]
    by_source: dict[str, int]
    user_states: dict[str, int]
    unread_high: int


@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    total = db.query(func.count(Story.id)).scalar() or 0

    stories_24h = (
        db.query(func.count(Story.id))
        .filter(Story.fetched_at >= now - timedelta(hours=24))
        .scalar() or 0
    )
    stories_7d = (
        db.query(func.count(Story.id))
        .filter(Story.fetched_at >= now - timedelta(days=7))
        .scalar() or 0
    )

    relevance_rows = (
        db.query(Story.relevance_label, func.count(Story.id))
        .group_by(Story.relevance_label)
        .all()
    )
    by_relevance = {(r or "none"): c for r, c in relevance_rows}

    domain_rows = (
        db.query(Story.sub_domain, func.count(Story.id))
        .group_by(Story.sub_domain)
        .all()
    )
    by_sub_domain = {(d or "none"): c for d, c in domain_rows}

    source_rows = (
        db.query(Source.name, func.count(Story.id))
        .join(Story, Story.source_id == Source.id)
        .group_by(Source.name)
        .all()
    )
    by_source = {name: c for name, c in source_rows}

    state_rows = (
        db.query(UserStoryState.state, func.count(UserStoryState.story_id))
        .group_by(UserStoryState.state)
        .all()
    )
    user_states = {s: c for s, c in state_rows}

    interacted_ids = db.query(UserStoryState.story_id).subquery()
    unread_high = (
        db.query(func.count(Story.id))
        .filter(
            Story.relevance_label == "high",
            Story.id.not_in(select(interacted_ids)),
        )
        .scalar() or 0
    )

    return AdminStats(
        total_stories=total,
        stories_last_24h=stories_24h,
        stories_last_7d=stories_7d,
        by_relevance=by_relevance,
        by_sub_domain=by_sub_domain,
        by_source=by_source,
        user_states=user_states,
        unread_high=unread_high,
    )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class SchedulerJob(BaseModel):
    id: str
    next_run_time: str | None
    trigger: str


@router.get("/scheduler", response_model=list[SchedulerJob])
def get_scheduler():
    from ingestion.scheduler import _scheduler

    if not _scheduler or not _scheduler.running:
        return []

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append(SchedulerJob(
            id=job.id,
            next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
            trigger=str(job.trigger),
        ))
    return jobs


# ---------------------------------------------------------------------------
# Run logs
# ---------------------------------------------------------------------------

class RunFile(BaseModel):
    filename: str
    timestamp: str
    size_bytes: int


class RunEntry(BaseModel):
    ts: str | None = None
    action: str | None = None
    title: str | None = None
    url: str | None = None
    triage_label: str | None = None
    relevance_label: str | None = None
    relevance_score: float | None = None
    sub_domain: str | None = None
    error: str | None = None


@router.get("/runs", response_model=list[RunFile])
def list_runs():
    runs_dir = Path(settings.runs_dir)
    if not runs_dir.exists():
        return []

    files = sorted(runs_dir.glob("*.jsonl"), reverse=True)[:50]
    result = []
    for f in files:
        stat = f.stat()
        result.append(RunFile(
            filename=f.name,
            timestamp=f.stem,
            size_bytes=stat.st_size,
        ))
    return result


@router.get("/runs/{filename}", response_model=list[RunEntry])
def get_run(filename: str):
    if "/" in filename or "\\" in filename or not filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = Path(settings.runs_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    entries = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    entries.append(RunEntry(**{k: data.get(k) for k in RunEntry.model_fields}))
                except Exception:
                    pass
    return entries


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------

class TriggerResult(BaseModel):
    status: str


def _bg(target, *args):
    threading.Thread(target=target, args=args, daemon=True).start()


@router.post("/trigger/ingestion", response_model=TriggerResult)
def trigger_all():
    from ingestion.scheduler import _run_source
    _bg(_run_source, "arxiv")
    _bg(_run_source, "hackernews")
    return TriggerResult(status="started")


@router.post("/trigger/ingestion/{source_name}", response_model=TriggerResult)
def trigger_source(source_name: str):
    if source_name not in ("arxiv", "hackernews"):
        raise HTTPException(status_code=400, detail="Unknown source. Use 'arxiv' or 'hackernews'")
    from ingestion.scheduler import _run_source
    _bg(_run_source, source_name)
    return TriggerResult(status="started")


@router.post("/trigger/nudge", response_model=TriggerResult)
def trigger_nudge():
    from ingestion.scheduler import _send_nudge
    _bg(_send_nudge)
    return TriggerResult(status="started")


# ---------------------------------------------------------------------------
# Nudge history
# ---------------------------------------------------------------------------

class NudgeLogEntry(BaseModel):
    id: int
    sent_at: datetime
    stories_count: int
    top_story_id: str | None


@router.get("/nudge-logs", response_model=list[NudgeLogEntry])
def get_nudge_logs(db: Session = Depends(get_db)):
    logs = db.query(NudgeLog).order_by(NudgeLog.sent_at.desc()).limit(50).all()
    return [
        NudgeLogEntry(
            id=log.id,
            sent_at=log.sent_at,
            stories_count=log.stories_count,
            top_story_id=log.top_story_id,
        )
        for log in logs
    ]
