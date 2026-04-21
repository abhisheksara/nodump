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
