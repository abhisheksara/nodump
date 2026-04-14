# AI Research Feed — MVP

> "In 5 minutes, know the 5 most important things in AI today — and why they matter to YOU."

Personalized AI research feed for AI engineers. Aggregates arXiv papers and top AI blogs, scores relevance with Claude, and lets you interact via a chat interface.

---

## Architecture

```
backend/   FastAPI + SQLAlchemy + APScheduler
frontend/  Next.js 14 + Tailwind CSS
db/        Postgres (or SQLite for local dev)
llm/       Anthropic Claude (haiku) with prompt caching
```

## Quick Start (Local Dev — SQLite, no Docker)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY
# DATABASE_URL defaults to sqlite:///./research_feed.db

uvicorn main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

On startup the backend will:
- Create DB tables
- Start the ingestion scheduler (every 6h by default)
- Run an immediate ingestion in the background

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Quick Start (Docker Compose — Postgres)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set ANTHROPIC_API_KEY

docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required** for LLM enrichment and chat |
| `DATABASE_URL` | `sqlite:///./research_feed.db` | Postgres or SQLite URL |
| `FETCH_INTERVAL_HOURS` | `6` | How often to ingest new content |
| `FEED_LIMIT` | `10` | Max items shown per feed |
| `USER_INTERESTS` | `LLMs,agents,applied ML,...` | Comma-separated interests for relevance |
| `TWITTER_BEARER_TOKEN` | — | Optional — enables Twitter/X ingestion |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/feed/` | Get ranked feed (`?source=arxiv&days=3`) |
| `POST` | `/feed/refresh` | Manually trigger ingestion |
| `POST` | `/feedback/` | Submit thumbs up/down |
| `DELETE` | `/feedback/` | Remove feedback |
| `POST` | `/chat/` | Chat with your feed (RAG) |
| `GET` | `/health` | Health check |

---

## Content Sources

- **arXiv** — cs.AI, cs.LG, cs.CL, cs.CV (20 papers/category)
- **RSS Blogs** — OpenAI, Anthropic, HuggingFace, DeepMind, BAIR, Lilian Weng

---

## How Relevance Works

For each item, Claude (Haiku) produces:
1. **Summary** — 3-5 sentences
2. **Why this matters to you** — specific to AI engineers working on LLMs/agents
3. **Relevance score** — 0.0 to 1.0

Feedback (thumbs up/down) adjusts the ranking in future feeds (+0.15 / -0.30).

The system prompt is cached via Anthropic's prompt caching API, keeping costs low on repeated calls.
