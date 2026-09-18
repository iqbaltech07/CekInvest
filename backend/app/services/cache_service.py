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
_redis_disabled_until = 0.0

# Local thread-safe in-memory fallback cache
_memory_cache: dict[str, tuple[Any, float]] = {}


def _get_client():
    """Return the Upstash Redis async client singleton, or None if not configured or circuit breaker open."""
    global _redis_client, _redis_disabled_until
    if time.time() < _redis_disabled_until:
        return None

    if _redis_client is not None:
        return _redis_client

    if not settings.UPSTASH_REDIS_URL or not settings.UPSTASH_REDIS_TOKEN:
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
        _redis_disabled_until = time.time() + 60.0
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

async def cache_get(key: str) -> Any | None:
    """Get a cached value. Falls back to local In-Memory TTL cache if Redis is not configured or slow/unreachable."""
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
        # Protect against slow/broken DNS with a strict 1.5 second timeout
        value = await asyncio.wait_for(client.get(key), timeout=1.5)
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value  # Return raw string if not valid JSON
        return value
    except Exception as exc:
        logger.warning("Cache GET failed for key '%s': %s. Disabling Redis for 5 minutes.", key, exc)
        global _redis_client, _redis_disabled_until
        _redis_client = None
        _redis_disabled_until = time.time() + 300.0
        # Return fallback from memory cache if present
        if key in _memory_cache:
            val, expiry = _memory_cache[key]
            if time.time() <= expiry:
                return val
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Set a cached value with TTL. Falls back to local In-Memory TTL cache if Redis is not configured or slow/unreachable."""
    client = _get_client()
    # Populate memory cache immediately for zero-latency local retrieval
    _memory_cache[key] = (value, time.time() + ttl_seconds)

    if client is None:
        return True
    try:
        # Always serialize to valid JSON string
        serialized = json.dumps(value)
        await asyncio.wait_for(client.set(key, serialized, ex=ttl_seconds), timeout=1.5)
        return True
    except Exception as exc:
        logger.warning("Cache SET failed for key '%s': %s. Disabling Redis for 5 minutes.", key, exc)
        global _redis_client, _redis_disabled_until
        _redis_client = None
        _redis_disabled_until = time.time() + 300.0
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

def make_api_key_hash(api_key: str) -> str:
    """Return a short non-reversible SHA-256 identifier for cache tracking."""
    return hashlib.sha256(api_key.strip().encode()).hexdigest()[:12]


async def mark_api_key_exhausted(api_key: str, cooldown_seconds: int = 1800) -> None:
    """
    Mark a specific Gemini API key as exhausted (429, Quota, or Auth limit).
    Defaults to 30 minutes cooldown (1800s).
    """
    if not api_key:
        return
    khash = make_api_key_hash(api_key)
    masked = f"...{api_key[-6:]}" if len(api_key) >= 6 else "***"
    logger.warning(
        "🚨 Gemini API key [%s] marked EXHAUSTED for %d seconds. Switching to next fallback key.",
        masked,
        cooldown_seconds,
    )
    await cache_set(f"sentra:key_exhausted:{khash}", True, ttl_seconds=cooldown_seconds)

    # Maintain backward compatibility with legacy primary flag
    try:
        from app.config import settings
        if api_key.strip() == settings.GEMINI_API_KEY.strip():
            await cache_set("sentra:api_key_exhausted", True, ttl_seconds=cooldown_seconds)
    except Exception:
        pass


async def is_api_key_exhausted(api_key: str) -> bool:
    """
    Check if a specific Gemini API key is currently in cooldown.
    """
    if not api_key:
        return False
    khash = make_api_key_hash(api_key)
    val = await cache_get(f"sentra:key_exhausted:{khash}")
    if val:
        return True

    try:
        from app.config import settings
        if api_key.strip() == settings.GEMINI_API_KEY.strip():
            legacy_val = await cache_get("sentra:api_key_exhausted")
            return bool(legacy_val)
    except Exception:
        pass

    return False


async def mark_primary_api_key_exhausted(cooldown_seconds: int = 1800) -> None:
    """Legacy alias: marks primary API key as exhausted."""
    from app.config import settings
    await mark_api_key_exhausted(settings.GEMINI_API_KEY, cooldown_seconds=cooldown_seconds)


async def is_primary_api_key_exhausted() -> bool:
    """Legacy alias: checks if primary API key is currently exhausted."""
    from app.config import settings
    return await is_api_key_exhausted(settings.GEMINI_API_KEY)
