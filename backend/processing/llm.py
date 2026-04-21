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
