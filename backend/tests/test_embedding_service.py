"""
Tests for Gemini Embedding Service (gemini-embedding-001).
"""
import pytest
from app.services.embedding_service import embedding_service


@pytest.mark.asyncio
async def test_embed_single_text():
    """Verify gemini-embedding-001 produces a 768-dimensional dense vector."""
    vec = await embedding_service.embed_text("Penawaran investasi profit harian 20% dijamin aman.")
    assert isinstance(vec, list)
    assert len(vec) == 768
    assert all(isinstance(x, float) for x in vec)


@pytest.mark.asyncio
async def test_embed_caching():
    """Verify repeated calls for the exact same text retrieve from in-memory cache."""
    text = "Tes caching embedding cepat."
    vec1 = await embedding_service.embed_text(text)
    vec2 = await embedding_service.embed_text(text)
    assert vec1 == vec2


@pytest.mark.asyncio
async def test_embed_empty_text():
    """Verify empty text returns zero vector without failing."""
    vec = await embedding_service.embed_text("   ")
    assert len(vec) == 768
    assert all(x == 0.0 for x in vec)
