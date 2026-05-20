"""
Cache service — Upstash Redis HTTP client wrapper.
Provides deduplication and TTL caching for OJK data, analysis results, and media search.
Gracefully degrades to no-op if Redis is not configured.
"""
import hashlib
import json
import logging
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-init Redis client
_redis_client = None

# Local thread-safe in-memory fallback cache
_memory_cache: dict[str, tuple[Any, float]] = {}


def _get_client():
    """Return the Upstash Redis async client singleton, or None if not configured."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not settings.UPSTASH_REDIS_URL or not settings.UPSTASH_REDIS_TOKEN:
        logger.warning("⚠️  Upstash Redis not configured — falling back to local In-Memory TTL Cache.")
        return None

    try:
        from upstash_redis.asyncio import Redis  # type: ignore
        _redis_client = Redis(
            url=settings.UPSTASH_REDIS_URL,
            token=settings.UPSTASH_REDIS_TOKEN,
        )
        logger.info("✅ Upstash Redis connected: %s", settings.UPSTASH_REDIS_URL)
        return _redis_client
    except Exception as exc:
        logger.error("Failed to connect to Upstash Redis: %s", exc)
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def cache_get(key: str) -> Any | None:
    """Get a cached value. Falls back to local In-Memory TTL cache if Redis is not configured."""
    client = _get_client()
    if client is None:
        now = time.time()
        if key in _memory_cache:
            val, expiry = _memory_cache[key]
            if now > expiry:
                _memory_cache.pop(key, None)
                return None
            return val
        return None
    try:
        value = await client.get(key)
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value  # Return raw string if not valid JSON
        return value
    except Exception as exc:
        logger.warning("Cache GET failed for key '%s': %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Set a cached value with TTL. Falls back to local In-Memory TTL cache if Redis is not configured."""
    client = _get_client()
    # Populate memory cache for fallback / speed
    _memory_cache[key] = (value, time.time() + ttl_seconds)

    if client is None:
        return True
    try:
        # Always serialize to valid JSON string
        serialized = json.dumps(value)
        await client.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning("Cache SET failed for key '%s': %s", key, exc)
        return False


async def cache_delete(key: str) -> bool:
    """Delete a cached key from both Redis and local memory cache."""
    client = _get_client()
    _memory_cache.pop(key, None)

    if client is None:
        return True
    try:
        await client.delete(key)
        return True
    except Exception as exc:
        logger.warning("Cache DELETE failed for key '%s': %s", key, exc)
        return False


# ── Rate Limiting ──────────────────────────────────────────────────────────────

from collections import defaultdict, deque
_local_rate_limit_hits: dict[str, deque[float]] = defaultdict(deque)

async def check_rate_limit(ip: str, max_requests: int, window_seconds: int) -> bool:
    """
    Check if an IP has exceeded the rate limit. Returns True if allowed, False if blocked.
    Uses Upstash Redis for global limit if available, otherwise falls back to local in-memory limit.
    """
    client = _get_client()
    
    if client is None:
        # Fallback to local in-memory sliding window
        now = time.monotonic()
        hits = _local_rate_limit_hits[ip]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= max_requests:
            return False
        hits.append(now)
        return True

    try:
        key = f"sentra:ratelimit:{ip}"
        # Fixed window rate limiting using Redis
        current = await client.incr(key)
        if current == 1:
            await client.expire(key, window_seconds)
        
        if current > max_requests:
            return False
        return True
    except Exception as exc:
        logger.warning("Rate limit check failed for IP '%s', allowing request. Error: %s", ip, exc)
        return True


# ── Key Builders ──────────────────────────────────────────────────────────────

import re

def _smart_normalize_text(text: str) -> str:
    """
    Aggressively normalizes text for caching by:
    1. Lowercasing
    2. Removing all non-alphanumeric characters (including emojis and punctuation)
    3. Collapsing multiple spaces into a single space
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def make_analysis_key(raw_text: str) -> str:
    """
    SHA-256 hash of smartly normalized input text for analysis deduplication.
    Identical inputs (ignoring emojis/punctuation) return the same cache key.
    """
    clean_text = _smart_normalize_text(raw_text)
    digest = hashlib.sha256(clean_text.encode()).hexdigest()
    return f"sentra:analysis:{digest}"


def make_ojk_key(entity_name: str) -> str:
    """Cache key for OJK entity lookup."""
    safe_name = entity_name.strip().lower().replace(" ", "_")
    return f"sentra:ojk:{safe_name}"


def make_media_key(entity_name: str) -> str:
    """Cache key for RSS media search results."""
    digest = hashlib.md5(entity_name.strip().lower().encode()).hexdigest()
    return f"sentra:media:{digest}"


def make_whois_key(domain: str) -> str:
    """Cache key for WHOIS / domain intel."""
    return f"sentra:whois:{domain.lower()}"


# ── API Key Rotation State ───────────────────────────────────────────────────

async def mark_primary_api_key_exhausted() -> None:
    """
    Mark the primary Gemini API key as exhausted (429 Rate Limit Reached).
    It will be disabled for 24 hours (86400 seconds), forcing fallback to backup key.
    """
    logger.error("🚨 PRIMARY GEMINI API KEY EXHAUSTED. Switching to BACKUP for 24 hours.")
    await cache_set("sentra:api_key_exhausted", True, ttl_seconds=86400)


async def is_primary_api_key_exhausted() -> bool:
    """
    Check if the primary API key is currently in cooldown mode.
    """
    val = await cache_get("sentra:api_key_exhausted")
    return bool(val)
