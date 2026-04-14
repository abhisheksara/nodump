"""Lightweight chat endpoint — RAG over stored content using Claude."""
import logging
from datetime import datetime, timedelta

import anthropic
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db
from db.models import ContentItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

_CHAT_SYSTEM = """You are an AI research assistant helping an AI engineer stay current with the field.
You have access to a curated feed of recent AI papers, blog posts, and news.
Answer questions concisely and cite specific items from the context when relevant.
If you don't know something from the context, say so honestly."""


class ChatRequest(BaseModel):
    message: str
    days: int = 7  # how far back to search


def _retrieve_context(db: Session, days: int, limit: int = 20) -> str:
    """Simple keyword-free retrieval: top-scored items from the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    items = (
        db.execute(
            select(ContentItem)
            .where(ContentItem.processed == True, ContentItem.published_at >= since)  # noqa: E712
            .order_by(ContentItem.relevance_score.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    if not items:
        return "No recent content found in the feed."

    parts = []
    for item in items:
        parts.append(
            f"[{item.source.upper()}] {item.title}\n"
            f"URL: {item.url}\n"
            f"Summary: {item.summary or item.content[:300]}\n"
            f"Why it matters: {item.why_it_matters}\n"
        )
    return "\n---\n".join(parts)


@router.post("/")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    """Non-streaming chat response using RAG over the stored feed."""
    if not settings.anthropic_api_key:
        return {
            "response": "Chat requires ANTHROPIC_API_KEY to be configured.",
            "sources": [],
        }

    context = _retrieve_context(db, body.days)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_message = (
        f"Recent AI content from my research feed (last {body.days} days):\n\n"
        f"{context}\n\n"
        f"User question: {body.message}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _CHAT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        return {"response": response.content[0].text}
    except anthropic.APIError as exc:
        logger.error("Chat LLM error: %s", exc)
        return {"response": f"Error: {exc}"}
