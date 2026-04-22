# 💡 Ideas & Reminders

Backlog of product ideas to revisit. Not in current scope — add to PRD when ready to build.

---

## 1. Free-form interest refinement (Phase 2 → V2)

**What:** Let users add descriptive sub-interests within a category.
- Instead of just selecting "AI / ML" as a chip
- User can optionally add: "research in tabular data generation", "AI-assisted productivity tools", "SaaS startups using AI"
- LLM uses this description directly as prompt context for relevance scoring

**Why it's better:**
- Much higher signal — niche description >> broad category
- Matches how people actually think about interests
- Competitive differentiator

**Why not now:**
- Blank text box kills onboarding conversion
- Free-form → no prompt cache sharing → LLM cost scales per-user
- Source routing harder (can't hardcode sources per free-form topic)
- Need broader ingestion coverage first

**How to ship it:**
- Ship predefined category chips first (V1)
- Add optional refinement text input per selected category — show suggestions/examples as placeholder text
- Use category → source routing, refinement → LLM prompt context injection
- Embedding-based semantic match for ranking (vs keyword match in V1)

**Onboarding UX:**
- Step 1: Pick categories (chips)
- Step 2 (optional): "Want more specific results? Describe what you care about within [category]" with example suggestions shown

---

## 2. (add more ideas here)
