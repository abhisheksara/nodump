# 📄 PRD: Personal AI Signal Engine (Phase 1 — Single User: Me)

---

## 1. 🎯 Goal

Build a **personal AI research filter** that:

- Reduces my daily AI content consumption time from ~1–2 hours → <15 minutes
- Surfaces only **high-leverage insights**
- Helps me **decide what to act on**, not just read

---

## 2. 👤 User (Only One)

**Abhishek (me):**
- Senior Data Scientist
- Interested in:
  - LLMs
  - Agents / multi-agent systems
  - Applied ML systems
  - Things that help me build faster or smarter

---

## 3. 🔥 Core Problem

> I consume a lot of AI content but:
- Most of it is noise
- I don’t know what is actually worth my time
- I rarely convert reading into action

---

## 4. 💡 Core Value Proposition

> “In 5 minutes, I know what matters in AI today — and what I should do about it.”

---

## 5. 🧱 MVP Scope (Strict)

### 5.1 Daily Output (THE PRODUCT)

Every day, generate:

## “Top 3 AI Things That Matter (For Me)”

Each item must follow this structure:

---

### 🧩 Output Format

Title

What happened (2–3 lines max)

Why this matters (specific to MY interests)

What I should do (MANDATORY — must be actionable)

Relevance (High / Medium / Ignore)

---

### 🚨 Quality Bar

If the output sounds like:
> “This is relevant to your interest in LLMs”

→ It is useless.

If it tells me:
> “Try this in your agent pipeline to reduce failures”

→ It is valuable.

---

## 6. 🔍 Data Sources (Phase 1)

Start with **ONE source only**:

Option A:
- arXiv (cs.AI, cs.LG)

Option B:
- Curated Twitter list (~50 high-signal accounts)

👉 Pick ONE. No multi-source aggregation yet.

---

## 7. ⚙️ Pipeline (Simple, Daily Batch)

1. Fetch ~50–100 items  
2. Deduplicate  
3. Run LLM to generate:
   - Summary
   - Why it matters (personalized)
   - What I should do  
4. Rank using simple heuristic:
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
- Postgres or even JSON initially

### Frontend (Optional)
- Not required

---

## 9. 📬 Delivery

Choose ONE:

- Email to myself (preferred)
- OR simple web page
- OR even CLI output

👉 Optimize for **consumption speed**, not UI

---

## 10. ❌ Explicit Non-Goals

Do NOT build:

- Chat interface  
- Feedback system  
- Multi-user support  
- Personalization engine  
- Real-time updates  
- Fancy UI  

If I build these, I am procrastinating.

---

## 11. 📊 Success Criteria (Personal)

After 7 days:

- I consistently check it daily
- It saves me time vs Twitter/arXiv
- At least 2–3 insights led to:
  - Trying something new
  - Changing how I build

---

## 12. ⚠️ Failure Conditions

Kill or rethink if:

- Output feels generic
- I ignore it after 3–4 days
- It doesn’t change what I do

---

## 13. 🚀 Execution Plan (Fast)

Day 1:
- Setup ingestion + basic pipeline

Day 2:
- Add LLM generation (summary + why + action)

Day 3:
- Ranking + output formatting

Day 4–7:
- Iterate on prompt quality manually

---

## 14. 🧠 Key Insight (Important)

This is NOT a summarization tool.

This is:
> A system that forces me to convert information → action

---

## 15. 🔄 Phase 2 (Only if Phase 1 Works)

Consider expanding ONLY if:

- I use it daily
- I feel a real advantage

Then add:
- Multi-source ingestion
- Light personalization
- Distribution

---

## Final Rule

If this does not make me think:
> “Damn, I should try this today”

Then it is not working.