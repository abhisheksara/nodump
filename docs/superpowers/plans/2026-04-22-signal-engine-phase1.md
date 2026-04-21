# Signal Engine Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personal AI/ML signal engine — arXiv + HN ingestion, two-stage GPT-4o enrichment, rolling queue, Next.js dashboard, email nudge.

**Architecture:** APScheduler triggers arXiv (6h) and HN (2h) fetchers → two-stage GPT-4o pipeline (triage then deep enrich) → Postgres → FastAPI → Next.js dashboard. Single-user ("me"), no auth.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Postgres 15, OpenAI SDK (gpt-4o), trafilatura, BeautifulSoup4, Next.js 14 App Router, Tailwind CSS, shadcn/ui, APScheduler, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-04-22-signal-engine-phase1-design.md`

---

## Checkpoint A: Backend core working (`python -m backend.run` fetches + enriches stories)
## Checkpoint B: API + scheduler running (`docker-compose up` serves full backend)
## Checkpoint C: Dashboard live (`localhost:3000` shows queue)

---

## File Map

**Modify:**
- `backend/config.py` — swap anthropic→openai, add dashboard_url, nudge settings
- `backend/requirements.txt` — add openai/trafilatura/bs4/lxml, remove anthropic/numpy
- `backend/.env.example` — update keys
- `backend/db/models.py` — complete rewrite: Source, Story, UserStoryState, NudgeLog
- `backend/db/database.py` — minor: remove sqlite check_same_thread hack for prod
- `backend/ingestion/arxiv.py` — update to new Story schema, accept source_id param
- `backend/ingestion/scheduler.py` — two jobs (arxiv 6h, hn 2h) + nudge cron
- `backend/processing/pipeline.py` — two-stage orchestration
- `backend/processing/llm.py` — complete rewrite: OpenAI SDK, stage1 + stage2
- `backend/delivery/email.py` — rewrite as nudge (not digest)
- `backend/main.py` — register new routers, add CORS
- `docker-compose.yml` — add frontend service

**Create:**
- `backend/ingestion/hn.py` — HN Algolia fetcher
- `backend/ingestion/dedup.py` — dedup by (source_id, external_id) or url
- `backend/processing/extractor.py` — arXiv HTML parse + HN trafilatura + comments
- `backend/processing/runlog.py` — JSONL run logger
- `backend/api/queue.py` — GET /queue rolling queue endpoint
- `backend/api/stories.py` — POST read/skip/save, GET saved/history
- `backend/api/sources.py` — GET/PATCH sources
- `backend/run.py` — CLI manual trigger entry point
- `tests/conftest.py` — pytest fixtures
- `tests/test_dedup.py`
- `tests/test_llm.py`
- `tests/test_queue_api.py`
- `frontend/` — full Next.js 14 app (scaffold + components + pages)

**Delete:**
- `backend/api/feed.py` — replaced by queue.py

---

## Task 1: Config + requirements

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`

- [ ] **Step 1: Rewrite config.py**

```python
# backend/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    database_url: str = "postgresql://feed:feed@localhost:5432/research_feed"
    dashboard_url: str = "http://localhost:3000"

    nudge_hour: int = 7
    nudge_minute: int = 0
    nudge_min_stories: int = 3

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = "abhisheksara27@gmail.com"

    runs_dir: str = "./runs"
    runs_retention_days: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
```

- [ ] **Step 2: Rewrite requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
openai>=1.30.0
arxiv==2.1.0
httpx==0.27.0
trafilatura>=1.9.0
beautifulsoup4>=4.12.0
lxml>=5.2.0
apscheduler==3.10.4
python-dotenv==1.0.1
pydantic==2.7.1
pydantic-settings==2.2.1
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

- [ ] **Step 3: Update .env.example**

```
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://feed:feed@localhost:5432/research_feed
DASHBOARD_URL=http://localhost:3000

NUDGE_HOUR=7
NUDGE_MINUTE=0
NUDGE_MIN_STORIES=3

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_TO=abhisheksara27@gmail.com
```

- [ ] **Step 4: Verify import**

```bash
cd /home/abhisheksara/nodump/backend
python -c "from config import settings; print(settings.openai_api_key)"
```
Expected: empty string (or your key if .env set)

- [ ] **Step 5: Commit**

```bash
git add backend/config.py backend/requirements.txt backend/.env.example
git commit -m "feat: migrate config to openai, add nudge/runs settings"
```

---

## Task 2: DB models rewrite

**Files:**
- Modify: `backend/db/models.py`

- [ ] **Step 1: Rewrite models.py**

```python
# backend/db/models.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from db.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # rss | api
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    authority_weight: Mapped[float] = mapped_column(Float, default=0.5)
    fetch_interval_mins: Mapped[int] = mapped_column(Integer, default=360)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    triage_label: Mapped[str | None] = mapped_column(String(10), nullable=True)
    triage_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    context_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    why_matters: Mapped[str] = mapped_column(Text, default="")
    what_to_do: Mapped[str] = mapped_column(Text, default="")
    relevance_label: Mapped[str | None] = mapped_column(String(10), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain: Mapped[str] = mapped_column(String(50), default="ai_ml")
    sub_domain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserStoryState(Base):
    __tablename__ = "user_story_state"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True, default="me")
    story_id: Mapped[str] = mapped_column(String(255), ForeignKey("stories.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(10), nullable=False)  # read | skipped | saved
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class NudgeLog(Base):
    __tablename__ = "nudge_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    stories_count: Mapped[int] = mapped_column(Integer, nullable=False)
    top_story_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("stories.id"), nullable=True)
```

- [ ] **Step 2: Update database.py to remove sqlite-only connect_args**

```python
# backend/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import settings


engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def seed_sources(db):
    """Insert default sources if missing."""
    from db.models import Source
    defaults = [
        Source(name="arxiv", kind="api", tags=["ai_ml", "research"],
               authority_weight=0.8, fetch_interval_mins=360),
        Source(name="hackernews", kind="api", tags=["ai_ml", "industry"],
               authority_weight=0.6, fetch_interval_mins=120),
    ]
    for src in defaults:
        if not db.query(Source).filter_by(name=src.name).first():
            db.add(src)
    db.commit()
```

- [ ] **Step 3: Commit**

```bash
git add backend/db/models.py backend/db/database.py
git commit -m "feat: rewrite db models - Source, Story, UserStoryState, NudgeLog"
```

---

## Task 3: Pytest setup

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create conftest.py**

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from db.models import Source


@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    arxiv_src = Source(name="arxiv", kind="api", tags=[], fetch_interval_mins=360)
    hn_src = Source(name="hackernews", kind="api", tags=[], fetch_interval_mins=120)
    session.add_all([arxiv_src, hn_src])
    session.commit()

    yield session
    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def arxiv_source(db):
    return db.query(Source).filter_by(name="arxiv").first()


@pytest.fixture(scope="function")
def hn_source(db):
    return db.query(Source).filter_by(name="hackernews").first()
```

- [ ] **Step 2: Create empty __init__.py**

```bash
touch backend/tests/__init__.py
```

- [ ] **Step 3: Verify pytest runs**

```bash
cd backend && python -m pytest tests/ -v
```
Expected: `no tests ran` (0 errors)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "test: add pytest setup and db fixture"
```

---

## Task 4: Dedup module

**Files:**
- Create: `backend/ingestion/dedup.py`
- Create: `backend/tests/test_dedup.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_dedup.py
from datetime import datetime, timezone
from db.models import Story
from ingestion.dedup import is_duplicate


def _make_story(db, source, ext_id, url):
    s = Story(
        id=f"{source.id}:{ext_id}",
        source_id=source.id,
        external_id=ext_id,
        url=url,
        title="Test",
        published_at=datetime.now(timezone.utc),
    )
    db.add(s)
    db.commit()
    return s


def test_new_story_not_duplicate(db, arxiv_source):
    assert is_duplicate(db, arxiv_source.id, "ext001", "http://example.com/1") is False


def test_duplicate_by_external_id(db, arxiv_source):
    _make_story(db, arxiv_source, "ext001", "http://example.com/1")
    assert is_duplicate(db, arxiv_source.id, "ext001", "http://example.com/2") is True


def test_duplicate_by_url(db, arxiv_source):
    _make_story(db, arxiv_source, "ext001", "http://example.com/shared")
    assert is_duplicate(db, arxiv_source.id, "ext999", "http://example.com/shared") is True


def test_different_source_same_ext_id_not_duplicate(db, arxiv_source, hn_source):
    _make_story(db, arxiv_source, "ext001", "http://arxiv.com/1")
    assert is_duplicate(db, hn_source.id, "ext001", "http://hn.com/1") is False
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest tests/test_dedup.py -v
```
Expected: `ImportError: cannot import name 'is_duplicate'`

- [ ] **Step 3: Implement dedup.py**

```python
# backend/ingestion/dedup.py
from sqlalchemy import or_
from sqlalchemy.orm import Session
from db.models import Story


def is_duplicate(db: Session, source_id: int, external_id: str, url: str) -> bool:
    return db.query(Story).filter(
        or_(
            (Story.source_id == source_id) & (Story.external_id == external_id),
            Story.url == url,
        )
    ).first() is not None
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest tests/test_dedup.py -v
```
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/ingestion/dedup.py backend/tests/test_dedup.py
git commit -m "feat: add dedup module with url+external_id dedup"
```

---

## Task 5: arXiv fetcher update

**Files:**
- Modify: `backend/ingestion/arxiv.py`

- [ ] **Step 1: Rewrite arxiv.py to emit new Story schema**

```python
# backend/ingestion/arxiv.py
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
```

- [ ] **Step 2: Verify import**

```bash
cd backend && python -c "from ingestion.arxiv import fetch_arxiv_papers; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/ingestion/arxiv.py
git commit -m "feat: update arxiv fetcher to new story schema"
```

---

## Task 6: HN fetcher

**Files:**
- Create: `backend/ingestion/hn.py`
- Create: `backend/tests/test_hn_fetcher.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_hn_fetcher.py
from unittest.mock import MagicMock, patch
from ingestion.hn import fetch_hn_stories, _parse_hits


HN_HITS_FIXTURE = [
    {
        "objectID": "12345",
        "title": "Show HN: New LLM framework",
        "url": "https://example.com/llm",
        "points": 250,
        "author": "user1",
        "created_at": "2026-04-22T08:00:00.000Z",
    },
    {
        "objectID": "99999",
        "title": "Ask HN: something unrelated",
        "url": None,  # self-post, no URL
        "points": 150,
        "author": "user2",
        "created_at": "2026-04-22T07:00:00.000Z",
    },
]


def test_parse_hits_returns_correct_shape():
    items = _parse_hits(HN_HITS_FIXTURE, source_id=2)
    assert len(items) == 2
    assert items[0]["external_id"] == "12345"
    assert items[0]["source_id"] == 2
    assert items[0]["url"] == "https://example.com/llm"
    assert items[1]["url"] == "https://news.ycombinator.com/item?id=99999"


def test_parse_hits_has_required_keys():
    items = _parse_hits(HN_HITS_FIXTURE, source_id=2)
    required = {"source_id", "external_id", "url", "title", "raw_content", "author", "published_at", "source_name"}
    for item in items:
        assert required.issubset(item.keys())
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest tests/test_hn_fetcher.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement hn.py**

```python
# backend/ingestion/hn.py
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
            "raw_content": hit.get("title", ""),  # Stage 1 triage uses title only
            "author": hit.get("author", ""),
            "published_at": published_at,
            "source_name": "hackernews",
            "hn_item_id": hn_id,  # passed to extractor for comments
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest tests/test_hn_fetcher.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/ingestion/hn.py backend/tests/test_hn_fetcher.py
git commit -m "feat: add HN Algolia fetcher"
```

---

## Task 7: Content extractor

**Files:**
- Create: `backend/processing/extractor.py`
- Create: `backend/tests/test_extractor.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_extractor.py
from unittest.mock import patch, MagicMock
from processing.extractor import _parse_arxiv_sections, _strip_html


ARXIV_HTML_FIXTURE = """
<html><body>
<section id="S1">
  <h2>1 Introduction</h2>
  <p>This paper presents a novel approach to agent planning.</p>
  <p>We demonstrate improvements on standard benchmarks.</p>
</section>
<section id="S2">
  <h2>2 Related Work</h2>
  <p>Prior work includes many things.</p>
</section>
<section id="S5">
  <h2>5 Conclusion</h2>
  <p>We showed that adaptive planning reduces failures by 40%.</p>
</section>
</body></html>
"""


def test_parse_arxiv_sections_extracts_intro_and_conclusion():
    result = _parse_arxiv_sections(ARXIV_HTML_FIXTURE)
    assert "novel approach" in result
    assert "adaptive planning" in result
    assert "Related Work" not in result


def test_strip_html_removes_tags():
    result = _strip_html("<p>Hello <b>world</b></p>")
    assert result == "Hello world"
    assert "<" not in result
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest tests/test_extractor.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement extractor.py**

```python
# backend/processing/extractor.py
import logging

import httpx
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TARGET_SECTIONS = {"introduction", "conclusion", "abstract", "summary", "discussion"}


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)


def _parse_arxiv_sections(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    extracted = []
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        heading_text = heading.get_text().strip().lower()
        if any(kw in heading_text for kw in _TARGET_SECTIONS):
            parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ["h1", "h2", "h3", "h4"]:
                    break
                parts.append(sibling.get_text(separator=" ", strip=True))
            section_text = " ".join(parts)[:1500]
            if section_text:
                extracted.append(section_text)
    return "\n\n".join(extracted)[:3000]


def extract_arxiv_content(arxiv_id: str, fallback: str = "") -> str:
    """Fetch arXiv HTML and extract intro + conclusion. Falls back to abstract."""
    clean_id = arxiv_id.split("v")[0]
    url = f"https://arxiv.org/html/{clean_id}"
    try:
        resp = httpx.get(url, timeout=15.0, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return fallback
        result = _parse_arxiv_sections(resp.text)
        return result if result else fallback
    except Exception as exc:
        logger.warning("arXiv HTML fetch failed for %s: %s", arxiv_id, exc)
        return fallback


def _fetch_hn_comments(hn_item_id: str, limit: int = 5) -> list[str]:
    try:
        resp = httpx.get(
            f"https://hacker-news.firebaseio.com/v0/item/{hn_item_id}.json",
            timeout=10.0,
        )
        data = resp.json()
        kid_ids = (data.get("kids") or [])[:limit]
        comments = []
        for kid_id in kid_ids:
            cr = httpx.get(
                f"https://hacker-news.firebaseio.com/v0/item/{kid_id}.json",
                timeout=5.0,
            )
            kid = cr.json()
            text = kid.get("text", "")
            if text:
                comments.append(_strip_html(text)[:300])
        return comments
    except Exception as exc:
        logger.warning("HN comments fetch failed for %s: %s", hn_item_id, exc)
        return []


def extract_hn_content(story_url: str, hn_item_id: str) -> str:
    """Extract article body via trafilatura + top 5 HN comments."""
    article_body = ""
    if story_url and "news.ycombinator.com" not in story_url:
        try:
            downloaded = trafilatura.fetch_url(story_url)
            if downloaded:
                article_body = (trafilatura.extract(downloaded) or "")[:2000]
        except Exception as exc:
            logger.warning("trafilatura failed for %s: %s", story_url, exc)

    comments = _fetch_hn_comments(hn_item_id)

    parts = []
    if article_body:
        parts.append(f"Article:\n{article_body}")
    if comments:
        parts.append("What HN says:\n" + "\n".join(f"- {c}" for c in comments))
    return "\n\n".join(parts)
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd backend && python -m pytest tests/test_extractor.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/processing/extractor.py backend/tests/test_extractor.py
git commit -m "feat: add content extractor for arxiv HTML and HN article+comments"
```

---

## Task 8: LLM two-stage pipeline

**Files:**
- Modify: `backend/processing/llm.py`
- Create: `backend/tests/test_llm.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_llm.py
import json
from unittest.mock import MagicMock, patch, call

import pytest


def _mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def mock_openai():
    with patch("processing.llm._get_client") as mock_get:
        client = MagicMock()
        mock_get.return_value = client
        yield client


def test_triage_high_label(mock_openai):
    from processing.llm import triage
    mock_openai.chat.completions.create.return_value = _mock_response(
        '{"triage_label": "high", "triage_score": 0.92, "sub_domain": "agents"}'
    )
    item = {"title": "Agent paper", "raw_content": "abstract here", "url": "http://x.com"}
    result = triage(item)
    assert result["triage_label"] == "high"
    assert result["triage_score"] == 0.92
    assert result["sub_domain"] == "agents"


def test_triage_retries_on_bad_json(mock_openai):
    from processing.llm import triage
    mock_openai.chat.completions.create.side_effect = [
        _mock_response("not json at all {{{"),
        _mock_response('{"triage_label": "medium", "triage_score": 0.5, "sub_domain": "llms"}'),
    ]
    item = {"title": "Test", "raw_content": "abstract", "url": "http://x.com"}
    result = triage(item)
    assert result["triage_label"] == "medium"
    assert mock_openai.chat.completions.create.call_count == 2


def test_triage_fallback_after_two_failures(mock_openai):
    from processing.llm import triage
    mock_openai.chat.completions.create.side_effect = [
        _mock_response("bad"),
        _mock_response("also bad"),
    ]
    item = {"title": "Test", "raw_content": "abstract", "url": "http://x.com"}
    result = triage(item)
    assert result["triage_label"] == "medium"
    assert result["triage_score"] == 0.3


def test_enrich_returns_all_fields(mock_openai):
    from processing.llm import enrich
    mock_openai.chat.completions.create.return_value = _mock_response(json.dumps({
        "summary": "A paper about agents.",
        "why_matters": "Reduces failure rate by 40%.",
        "what_to_do": "Try integrating this backoff into your agent loop.",
        "relevance_label": "high",
        "relevance_score": 0.88,
    }))
    item = {"title": "Agent paper", "triage_label": "high", "sub_domain": "agents", "url": "http://x.com"}
    result = enrich(item, "intro text here")
    assert result["summary"] == "A paper about agents."
    assert result["what_to_do"].startswith("Try")
    assert result["relevance_label"] == "high"
    assert result["llm_model"] == "gpt-4o"


def test_enrich_normalizes_bad_label(mock_openai):
    from processing.llm import enrich
    mock_openai.chat.completions.create.return_value = _mock_response(json.dumps({
        "summary": "s", "why_matters": "w", "what_to_do": "t",
        "relevance_label": "INVALID", "relevance_score": 0.5,
    }))
    item = {"title": "T", "sub_domain": "llms", "url": "http://x.com"}
    result = enrich(item, "content")
    assert result["relevance_label"] == "medium"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest tests/test_llm.py -v
```
Expected: `ImportError` or test failures

- [ ] **Step 3: Rewrite llm.py**

```python
# backend/processing/llm.py
import json
import logging

from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


_SYSTEM_PROMPT = """You are a ruthless AI/ML signal filter for Abhishek — Senior Data Scientist \
obsessed with LLMs, agents, multi-agent systems, applied ML, inference/efficiency, and building \
AI systems faster.

Your job: filter AI/ML content ruthlessly. Surface only what will make Abhishek think \
"I should try this today." Drop everything else.

PERSONA:
- Abhishek builds and deploys LLM-powered applications, agent systems, and ML pipelines
- He cares about: practical engineering, latency/cost tradeoffs, novel architectures that are \
actually implementable, new tools that change how you build
- He does NOT care about: hype with no substance, incremental benchmark improvements, papers \
that won't matter in 6 months, anything theoretical with no path to production

SUB-DOMAINS (pick exactly one):
- llms: LLM architectures, training, fine-tuning, prompting, RAG, RLHF, model releases
- agents: agent frameworks, multi-agent systems, planning, tool use, memory, orchestration
- applied_ml: ML engineering, MLOps, data pipelines, evaluation frameworks, production systems
- infra_inference: inference optimization, quantization, serving, hardware, latency, cost
- other: does not fit above clearly

QUALITY BAR for what_to_do:
BAD: "This is relevant to your interest in LLMs." — useless
BAD: "Worth reading if you work with transformers." — vague
GOOD: "Try replacing your agent's retry logic with this paper's adaptive backoff — run it on \
your eval harness this week."
GOOD: "Benchmark this quantization scheme against your current INT8 baseline — the latency \
numbers matter for your serving costs."

RULES:
- what_to_do must start with an imperative verb: Try / Test / Benchmark / Implement / Apply / \
Fork / Read / Skip
- what_to_do must name a concrete artifact or action target
- If no actionable angle: relevance_label = "medium", what_to_do starts with "Read — "
- If purely theoretical, no near-term application: triage_label = "ignore"
- relevance_label "high" = act this week
- relevance_label "medium" = worth knowing, no urgency
- Output ONLY valid JSON. No markdown, no explanation."""


_TRIAGE_TEMPLATE = """\
Source: {source}
Title: {title}
Content: {content}

JSON only:
{{"triage_label": "<high|medium|ignore>", "triage_score": <0.0-1.0>, \
"sub_domain": "<llms|agents|applied_ml|infra_inference|other>"}}"""


_ENRICH_TEMPLATE = """\
Source: {source}
Title: {title}
Sub-domain: {sub_domain}

Content:
{content}

JSON only:
{{"summary": "<2-3 sentences: what + result>", \
"why_matters": "<2 sentences: specific impact for LLM/agent/applied-ML work>", \
"what_to_do": "<one imperative sentence: concrete action this week>", \
"relevance_label": "<high|medium>", \
"relevance_score": <0.0-1.0>}}"""


def _call(prompt: str) -> dict:
    client = _get_client()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=600,
    )
    return json.loads(resp.choices[0].message.content.strip())


def triage(item: dict) -> dict:
    """Stage 1: classify label + score + sub_domain. Retries once on parse error."""
    prompt = _TRIAGE_TEMPLATE.format(
        source=item.get("source_name", ""),
        title=item["title"],
        content=item.get("raw_content", "")[:1000],
    )
    for attempt in range(2):
        try:
            result = _call(prompt)
            label = result.get("triage_label", "medium")
            if label not in ("high", "medium", "ignore"):
                label = "medium"
            return {
                **item,
                "triage_label": label,
                "triage_score": float(result.get("triage_score", 0.5)),
                "sub_domain": result.get("sub_domain", "other"),
            }
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            if attempt == 1:
                logger.warning("Triage failed for '%s': %s", item.get("title"), exc)
                return {**item, "triage_label": "medium", "triage_score": 0.3, "sub_domain": "other"}


def enrich(item: dict, extracted_content: str) -> dict:
    """Stage 2: summary, why_matters, what_to_do. Retries once on parse error."""
    prompt = _ENRICH_TEMPLATE.format(
        source=item.get("source_name", ""),
        title=item["title"],
        sub_domain=item.get("sub_domain", "other"),
        content=extracted_content[:3000],
    )
    for attempt in range(2):
        try:
            result = _call(prompt)
            label = result.get("relevance_label", "medium")
            if label not in ("high", "medium"):
                label = "medium"
            return {
                **item,
                "summary": str(result.get("summary", ""))[:800],
                "why_matters": str(result.get("why_matters", ""))[:500],
                "what_to_do": str(result.get("what_to_do", ""))[:300],
                "relevance_label": label,
                "relevance_score": float(result.get("relevance_score", 0.5)),
                "llm_model": "gpt-4o",
            }
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            if attempt == 1:
                logger.warning("Enrich failed for '%s': %s", item.get("title"), exc)
                return {
                    **item,
                    "summary": item.get("raw_content", "")[:400],
                    "why_matters": "",
                    "what_to_do": "",
                    "relevance_label": "medium",
                    "relevance_score": 0.3,
                    "llm_model": "gpt-4o",
                }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_llm.py -v
```
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/processing/llm.py backend/tests/test_llm.py
git commit -m "feat: two-stage LLM pipeline with gpt-4o, retry on parse error"
```

---

## Task 9: Run logger

**Files:**
- Create: `backend/processing/runlog.py`

- [ ] **Step 1: Implement runlog.py**

```python
# backend/processing/runlog.py
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class RunLogger:
    def __init__(self):
        self._entries: list[dict] = []

    def record(self, item: dict, action: str, **extra) -> None:
        self._entries.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "triage_label": item.get("triage_label"),
            "relevance_label": item.get("relevance_label"),
            "relevance_score": item.get("relevance_score"),
            "sub_domain": item.get("sub_domain"),
            **extra,
        })

    def save(self, runs_dir: str) -> Path:
        path = Path(runs_dir)
        path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
        filepath = path / f"{ts}.jsonl"
        with filepath.open("w") as f:
            for entry in self._entries:
                f.write(json.dumps(entry, default=str) + "\n")
        logger.info("Run log: %s (%d entries)", filepath, len(self._entries))
        return filepath
```

- [ ] **Step 2: Commit**

```bash
git add backend/processing/runlog.py
git commit -m "feat: add JSONL run logger for pipeline audit trail"
```

---

## Task 10: Pipeline orchestrator

**Files:**
- Modify: `backend/processing/pipeline.py`

- [ ] **Step 1: Rewrite pipeline.py**

```python
# backend/processing/pipeline.py
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/processing/pipeline.py
git commit -m "feat: pipeline orchestrator with two-stage LLM and run logging"
```

---

## Task 11: Manual run entry point (Checkpoint A)

**Files:**
- Create: `backend/run.py`

- [ ] **Step 1: Create run.py**

```python
# backend/run.py
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
```

- [ ] **Step 2: Start Postgres and run**

```bash
docker-compose up db -d
cd backend && OPENAI_API_KEY=your_key python run.py
```
Expected: logs show arXiv and HN fetching, pipeline stats. Check `./runs/` for JSONL file.

- [ ] **Step 3: Verify stories in DB**

```bash
docker exec -it $(docker-compose ps -q db) psql -U feed -d research_feed \
  -c "SELECT title, relevance_label, sub_domain FROM stories LIMIT 5;"
```
Expected: rows with titles, labels, sub_domains populated.

- [ ] **Step 4: Commit**

```bash
git add backend/run.py
git commit -m "feat: add manual run entry point — checkpoint A complete"
```

---

## Task 12: API — queue endpoint

**Files:**
- Create: `backend/api/queue.py`
- Create: `backend/tests/test_queue_api.py`
- Delete: `backend/api/feed.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_queue_api.py
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base, get_db
from db.models import Source, Story, UserStoryState


@pytest.fixture
def client(db):
    from main import app
    from db.database import get_db as original_get_db

    def override():
        yield db

    app.dependency_overrides[original_get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _add_story(db, source, ext_id, score, label="high", days_ago=0, sub="agents"):
    now = datetime.now(timezone.utc)
    s = Story(
        id=f"{source.id}:{ext_id}",
        source_id=source.id,
        external_id=ext_id,
        url=f"http://example.com/{ext_id}",
        title=f"Story {ext_id}",
        published_at=now - timedelta(days=days_ago),
        relevance_label=label,
        relevance_score=score,
        processed_at=now,
        domain="ai_ml",
        sub_domain=sub,
    )
    db.add(s)
    db.commit()
    return s


def test_queue_returns_up_to_5(client, db, arxiv_source):
    for i in range(7):
        _add_story(db, arxiv_source, f"p{i}", score=float(i) / 7)
    resp = client.get("/queue/")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


def test_queue_ordered_by_score(client, db, arxiv_source):
    _add_story(db, arxiv_source, "low", score=0.3)
    _add_story(db, arxiv_source, "high", score=0.9)
    _add_story(db, arxiv_source, "mid", score=0.6)
    resp = client.get("/queue/")
    scores = [s["relevance_score"] for s in resp.json()]
    assert scores == sorted(scores, reverse=True)


def test_queue_excludes_read_stories(client, db, arxiv_source):
    s = _add_story(db, arxiv_source, "read_me", score=0.99)
    db.add(UserStoryState(user_id="me", story_id=s.id, state="read"))
    db.commit()
    resp = client.get("/queue/")
    ids = [x["id"] for x in resp.json()]
    assert s.id not in ids


def test_queue_domain_filter(client, db, arxiv_source):
    _add_story(db, arxiv_source, "a1", score=0.9, sub="agents")
    _add_story(db, arxiv_source, "l1", score=0.8, sub="llms")
    resp = client.get("/queue/?domain=agents")
    assert all(s["sub_domain"] == "agents" for s in resp.json())


def test_queue_excludes_old_stories(client, db, arxiv_source):
    _add_story(db, arxiv_source, "old", score=0.99, days_ago=31)
    resp = client.get("/queue/")
    assert len(resp.json()) == 0
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd backend && python -m pytest tests/test_queue_api.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create queue.py**

```python
# backend/api/queue.py
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Story, UserStoryState

router = APIRouter(prefix="/queue", tags=["queue"])

USER_ID = "me"


class StoryOut(BaseModel):
    id: str
    title: str
    url: str
    author: str
    published_at: datetime
    source_id: int
    summary: str
    why_matters: str
    what_to_do: str
    relevance_label: str | None
    relevance_score: float | None
    domain: str
    sub_domain: str | None
    triage_label: str | None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[StoryOut])
def get_queue(
    domain: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    q = (
        db.query(Story)
        .outerjoin(
            UserStoryState,
            (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == USER_ID),
        )
        .filter(
            Story.relevance_label.in_(["high", "medium"]),
            Story.processed_at.isnot(None),
            Story.published_at >= cutoff,
            UserStoryState.story_id.is_(None),
        )
    )
    if domain:
        q = q.filter(Story.sub_domain == domain)

    return q.order_by(Story.relevance_score.desc()).limit(5).all()
```

- [ ] **Step 4: Update main.py temporarily to test**

```python
# backend/main.py (minimal version for testing)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.queue import router as queue_router
from db.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(title="Signal Engine", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(queue_router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/test_queue_api.py -v
```
Expected: `5 passed`

- [ ] **Step 6: Delete old feed.py**

```bash
rm backend/api/feed.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/api/queue.py backend/tests/test_queue_api.py backend/main.py
git rm backend/api/feed.py
git commit -m "feat: rolling queue API with 30-day window and domain filter"
```

---

## Task 13: API — story actions (read/skip/save, saved, history)

**Files:**
- Create: `backend/api/stories.py`

- [ ] **Step 1: Create stories.py**

```python
# backend/api/stories.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.queue import StoryOut, USER_ID
from db.database import get_db
from db.models import Story, UserStoryState

router = APIRouter(prefix="/stories", tags=["stories"])


def _set_state(story_id: str, state: str, db: Session) -> dict:
    if not db.get(Story, story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    existing = db.get(UserStoryState, (USER_ID, story_id))
    if existing:
        existing.state = state
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(UserStoryState(user_id=USER_ID, story_id=story_id, state=state,
                              updated_at=datetime.now(timezone.utc)))
    db.commit()
    return {"ok": True}


@router.post("/{story_id}/read")
def mark_read(story_id: str, db: Session = Depends(get_db)):
    return _set_state(story_id, "read", db)


@router.post("/{story_id}/skip")
def mark_skip(story_id: str, db: Session = Depends(get_db)):
    return _set_state(story_id, "skipped", db)


@router.post("/{story_id}/save")
def mark_save(story_id: str, db: Session = Depends(get_db)):
    return _set_state(story_id, "saved", db)


@router.get("/saved", response_model=list[StoryOut])
def get_saved(db: Session = Depends(get_db)):
    return (
        db.query(Story)
        .join(UserStoryState,
              (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == USER_ID))
        .filter(UserStoryState.state == "saved")
        .order_by(UserStoryState.updated_at.desc())
        .all()
    )


@router.get("/history", response_model=list[StoryOut])
def get_history(q: str | None = Query(default=None), db: Session = Depends(get_db)):
    query = (
        db.query(Story)
        .join(UserStoryState,
              (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == USER_ID))
        .filter(UserStoryState.state.in_(["read", "skipped"]))
    )
    if q:
        query = query.filter(Story.title.ilike(f"%{q}%"))
    return query.order_by(UserStoryState.updated_at.desc()).limit(100).all()
```

- [ ] **Step 2: Commit**

```bash
git add backend/api/stories.py
git commit -m "feat: story actions API (read/skip/save) and saved/history endpoints"
```

---

## Task 14: API — sources

**Files:**
- Create: `backend/api/sources.py`

- [ ] **Step 1: Create sources.py**

```python
# backend/api/sources.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Source

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceOut(BaseModel):
    id: int
    name: str
    kind: str
    active: bool
    fetch_interval_mins: int
    last_fetched_at: str | None

    class Config:
        from_attributes = True


class SourcePatch(BaseModel):
    active: bool


@router.get("/", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()


@router.patch("/{source_id}", response_model=SourceOut)
def toggle_source(source_id: int, body: SourcePatch, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.active = body.active
    db.commit()
    db.refresh(source)
    return source
```

- [ ] **Step 2: Commit**

```bash
git add backend/api/sources.py
git commit -m "feat: sources API with active toggle"
```

---

## Task 15: Scheduler + email nudge + main.py (Checkpoint B)

**Files:**
- Modify: `backend/ingestion/scheduler.py`
- Modify: `backend/delivery/email.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Rewrite scheduler.py**

```python
# backend/ingestion/scheduler.py
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_source(source_name: str):
    from db.database import SessionLocal, seed_sources
    from db.models import Source
    from processing.pipeline import process_and_store

    fetcher = None
    if source_name == "arxiv":
        from ingestion.arxiv import fetch_arxiv_papers as fetcher
    elif source_name == "hackernews":
        from ingestion.hn import fetch_hn_stories as fetcher

    if fetcher is None:
        return

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
```

- [ ] **Step 2: Rewrite email.py as nudge**

```python
# backend/delivery/email.py
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from config import settings
from db.models import NudgeLog, Story, UserStoryState

logger = logging.getLogger(__name__)


def _count_new_high_unread(db: Session) -> tuple[int, Story | None]:
    last = db.query(NudgeLog).order_by(NudgeLog.sent_at.desc()).first()
    since = last.sent_at if last else datetime.fromtimestamp(0, tz=timezone.utc)

    stories = (
        db.query(Story)
        .outerjoin(
            UserStoryState,
            (UserStoryState.story_id == Story.id) & (UserStoryState.user_id == "me"),
        )
        .filter(
            Story.relevance_label == "high",
            Story.processed_at >= since,
            UserStoryState.story_id.is_(None),
        )
        .order_by(Story.relevance_score.desc())
        .all()
    )
    return len(stories), (stories[0] if stories else None)


def send_nudge(db: Session) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.info("SMTP not configured — skipping nudge.")
        return

    count, top = _count_new_high_unread(db)
    if count < settings.nudge_min_stories:
        logger.info("Only %d new high stories — below threshold of %d.",
                    count, settings.nudge_min_stories)
        return

    body = (
        f"{count} new AI/ML reads in your queue.\n\n"
        f"{top.title}\n"
        f"→ {top.what_to_do}\n\n"
        f"Open dashboard: {settings.dashboard_url}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{count} new AI/ML reads in your queue"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.email_to
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.email_to, msg.as_string())
        db.add(NudgeLog(stories_count=count, top_story_id=top.id if top else None))
        db.commit()
        logger.info("Nudge sent: %d stories to %s", count, settings.email_to)
    except Exception as exc:
        logger.error("Nudge send failed: %s", exc)
```

- [ ] **Step 3: Finalize main.py**

```python
# backend/main.py
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.queue import router as queue_router
from api.sources import router as sources_router
from api.stories import router as stories_router
from db.database import init_db, seed_sources
from ingestion.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")

app = FastAPI(title="Signal Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queue_router)
app.include_router(stories_router)
app.include_router(sources_router)


@app.on_event("startup")
async def startup():
    init_db()
    db_gen = (lambda: None)()  # noqa — seed via direct session
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        seed_sources(db)
    finally:
        db.close()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/refresh")
def refresh():
    import threading
    from run import run
    threading.Thread(target=run, daemon=True).start()
    return {"status": "started"}
```

- [ ] **Step 4: Test full backend**

```bash
docker-compose up db -d
cd backend && pip install -r requirements.txt
uvicorn main:app --reload
```

In another terminal:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/queue/
curl http://localhost:8000/sources/
```
Expected: `{"status":"ok"}`, stories list, sources list.

- [ ] **Step 5: Commit — Checkpoint B**

```bash
git add backend/ingestion/scheduler.py backend/delivery/email.py backend/main.py
git commit -m "feat: scheduler (arxiv 6h, hn 2h, nudge daily), email nudge, wired main.py — checkpoint B"
```

---

## Task 16: Frontend scaffold

**Files:**
- Create: `frontend/` (full Next.js 14 app)

- [ ] **Step 1: Scaffold Next.js 14 with TypeScript + Tailwind + App Router**

```bash
cd /home/abhisheksara/nodump
npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*" --no-eslint
```
When prompted: accept all defaults.

- [ ] **Step 2: Install shadcn/ui + date-fns + lucide**

```bash
cd frontend
npx shadcn-ui@latest init
```
Accept defaults: TypeScript, Default style, Zinc base color, `./components/ui`, CSS variables yes.

```bash
npm install date-fns lucide-react
```

- [ ] **Step 3: Configure dark mode in tailwind.config.ts**

```typescript
// frontend/tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: { extend: {} },
  plugins: [],
};
export default config;
```

- [ ] **Step 4: Set NEXT_PUBLIC_API_URL in .env.local**

```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
```

- [ ] **Step 5: Verify scaffold runs**

```bash
cd frontend && npm run dev
```
Expected: Next.js dev server at `http://localhost:3000`

- [ ] **Step 6: Commit**

```bash
cd /home/abhisheksara/nodump
git add frontend/
git commit -m "feat: scaffold Next.js 14 app with Tailwind + shadcn/ui"
```

---

## Task 17: Types + API client

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create types.ts**

```typescript
// frontend/lib/types.ts
export interface Story {
  id: string;
  title: string;
  url: string;
  author: string;
  published_at: string;
  source_id: number;
  summary: string;
  why_matters: string;
  what_to_do: string;
  relevance_label: "high" | "medium" | null;
  relevance_score: number | null;
  domain: string;
  sub_domain: string | null;
  triage_label: string | null;
}

export interface Source {
  id: number;
  name: string;
  kind: string;
  active: boolean;
  fetch_interval_mins: number;
  last_fetched_at: string | null;
}
```

- [ ] **Step 2: Create api.ts**

```typescript
// frontend/lib/api.ts
import { Source, Story } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  getQueue: (domain?: string | null) =>
    request<Story[]>(`/queue/${domain ? `?domain=${domain}` : ""}`),

  markRead: (id: string) =>
    request<{ ok: boolean }>(`/stories/${id}/read`, { method: "POST" }),

  markSkip: (id: string) =>
    request<{ ok: boolean }>(`/stories/${id}/skip`, { method: "POST" }),

  markSave: (id: string) =>
    request<{ ok: boolean }>(`/stories/${id}/save`, { method: "POST" }),

  getSaved: () => request<Story[]>("/stories/saved"),

  getHistory: (q?: string) =>
    request<Story[]>(`/stories/history${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  getSources: () => request<Source[]>("/sources/"),

  updateSource: (id: number, active: boolean) =>
    request<Source>(`/sources/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    }),

  triggerRefresh: () => request<{ status: string }>("/refresh", { method: "POST" }),
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/
git commit -m "feat: typed API client and Story/Source types"
```

---

## Task 18: StoryCard component

**Files:**
- Create: `frontend/components/StoryCard.tsx`

- [ ] **Step 1: Create StoryCard.tsx**

```tsx
// frontend/components/StoryCard.tsx
"use client";

import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { BookCheck, Bookmark, ExternalLink, SkipForward } from "lucide-react";
import { api } from "@/lib/api";
import { Story } from "@/lib/types";

const SUB_LABELS: Record<string, string> = {
  llms: "LLMs",
  agents: "Agents",
  applied_ml: "Applied ML",
  infra_inference: "Infra/Inference",
  other: "Other",
};

interface Props {
  story: Story;
  onAction?: (id: string) => void;
  showActions?: boolean;
}

export function StoryCard({ story, onAction, showActions = true }: Props) {
  const [busy, setBusy] = useState<string | null>(null);

  const act = async (fn: () => Promise<unknown>, key: string) => {
    setBusy(key);
    try {
      await fn();
      onAction?.(story.id);
    } catch (e) {
      console.error(e);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 space-y-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          {story.sub_domain && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 font-mono">
              {SUB_LABELS[story.sub_domain] ?? story.sub_domain}
            </span>
          )}
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              story.relevance_label === "high"
                ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                : "bg-zinc-800 text-zinc-500"
            }`}
          >
            {story.relevance_label ?? "–"}
          </span>
          <span className="text-xs text-zinc-600">
            {formatDistanceToNow(new Date(story.published_at), { addSuffix: true })}
          </span>
        </div>
        <a
          href={story.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-zinc-600 hover:text-zinc-200 transition-colors mt-0.5"
          title="Open original"
        >
          <ExternalLink size={15} />
        </a>
      </div>

      {/* Title */}
      <h2 className="text-sm font-semibold text-zinc-100 leading-snug">{story.title}</h2>

      {/* Summary */}
      {story.summary && (
        <p className="text-sm text-zinc-400 leading-relaxed">{story.summary}</p>
      )}

      {/* Why it matters */}
      {story.why_matters && (
        <div className="space-y-0.5">
          <p className="text-xs text-zinc-600 uppercase tracking-widest">Why it matters</p>
          <p className="text-sm text-zinc-300 leading-relaxed">{story.why_matters}</p>
        </div>
      )}

      {/* Action */}
      {story.what_to_do && (
        <div className="rounded-md bg-zinc-800/60 border border-zinc-700/60 px-4 py-3 space-y-0.5">
          <p className="text-xs text-zinc-600 uppercase tracking-widest">Action</p>
          <p className="text-sm text-zinc-100 font-medium leading-snug">{story.what_to_do}</p>
        </div>
      )}

      {/* Buttons */}
      {showActions && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => act(() => api.markRead(story.id), "read")}
            disabled={busy !== null}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-emerald-950/60 text-emerald-400 hover:bg-emerald-950 disabled:opacity-40 transition-colors border border-emerald-900/50"
          >
            <BookCheck size={13} />
            {busy === "read" ? "…" : "Read"}
          </button>
          <button
            onClick={() => act(() => api.markSkip(story.id), "skip")}
            disabled={busy !== null}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-400 hover:bg-zinc-700 disabled:opacity-40 transition-colors"
          >
            <SkipForward size={13} />
            {busy === "skip" ? "…" : "Skip"}
          </button>
          <button
            onClick={() => act(() => api.markSave(story.id), "save")}
            disabled={busy !== null}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-400 hover:bg-zinc-700 disabled:opacity-40 transition-colors"
          >
            <Bookmark size={13} />
            {busy === "save" ? "…" : "Save"}
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/StoryCard.tsx
git commit -m "feat: StoryCard component with read/skip/save actions"
```

---

## Task 19: DomainTabs component

**Files:**
- Create: `frontend/components/DomainTabs.tsx`

- [ ] **Step 1: Create DomainTabs.tsx**

```tsx
// frontend/components/DomainTabs.tsx
"use client";

const DOMAINS = [
  { key: null, label: "All" },
  { key: "llms", label: "LLMs" },
  { key: "agents", label: "Agents" },
  { key: "applied_ml", label: "Applied ML" },
  { key: "infra_inference", label: "Infra / Inference" },
];

interface Props {
  active: string | null;
  onChange: (domain: string | null) => void;
}

export function DomainTabs({ active, onChange }: Props) {
  return (
    <div className="flex gap-1 border-b border-zinc-800">
      {DOMAINS.map(({ key, label }) => (
        <button
          key={String(key)}
          onClick={() => onChange(key)}
          className={`px-4 py-2 text-sm transition-colors rounded-t-md -mb-px ${
            active === key
              ? "text-zinc-100 border border-zinc-800 border-b-zinc-900 bg-zinc-900"
              : "text-zinc-500 hover:text-zinc-300"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/DomainTabs.tsx
git commit -m "feat: DomainTabs component for queue filtering"
```

---

## Task 20: Layout + globals

**Files:**
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: Rewrite layout.tsx**

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Signal Engine",
  description: "Personal AI/ML signal filter",
};

const NAV = [
  { href: "/", label: "Queue" },
  { href: "/saved", label: "Saved" },
  { href: "/history", label: "History" },
  { href: "/settings", label: "Settings" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-zinc-950 text-zinc-100 min-h-screen antialiased`}>
        <div className="max-w-2xl mx-auto px-4 py-8">
          <header className="flex items-center justify-between mb-10">
            <Link href="/" className="font-mono text-sm text-zinc-500 hover:text-zinc-300 tracking-tight transition-colors">
              signal engine
            </Link>
            <nav className="flex gap-6">
              {NAV.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors"
                >
                  {label}
                </Link>
              ))}
            </nav>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Trim globals.css to essentials**

```css
/* frontend/app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: dark;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/layout.tsx frontend/app/globals.css
git commit -m "feat: dark layout with nav"
```

---

## Task 21: Queue page

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Write queue page**

```tsx
// frontend/app/page.tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Story } from "@/lib/types";
import { DomainTabs } from "@/components/DomainTabs";
import { StoryCard } from "@/components/StoryCard";

export default function QueuePage() {
  const [domain, setDomain] = useState<string | null>(null);
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStories(await api.getQueue(domain));
    } catch (e) {
      setError("Failed to load queue. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [domain]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-zinc-100">Queue</h1>
        <button
          onClick={load}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          refresh
        </button>
      </div>

      <DomainTabs active={domain} onChange={(d) => { setDomain(d); }} />

      {loading && (
        <div className="text-zinc-600 text-sm py-12 text-center">Loading…</div>
      )}

      {error && (
        <div className="text-red-400 text-sm py-12 text-center">{error}</div>
      )}

      {!loading && !error && stories.length === 0 && (
        <div className="text-zinc-600 text-sm py-16 text-center">
          Queue clear. New stories arrive every few hours.
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-3">
          {stories.map((s) => (
            <StoryCard
              key={s.id}
              story={s}
              onAction={(id) => setStories((prev) => prev.filter((x) => x.id !== id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: queue page with domain tabs and story cards"
```

---

## Task 22: Saved page

**Files:**
- Create: `frontend/app/saved/page.tsx`

- [ ] **Step 1: Create saved page**

```tsx
// frontend/app/saved/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Story } from "@/lib/types";
import { StoryCard } from "@/components/StoryCard";

export default function SavedPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSaved().then(setStories).finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-5">
      <h1 className="text-lg font-semibold text-zinc-100">Saved</h1>
      {loading && <div className="text-zinc-600 text-sm py-12 text-center">Loading…</div>}
      {!loading && stories.length === 0 && (
        <div className="text-zinc-600 text-sm py-16 text-center">Nothing saved yet.</div>
      )}
      <div className="space-y-3">
        {stories.map((s) => (
          <StoryCard key={s.id} story={s} showActions={false} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/saved/
git commit -m "feat: saved stories page"
```

---

## Task 23: History page

**Files:**
- Create: `frontend/app/history/page.tsx`

- [ ] **Step 1: Create history page**

```tsx
// frontend/app/history/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Story } from "@/lib/types";
import { StoryCard } from "@/components/StoryCard";

export default function HistoryPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  const load = (q: string) => {
    setLoading(true);
    api.getHistory(q || undefined).then(setStories).finally(() => setLoading(false));
  };

  useEffect(() => { load(""); }, []);

  return (
    <div className="space-y-5">
      <h1 className="text-lg font-semibold text-zinc-100">History</h1>
      <input
        type="text"
        placeholder="Search by title…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && load(query)}
        className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
      />
      {loading && <div className="text-zinc-600 text-sm py-12 text-center">Loading…</div>}
      {!loading && stories.length === 0 && (
        <div className="text-zinc-600 text-sm py-16 text-center">No history yet.</div>
      )}
      <div className="space-y-3">
        {stories.map((s) => (
          <StoryCard key={s.id} story={s} showActions={false} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/history/
git commit -m "feat: history page with title search"
```

---

## Task 24: Settings page

**Files:**
- Create: `frontend/app/settings/page.tsx`

- [ ] **Step 1: Create settings page**

```tsx
// frontend/app/settings/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Source } from "@/lib/types";

export default function SettingsPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    api.getSources().then(setSources).finally(() => setLoading(false));
  }, []);

  const toggle = async (source: Source) => {
    const updated = await api.updateSource(source.id, !source.active);
    setSources((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  };

  const triggerRefresh = async () => {
    setRefreshing(true);
    try {
      await api.triggerRefresh();
    } finally {
      setTimeout(() => setRefreshing(false), 2000);
    }
  };

  return (
    <div className="space-y-8">
      <h1 className="text-lg font-semibold text-zinc-100">Settings</h1>

      <section className="space-y-3">
        <h2 className="text-xs text-zinc-500 uppercase tracking-widest">Sources</h2>
        {loading && <div className="text-zinc-600 text-sm">Loading…</div>}
        {sources.map((src) => (
          <div
            key={src.id}
            className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3"
          >
            <div>
              <p className="text-sm font-medium text-zinc-200">{src.name}</p>
              <p className="text-xs text-zinc-600 mt-0.5">
                {src.kind} · every {src.fetch_interval_mins / 60}h
                {src.last_fetched_at && ` · last fetched ${new Date(src.last_fetched_at).toLocaleString()}`}
              </p>
            </div>
            <button
              onClick={() => toggle(src)}
              className={`relative w-10 h-5 rounded-full transition-colors ${
                src.active ? "bg-emerald-600" : "bg-zinc-700"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  src.active ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-xs text-zinc-500 uppercase tracking-widest">Actions</h2>
        <button
          onClick={triggerRefresh}
          disabled={refreshing}
          className="px-4 py-2 text-sm rounded-md bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50 transition-colors"
        >
          {refreshing ? "Ingestion started…" : "Run ingestion now"}
        </button>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/settings/
git commit -m "feat: settings page with source toggles and manual refresh"
```

---

## Task 25: docker-compose + frontend Dockerfile (Checkpoint C)

**Files:**
- Modify: `docker-compose.yml`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create frontend/Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM base AS builder
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

- [ ] **Step 2: Add standalone output to next.config.js**

```javascript
// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};
module.exports = nextConfig;
```

- [ ] **Step 3: Update docker-compose.yml**

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: feed
      POSTGRES_PASSWORD: feed
      POSTGRES_DB: research_feed
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U feed"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    environment:
      DATABASE_URL: postgresql://feed:feed@db:5432/research_feed
      DASHBOARD_URL: http://localhost:3000
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - runs_data:/app/runs

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on:
      - backend

volumes:
  pgdata:
  runs_data:
```

- [ ] **Step 4: Full stack smoke test**

```bash
docker-compose down -v
docker-compose up --build
```

Visit `http://localhost:3000` — expect dashboard with dark theme and nav.
Visit `http://localhost:3000/settings` — expect sources list with toggles.
Click "Run ingestion now" — backend starts pipeline, check backend logs.

- [ ] **Step 5: Commit — Checkpoint C**

```bash
git add frontend/Dockerfile frontend/next.config.js docker-compose.yml
git commit -m "feat: add frontend docker service, standalone Next.js build — checkpoint C complete"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| arXiv + HN ingestion | Tasks 5, 6 |
| Two-stage GPT-4o triage + enrich | Task 8 |
| Content extraction (arXiv HTML, trafilatura, HN comments) | Task 7 |
| Dedup by (source_id, external_id) + url | Task 4 |
| Postgres schema: Source, Story, UserStoryState, NudgeLog | Task 2 |
| Rolling queue SQL (30-day, unread, ranked) | Task 12 |
| Read/Skip/Save actions | Task 13 |
| Saved + History endpoints | Task 13 |
| Sources toggle API | Task 14 |
| Scheduler: arxiv 6h, hn 2h, nudge 07:00 | Task 15 |
| Email nudge (≥3 high unread, 3-line format) | Task 15 |
| Run logs JSONL | Task 9 |
| Manual trigger `python run.py` | Task 11 |
| Next.js 14 dark dashboard | Tasks 16–24 |
| Domain tabs (All/LLMs/Agents/Applied ML/Infra) | Task 19 |
| StoryCard with all fields + actions | Task 18 |
| Saved page | Task 22 |
| History page with search | Task 23 |
| Settings: source toggles + manual refresh | Task 24 |
| Docker Compose full stack | Task 25 |
| CORS configured | Task 15 (main.py) |

No gaps found.

### Type consistency check

- `StoryOut` (backend) ↔ `Story` (frontend): fields match — `why_matters`, `what_to_do`, `relevance_label`, `sub_domain`, `triage_label` all present in both.
- `SourceOut` (backend) ↔ `Source` (frontend): match.
- `_set_state` used in read/skip/save — all call same function, `USER_ID = "me"` consistent.
- `seed_sources` called in both `run.py` and `main.py` startup — idempotent (checks before insert), safe.
