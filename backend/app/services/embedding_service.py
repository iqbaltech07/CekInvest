"""
Semantic Embedding Service using Google Gemini (gemini-embedding-001).
Produces 768-dimensional dense semantic vector representations for RAG and Graph similarity.
"""
import asyncio
import logging
from typing import List, Optional
from functools import lru_cache

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating high-dimensional dense semantic embeddings
    using Google's gemini-embedding-001 model with flexible output dimensionality.
    """

    def __init__(self) -> None:
        self.model = getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")
        self.dim = getattr(settings, "EMBEDDING_DIM", 768)
        self._client: Optional[genai.Client] = None
        self._cache: dict[str, list[float]] = {}
        self._max_cache_size = 2000

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """
        Generates a 768-dimensional vector embedding for a single text string.
        Utilizes multi-layer caching and multi-key fallback rotation.
        """
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * self.dim

        # Check in-memory fast cache first
        cache_key = clean_text[:300]
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check L2 Multi-Layer Cache via cache_service
        import hashlib
        emb_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        emb_cache_key = f"emb:{emb_hash}"
        try:
            from app.services.cache_service import cache_get, cache_set
            cached_emb = await cache_get(emb_cache_key)
            if cached_emb and isinstance(cached_emb, list):
                self._cache[cache_key] = cached_emb
                return cached_emb
        except Exception:
            pass

        from app.services.cache_service import is_api_key_exhausted, mark_api_key_exhausted

        all_keys = settings.get_gemini_api_keys()
        if not all_keys:
            all_keys = [settings.GEMINI_API_KEY]

        active_keys = []
        cooldown_keys = []
        for k in all_keys:
            if await is_api_key_exhausted(k):
                cooldown_keys.append(k)
            else:
                active_keys.append(k)

        candidate_keys = active_keys if active_keys else cooldown_keys
        last_exception = None

        for api_key in candidate_keys:
            masked = f"...{api_key[-6:]}" if len(api_key) >= 6 else "***"
            try:
                client = genai.Client(api_key=api_key)
                response = await client.aio.models.embed_content(
                    model=self.model,
                    contents=clean_text,
                    config=types.EmbedContentConfig(output_dimensionality=self.dim),
                )
                embedding = [float(v) for v in response.embeddings[0].values]

                # Cache management (L1 in-memory)
                if len(self._cache) >= self._max_cache_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                self._cache[cache_key] = embedding

                # Cache management (L2 persistent cache — 7 days TTL)
                try:
                    await cache_set(emb_cache_key, embedding, ttl_seconds=86400 * 7)
                except Exception:
                    pass

                return embedding

            except Exception as exc:
                last_exception = exc
                err_msg = str(exc).lower()
                is_key_err = any(term in err_msg for term in (
                    "429", "resource_exhausted", "quota", "rate limit", "401", "403",
                    "permission_denied", "api_key_invalid", "unauthenticated"
                ))
                if is_key_err:
                    logger.warning(
                        "gemini-embedding-001 failed on key [%s]: %s. Marking key in cooldown.",
                        masked,
                        exc,
                    )
                    await mark_api_key_exhausted(api_key)
                else:
                    logger.warning(
                        "gemini-embedding-001 call failed on key [%s]: %s. Trying next key...",
                        masked,
                        exc,
                    )

        if last_exception:
            raise last_exception
        return [0.0] * self.dim

    async def embed_texts(self, texts: list[str], batch_size: int = 15) -> list[list[float]]:
        """
        Generates vector embeddings for a list of texts in controlled batches.
        """
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            tasks = [self.embed_text(t) for t in chunk]
            batch_embeddings = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(batch_embeddings)
            if i + batch_size < len(texts):
                await asyncio.sleep(0.2)  # Avoid burst quota limits
        return results


# Global singleton instance
embedding_service = EmbeddingService()
