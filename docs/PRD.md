The skill expects a file path but got raw text — compressing directly:

---

# 📄 PRD: Personal AI Signal Engine (Phase 1 — Single User: Me)

---

## 1. 🎯 Goal

Build **personal AI research filter** that:

- Cut daily AI content time ~1–2hr → <15min
- Surface only **high-leverage insights**
- **Decide what to act on**, not just read

---

## 2. 👤 User (Only One)

**Abhishek (me):**
- Senior Data Scientist
- Interests:
  - LLMs
  - Agents / multi-agent systems
  - Applied ML systems
  - Build faster/smarter

---

## 3. 🔥 Core Problem

> Consume lots AI content but:
- Mostly noise
- Don't know what's worth time
- Rarely convert reading → action

---

## 4. 💡 Core Value Proposition

> "In 5 minutes, I know what matters in AI today — and what I should do about it."

---

## 5. 🧱 MVP Scope (Strict)

### 5.1 Daily Output (THE PRODUCT)

Daily generate:

## "Top 3 AI Things That Matter (For Me)"

Each item:

---

### 🧩 Output Format

Title

What happened (2–3 lines max)

Why matters (specific to MY interests)

What I should do (MANDATORY — must be actionable)

Relevance (High / Medium / Ignore)

---

### 🚨 Quality Bar

Bad:
> "This is relevant to your interest in LLMs"

→ Useless.

Good:
> "Try this in your agent pipeline to reduce failures"

→ Valuable.

---

## 6. 🔍 Data Sources (Phase 1)

**ONE source only**:

Option A:
- arXiv (cs.AI, cs.LG)

Option B:
- Curated Twitter list (~50 high-signal accounts)

👉 Pick ONE. No multi-source aggregation yet.

---

## 7. ⚙️ Pipeline (Simple, Daily Batch)

1. Fetch ~50–100 items
2. Deduplicate
3. Run LLM → generate:
   - Summary
   - Why matters (personalized)
   - What to do
4. Rank via heuristic:
   - LLM judgment + keyword match
5. Select top 3
6. Store results

---

## 8. 🏗️ Tech Stack

### Backend
- Python (FastAPI or simple script)

### LLM
- OpenAI / Claude

### Storage
- Postgres or JSON initially

### Frontend (Optional)
- Not required

---

## 9. 📬 Delivery

ONE:

- Email to myself (preferred)
- OR simple web page
- OR CLI output

👉 Optimize **consumption speed**, not UI

---

## 10. ❌ Explicit Non-Goals

Do NOT build:

- Chat interface
- Feedback system
- Multi-user support
- Personalization engine
- Real-time updates
- Fancy UI

Building these = procrastinating.

---

## 11. 📊 Success Criteria (Personal)

After 7 days:

- Check daily
- Saves time vs Twitter/arXiv
- 2–3 insights led to:
  - Trying something new
  - Changed how I build

---

## 12. ⚠️ Failure Conditions

Kill/rethink if:

- Output generic
- Ignore after 3–4 days
- Doesn't change what I do

---

## 13. 🚀 Execution Plan (Fast)

Day 1: Setup ingestion + basic pipeline

Day 2: Add LLM generation (summary + why + action)

Day 3: Ranking + output formatting

Day 4–7: Iterate prompt quality manually

---

## 14. 🧠 Key Insight (Important)

NOT summarization tool.

> System that forces convert information → action

---

## 15. 🔄 Phase 2 (Only if Phase 1 Works)

Expand ONLY if:

- Use daily
- Real advantage felt

Add:
- Multi-source ingestion
- Light personalization
- Distribution

---

# 📄 PRD: Generalized Signal Engine (Phase 2 — Multi-Topic, Multi-User)

---

## 1. 🎯 Goal

Extend personal AI signal engine → general-purpose daily briefing platform.

Users pick interest domains. Get top 5 high-signal stories each day with actionable context. No noise, no scroll.

---

## 2. 👤 Target Users

Busy professionals who:
- Follow multiple domains (tech, business, politics, startups)
- Spend 1–2hr/day on news/feeds
- Rarely convert reading → action or decision

---

## 3. 💡 Core Value Proposition

> "5 minutes. Your domains. What matters today — and what to do about it."

Same formula as Phase 1, generalized across topics + users.

---

## 4. 🧱 Product Scope

### 4.1 Interest Domains (V1)

Predefined categories user selects (1–5 max):

- AI / ML
- Startups / Venture
- Business / Strategy
- Politics / Policy
- Science / Research
- Finance / Markets

Onboarding shows categories as clickable chips (low friction). User picks and goes — no blank inputs.

> **V2 note:** Add free-form interest refinement per category (e.g. within AI/ML → "agents, tabular data generation"). See `IDEAS.md`.

### 4.2 Story Queue (Core Model)

No daily pressure. Instead: **rolling queue of top 5 unread stories** from last 30 days.

- Pipeline ingests + ranks continuously
- Queue always shows best 5 unread across selected domains
- As user clears stories, next-best surface from backlog
- Stories older than 30 days auto-expire from queue

**User actions per story:**

| Action | Meaning |
|---|---|
| Mark as Read | Consumed (or acknowledged) — removed from queue |
| Skip | Not relevant right now — removed from queue |
| Save | Keep for later (outside main queue) |

No streaks. No pressure. Queue shrinks when user engages, refills as new content arrives.

Each story card:

```
Title

What happened (2–3 lines)

Why matters (tied to selected domain context)

What to do / think about (actionable)

Domain tag + Relevance (High / Medium) + Published date
```

### 4.3 Delivery

- Dashboard (primary) — queue view, story cards, history, settings
- Email (secondary) — "X new stories in your queue" nudge, configurable frequency
- No mobile app in Phase 2

---

## 5. ⚙️ Pipeline Changes vs Phase 1

| Component | Phase 1 | Phase 2 |
|---|---|---|
| Sources | 1 (arXiv or Twitter) | Per-domain source map |
| Personalization | Hardcoded (me) | User interest profile |
| LLM context | Fixed persona | Dynamic domain context |
| Output model | Daily top 3 | Rolling queue, top 5 unread (30-day window) |
| User actions | None | Read / Skip / Save |
| Users | 1 | Multi-user |
| Delivery | CLI / email | Dashboard + email nudge |

### 5.1 Source Map (Per Domain)

Each domain gets 2–3 curated sources:

- AI/ML → arXiv cs.AI, Twitter/X list, HN filtered
- Startups → TechCrunch RSS, PG essays, Twitter/X VC list
- Business → FT RSS, HBR, Bloomberg headlines
- Politics → Reuters, AP, Politico
- Finance → FT Markets, WSJ headlines

### 5.2 LLM Prompt Adaptation

Domain-aware prompt injection:

> "User follows [Startups, AI]. For each story, explain relevance in context of someone building or investing in early-stage tech companies."

---

## 6. 🏗️ Tech Stack

### Backend
- FastAPI (extend Phase 1)
- Per-domain ingestion modules
- User profile store

### Auth
- Simple email-based (magic link) — no OAuth needed Phase 2

### Storage
- Postgres: users, interest profiles, digest history
- Keep JSON fallback for stories

### LLM
- Claude (primary) — prompt caching per domain batch
- Per-domain system prompt, shared summarization pipeline

### Frontend
- Dashboard (React/Next.js) — primary web experience
  - Queue view: top 5 unread stories, ranked by relevance
  - Per-card actions: Mark Read / Skip / Save
  - Domain filter tabs (show queue filtered by domain)
  - Saved stories view
  - History (all read/skipped stories, searchable)
  - Interest settings (domain selection)
- Design bar: high signal-to-noise, fast to scan, no clutter

### Email
- Resend or SendGrid — transactional, daily digest

---

## 7. 👤 User Flow

### Onboarding (once)
1. Enter email → magic link login
2. Pick 1–5 interest domains
3. Set nudge frequency (daily / weekly)
4. Land on dashboard → queue pre-populated

### Daily Use
1. Open app (or click email nudge)
2. See queue: top 5 unread stories ranked by relevance
3. Per story: read summary → Mark Read / Skip / Save
4. Queue refills silently as stories cleared

### Occasional
- Filter queue by domain tab
- Review Saved stories
- Browse History (all past reads/skips, searchable)
- Adjust domains in Settings

**Key UX principle:** queue always ready, never stale pressure. User opens whenever — finds 5 best unread waiting, not "you missed Monday's digest."

No account management. No social. No sharing.

---

## 8. ❌ Non-Goals (Phase 2)

Do NOT build:

- Personalization beyond domain selection
- Social / sharing features
- Real-time feed
- Mobile app
- Comments or discussion
- Recommendation engine
- Custom source addition by users

---

## 9. 📊 Success Criteria

After 30 days public:

- 50+ active users (open email 4+/7 days)
- Open rate >40%
- 3+ domains covered with quality output
- User feedback: "actionable" not "generic"

---

## 10. ⚠️ Failure Conditions

Kill/rethink if:

- Output quality degrades vs Phase 1 (generalization kills signal)
- Open rate <25% after 2 weeks
- Ops cost per user unsustainable at scale

---

## 11. 🚀 Build Sequence

**Week 1:** Domain source map + multi-domain ingestion
**Week 2:** User profiles + interest-aware LLM prompts
**Week 3:** Email delivery + simple web view
**Week 4:** Onboarding flow + invite 10 beta users

---

## Final Rule

If doesn't make me think:
> "Damn, I should try this today"

Not working.