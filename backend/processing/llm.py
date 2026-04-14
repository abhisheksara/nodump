"""LLM processing via Claude API (Anthropic).

Uses prompt caching for the system prompt so repeated calls are cheap.
"""
import json
import logging
import re

import anthropic

from config import settings

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# System prompt is cached — only sent once per cache TTL (5 min by default)
_SYSTEM_PROMPT = """You are an AI research curator for senior AI engineers.
Your job is to evaluate content and explain its relevance to practitioners working on LLMs, agents, and applied ML.
Always respond with valid JSON only — no markdown fences, no extra text."""

_USER_PROMPT_TEMPLATE = """User profile:
- Role: AI engineer / data scientist
- Interests: {interests}

Content to evaluate:
Title: {title}
Source: {source}
Author: {author}

{content}

Respond with ONLY this JSON (no markdown, no extra text):
{{
  "summary": "<3-5 sentence summary>",
  "why_it_matters": "<2-3 sentences explaining why this matters specifically to an AI engineer working on LLMs and agents>",
  "relevance_score": <float 0.0-1.0>
}}"""


def enrich_item(item: dict) -> dict:
    """Call Claude to get summary, why_it_matters, and relevance_score.

    Returns the original item dict updated with LLM fields.
    Falls back gracefully on error.
    """
    if not settings.anthropic_api_key:
        # No API key — return stub enrichment
        return {
            **item,
            "summary": item["content"][:300],
            "why_it_matters": "Configure ANTHROPIC_API_KEY to enable personalized relevance explanations.",
            "relevance_score": 0.5,
        }

    client = _get_client()
    prompt = _USER_PROMPT_TEMPLATE.format(
        interests=settings.user_interests,
        title=item["title"],
        source=item["source"],
        author=item.get("author", "unknown"),
        content=item["content"][:3000],
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # cache system prompt
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        return {
            **item,
            "summary": parsed.get("summary", "")[:1000],
            "why_it_matters": parsed.get("why_it_matters", "")[:500],
            "relevance_score": float(parsed.get("relevance_score", 0.5)),
        }
    except (json.JSONDecodeError, KeyError, anthropic.APIError) as exc:
        logger.warning("LLM enrichment failed for '%s': %s", item.get("title"), exc)
        return {
            **item,
            "summary": item["content"][:400],
            "why_it_matters": "",
            "relevance_score": 0.3,
        }
