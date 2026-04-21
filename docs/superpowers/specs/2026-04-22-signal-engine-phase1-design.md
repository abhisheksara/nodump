# Signal Engine Phase 1 — Design Spec

## Goal

Single-user personal AI/ML signal filter. Open dashboard or email nudge → see ranked unread stories with actionable takeaways. Replaces 1–2hr/day of Twitter/arXiv scrolling. Validated by 14+ days of daily use before Phase 2 begins.

## Trajectory

- **Phase 1 (this spec):** Personal, single-user, no auth, localhost dashboard + email nudge.
- **Phase 2:** Source breadth, prompt A/B harness, eval loop, search. Still personal.
- **Phase 3:** Multi-user public launch — auth, user profiles, Resend, deploy. Architecture.md becomes relevant here.

---

## Architecture

```
Scheduler (APScheduler)
  → arxiv_fetcher      → dedup (source_id + external_id + url hash)
  → hn_fetcher         ↓
                    LLM triage (gpt-4o, Stage 1)
                       ↓ drop 'ignore'
                    Content extractor (arxiv HTML / trafilatura + HN comments)
                       ↓
                    LLM enrich (gpt-4o, Stage 2)
                       ↓
                    Postgres (stories + user_story_state)
                       ↓
                    Nudge job (SMTP, 07:00 daily)

FastAPI (backend)
  GET  /queue              → top 5 unread, optional ?domain=
  POST /stories/{id}/read
  POST /stories/{id}/skip
  POST /stories/{id}/save
  GET  /stories/saved
  GET  /stories/history    → read+skipped, ?q= search
  GET  /sources            → list sources
  PATCH /sources/{id}      → toggle active
  POST /refresh            → manual trigger
  GET  /health

Next.js 14 (App Router, frontend)
  /           queue + domain tabs
  /saved      saved stories
  /history    read+skipped, searchable
  /settings   source toggles, env config read-only
```

---

## Data Model

### `sources`
```sql
CREATE TABLE sources (
  id                  SERIAL PRIMARY KEY,
  name                VARCHAR(100) NOT NULL,
  kind                VARCHAR(20) NOT NULL,      -- 'rss' | 'api'
  config_json         JSONB NOT NULL DEFAULT '{}',
  tags                TEXT[] NOT NULL DEFAULT '{}',
  authority_weight    FLOAT NOT NULL DEFAULT 0.5,
  fetch_interval_mins INT NOT NULL DEFAULT 360,
  active              BOOLEAN NOT NULL DEFAULT TRUE,
  last_fetched_at     TIMESTAMPTZ
);
-- Seeded: arxiv (kind=api), hackernews (kind=api)
```

### `stories`
```sql
CREATE TABLE stories (
  id                  VARCHAR(255) PRIMARY KEY,  -- source_id:external_id
  source_id           INT NOT NULL REFERENCES sources(id),
  external_id         VARCHAR(255) NOT NULL,
  url                 TEXT NOT NULL UNIQUE,
  title               TEXT NOT NULL,
  raw_content         TEXT NOT NULL DEFAULT '',  -- abstract or snippet
  author              TEXT NOT NULL DEFAULT '',
  published_at        TIMESTAMPTZ NOT NULL,
  fetched_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Stage 1 triage
  triage_label        VARCHAR(10),               -- 'high' | 'medium' | 'ignore'
  triage_score        FLOAT,

  -- Stage 2 enrichment
  context_used        JSONB,                     -- what was fed to LLM (for replay)
  summary             TEXT NOT NULL DEFAULT '',
  why_matters         TEXT NOT NULL DEFAULT '',
  what_to_do          TEXT NOT NULL DEFAULT '',
  relevance_label     VARCHAR(10),               -- 'high' | 'medium'
  relevance_score     FLOAT,
  domain              VARCHAR(50),               -- always 'ai_ml' Phase 1
  sub_domain          VARCHAR(50),               -- 'llms'|'agents'|'applied_ml'|'infra_inference'|'other'
  llm_model           VARCHAR(100),
  processed_at        TIMESTAMPTZ
);

CREATE UNIQUE INDEX stories_source_external ON stories(source_id, external_id);
CREATE INDEX stories_queue ON stories(relevance_score DESC, published_at DESC)
  WHERE relevance_label != 'ignore' AND processed_at IS NOT NULL;
```

### `user_story_state`
```sql
CREATE TABLE user_story_state (
  user_id     VARCHAR(50) NOT NULL DEFAULT 'me',  -- hardcoded Phase 1, FK Phase 3
  story_id    VARCHAR(255) NOT NULL REFERENCES stories(id),
  state       VARCHAR(10) NOT NULL,               -- 'read' | 'skipped' | 'saved'
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, story_id)
);
```

### `nudge_log`
```sql
CREATE TABLE nudge_log (
  id              SERIAL PRIMARY KEY,
  sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  stories_count   INT NOT NULL,
  top_story_id    VARCHAR(255) REFERENCES stories(id)
);
```

---

## Ingestion

### arXiv
- Source: arXiv API, categories `cs.AI` + `cs.LG`, last 48h.
- Fetch interval: every 6h.
- `external_id`: arXiv paper ID (e.g. `2401.12345`).
- `raw_content`: abstract (from API response, free).
- Story schema emitted: `{id, source_id, external_id, url, title, raw_content, author, published_at}`.

### HN (Hacker News)
- Source: HN Algolia API — top stories with score ≥ 100.
- Fetch interval: every 2h.
- `external_id`: HN item ID.
- `raw_content`: HN title + story URL og:description (httpx GET, read only `<meta>` tags, fast).
- Comments: top 5 by score fetched from HN Firebase API during Stage 2.
- Story schema emitted: same as above.

### Dedup
Skip insert if `(source_id, external_id)` already exists, or `url` already exists.

---

## LLM Pipeline (Two-Stage)

**Provider:** OpenAI SDK, model `gpt-4o`.
**Caching:** Automatic prefix caching (system prompt first, >1024 tokens — no extra config needed).

### Stage 1 — Triage

**Input:** title + abstract (arXiv) or title + og:description (HN). ~300–500 tokens.

**System prompt (cached):**
```
You are a ruthless AI/ML signal filter for Abhishek — Senior Data Scientist
obsessed with LLMs, agents, multi-agent systems, applied ML, inference.
Score each item on relevance to him. Output only valid JSON.
```

**User prompt:**
```
Source: {source}
Title: {title}
Content: {raw_content}

JSON only:
{
  "triage_label": "<high|medium|ignore>",
  "triage_score": <float 0.0-1.0>,
  "sub_domain": "<llms|agents|applied_ml|infra_inference|other>"
}
```

**If `triage_label = "ignore"` → drop story. Do not fetch content. Do not store.**

### Stage 2 — Deep Enrich (non-ignore only)

**Content extraction per source:**

| Source | Extracted content |
|---|---|
| arXiv | Fetch `arxiv.org/html/{id}` → BeautifulSoup → extract Introduction + Conclusion sections. Fallback: abstract only if HTML 404. |
| HN | trafilatura on story URL (first 2000 chars). Fetch top 5 HN comments via Firebase API. Format: `[article excerpt]\n\nWhat HN says:\n- {comment1}\n- {comment2}...` |

**System prompt (same cached prompt as Stage 1).**

**User prompt:**
```
Source: {source}
Title: {title}
Sub-domain: {sub_domain}
Content:
{extracted_content}

Abhishek's interests: LLMs, agents, multi-agent systems, applied ML, inference.

Quality bar for what_to_do:
BAD: "This is relevant to LLMs." (obvious, no action)
GOOD: "Try replacing your agent's retry logic with this paper's adaptive backoff — run it on your eval harness this week."

Rules:
- what_to_do must start with an imperative verb (Try/Test/Benchmark/Implement/Apply/Skip)
- Must name a concrete artifact or action target
- If no actionable angle → set relevance_label 'medium', what_to_do starts with "Read — "

JSON only:
{
  "summary": "<2-3 sentences: what happened and what result>",
  "why_matters": "<2 sentences: specific impact on LLM/agent/applied-ML work>",
  "what_to_do": "<one imperative sentence: concrete action Abhishek can take this week>",
  "relevance_label": "<high|medium>",
  "relevance_score": <float 0.0-1.0>
}
```

**Storage:** persist `context_used` = `{source, title, extracted_content}` as JSONB for replay.

**Error handling:**
- Stage 1 JSON parse fail → 1 retry → skip item (log to run file).
- Stage 2 extraction fail → fallback to abstract → still enrich.
- Stage 2 LLM fail → 1 retry → store with empty enrichment fields, mark `processed_at` NULL.

---

## Queue Logic

```sql
SELECT s.*
FROM stories s
LEFT JOIN user_story_state uss
  ON uss.story_id = s.id AND uss.user_id = 'me'
WHERE s.relevance_label IN ('high', 'medium')
  AND s.processed_at IS NOT NULL
  AND s.published_at >= NOW() - INTERVAL '30 days'
  AND (:sub_domain IS NULL OR s.sub_domain = :sub_domain)
  AND uss.story_id IS NULL
ORDER BY s.relevance_score DESC
LIMIT 5;
```

---

## Scheduler

| Job | Interval | Logic |
|---|---|---|
| `fetch_arxiv` | Every 6h | Fetch → dedup → Stage 1 → Stage 2 → store |
| `fetch_hn` | Every 2h | Fetch → dedup → Stage 1 → Stage 2 → store |
| `send_nudge` | Daily 07:00 | Count new unread `high` stories since last nudge. If ≥3 → send email. |

---

## Email Nudge

- **Trigger:** ≥3 new unread `high` stories since last `nudge_log` entry.
- **Transport:** SMTP (existing `backend/delivery/email.py`), env-configured.
- **Format:**
  ```
  Subject: {N} new AI/ML reads in your queue

  {top_story_title}
  → {what_to_do}

  Open dashboard → {DASHBOARD_URL}
  ```
- **On send:** insert row to `nudge_log`.

---

## Run Logs

Every ingestion run writes to `./runs/YYYY-MM-DDTHHMM.jsonl`. Each line is a JSON object with `raw_item`, `triage_result`, `extracted_content`, `enrich_result`, `action` (`stored` | `skipped_duplicate` | `dropped_ignore` | `enrich_failed`). Retained 30 days.

---

## Frontend (Next.js 14)

**Stack:** Next.js 14 App Router, Tailwind CSS, shadcn/ui components, Inter font. Dark mode default. `max-w-2xl` content column. Linear-esque minimal chrome.

**Pages:**

### `/` — Queue
- Domain tabs: All / LLMs / Agents / Applied ML / Infra-Inference (filtered by `?domain=`).
- Up to 5 story cards, ranked by score.
- Empty state: "Queue clear. Check back tomorrow." with last-fetch timestamp.

**Story card:**
```
[Source chip] [Sub-domain chip] [High/Medium badge]    {published_at relative}

{title}                                                 [↗ Open]

{summary}

Why it matters: {why_matters}

Action: {what_to_do}

[✓ Read]  [→ Skip]  [⊕ Save]
```

### `/saved` — Saved Stories
Same card shape. No action buttons except [Remove from saved].

### `/history` — All Dismissed
Read + skipped stories, newest first. `<input>` search by title (client-side filter). Shows state badge (Read/Skipped).

### `/settings` — Config
- Source list: name, kind, active toggle (PATCH `/sources/{id}`).
- Read-only: `digest_hour`, `email_to`, `feed_limit` from API.
- Manual trigger: "Run ingestion now" button → POST `/refresh`.

---

## Backend File Structure

```
backend/
  config.py                     # add openai_api_key, dashboard_url; remove anthropic fields
  main.py                       # unchanged structure
  api/
    feed.py → queue.py          # rename; rewrite for rolling queue + sub_domain filter
    sources.py                  # NEW: list + toggle sources
    stories.py                  # NEW: read/skip/save + saved + history
  db/
    models.py                   # rewrite: sources, stories, user_story_state, nudge_log
    database.py                 # unchanged
    migrations/                 # Alembic; start fresh migration chain
  ingestion/
    arxiv.py                    # update to new Story schema
    hn.py                       # NEW
    scheduler.py                # add hn job; fix nudge logic
    dedup.py                    # NEW: extracted dedup logic
  processing/
    pipeline.py                 # two-stage LLM call
    llm.py                      # rewrite: openai SDK, Stage 1 + Stage 2 prompts
    extractor.py                # NEW: arXiv HTML parse + HN trafilatura + comments
  delivery/
    email.py                    # demote to nudge format
  run.py                        # NEW: CLI entry point for manual trigger
```

## Frontend File Structure

```
frontend/
  app/
    layout.tsx                  # dark theme, Inter font, nav
    page.tsx                    # queue view
    saved/page.tsx
    history/page.tsx
    settings/page.tsx
  components/
    StoryCard.tsx
    DomainTabs.tsx
    QueueView.tsx
  lib/
    api.ts                      # typed fetch wrappers for all endpoints
    types.ts                    # Story, Source, etc.
  next.config.js
  tailwind.config.js
  package.json                  # Next.js 14, shadcn/ui, tailwindcss
```

---

## Dependencies

### Backend (additions to requirements.txt)
```
openai>=1.30.0          # replaces anthropic
trafilatura>=1.9.0      # HN article body extraction
beautifulsoup4>=4.12.0  # arXiv HTML section extraction
lxml>=5.2.0             # BS4 parser
```
Remove: `anthropic`, `numpy` (unused).

### Frontend
```json
{
  "next": "14",
  "react": "^18",
  "tailwindcss": "^3",
  "@radix-ui/react-*": "shadcn/ui deps",
  "lucide-react": "icons"
}
```

---

## docker-compose.yml changes

Add frontend service:
```yaml
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
```

---

## Testing

- **Unit:** prompt JSON parse (mock OpenAI), dedup hash logic, queue SQL (SQLite in-memory fixture), arXiv HTML section extractor (fixture HTML), HN comment parser (fixture JSON).
- **Integration:** full pipeline on 5 fixture stories (2 arXiv, 2 HN, 1 HN dead URL) → assert DB state. Mock OpenAI calls with recorded responses.
- **Manual:** `python -m backend.run` → inspect `./runs/` JSONL + check DB.
- No CI Phase 1.

---

## What This Replaces / Removes

| Old | New |
|---|---|
| `anthropic` SDK | `openai` SDK |
| `backend/api/chat.py` | deleted (already gone) |
| `backend/api/feedback.py` | deleted (already gone) |
| `backend/ingestion/rss.py` | deleted (already gone); arxiv.py updated |
| `content_items` table | `stories` table (fresh migration) |
| Single-stage haiku enrich | Two-stage gpt-4o triage + deep enrich |
| Full email digest | Nudge email (3-line format) |
| `frontend/` (deleted) | Rebuilt: Next.js 14 App Router |

---

## Explicitly Out of Scope (Phase 1)

- Auth of any kind
- Multi-user support
- Twitter/X source
- Papers with Code source (Phase 2)
- Object storage (S3/MinIO)
- Resend transactional email
- Prompt A/B harness
- Feedback/thumbs signal
- Search (history page: client-side filter only)
- Mobile
- CI/CD
- Deployment
