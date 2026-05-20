"""
Media Search Service — RSS feed intelligence.
PRD Check #20: Cek pemberitaan media (berita negatif tentang nama entitas).

Sources (free RSS, no API key):
  - Detik Finance, Kompas Money, Tempo Bisnis, CNBC Indonesia
  - Diperkuat Gemini Search Grounding untuk pencarian real-time (via SENTRA)
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import httpx

from app.config import settings
from app.services.cache_service import cache_get, cache_set, make_media_key

logger = logging.getLogger(__name__)

_RSS_FEEDS = [
    ("Detik Finance",   "https://rss.detik.com/index.php/detikfinance"),
    ("Kompas Money",    "https://rss.kompas.com/money"),
    ("Tempo Bisnis",    "https://rss.tempo.co/bisnis"),
    ("CNBC Indonesia",  "https://www.cnbcindonesia.com/rss"),
]

_SCAM_KEYWORDS = [
    "penipuan", "scam", "ilegal", "bodong", "ojk", "satgas", "korban",
    "investasi palsu", "pinjol ilegal", "robot trading palsu", "rug pull",
    "gagal bayar", "kabur", "ditangkap", "diblokir", "tersangka",
]


@dataclass
class NewsItem:
    title: str
    url: str
    published: str | None
    source: str
    is_negative: bool


async def search_entity_in_news(entity_name: str) -> list[NewsItem]:
    """
    Search Indonesian media RSS feeds for news about an entity.
    Returns list of relevant news items, flagging negative/scam-related coverage.
    """
    if not entity_name or len(entity_name.strip()) < 3:
        return []

    cache_key = make_media_key(entity_name)
    cached = await cache_get(cache_key)
    if cached:
        return [NewsItem(**item) for item in cached]

    results: list[NewsItem] = []
    entity_lower = entity_name.strip().lower()

    # Fetch all RSS feeds in parallel
    import asyncio
    tasks = [
        asyncio.create_task(_fetch_rss_feed(name, url, entity_lower))
        for name, url in _RSS_FEEDS
    ]
    feed_results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in feed_results:
        if isinstance(res, list):
            results.extend(res)

    # Cache results
    ttl = settings.MEDIA_CACHE_TTL_HOURS * 3600
    await cache_set(cache_key, [item.__dict__ for item in results], ttl_seconds=ttl)
    return results


async def _fetch_rss_feed(source_name: str, feed_url: str, entity_lower: str) -> list[NewsItem]:
    """Fetch a single RSS feed and filter for entity mentions."""
    try:
        import feedparser  # type: ignore
        import asyncio

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(feed_url)
            if resp.status_code != 200:
                return []

        feed = await asyncio.to_thread(feedparser.parse, resp.text)
        items = []

        for entry in feed.entries[:50]:
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""
            content = (title + " " + summary).lower()

            if entity_lower not in content:
                continue

            is_negative = any(kw in content for kw in _SCAM_KEYWORDS)
            published = None
            if hasattr(entry, "published"):
                published = entry.published

            items.append(NewsItem(
                title=title,
                url=getattr(entry, "link", feed_url),
                published=published,
                source=source_name,
                is_negative=is_negative,
            ))

        return items
    except Exception as exc:
        logger.debug("RSS feed '%s' failed (non-fatal): %s", source_name, exc)
        return []
