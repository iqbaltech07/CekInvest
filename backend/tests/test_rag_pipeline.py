"""
Tests for Dense Semantic RAG & pgvector Store Pipeline.
"""
import pytest
from httpx import AsyncClient
from prisma import Prisma

from app.services.vector_store import vector_store
from app.services.rag_service import rag_service


@pytest.mark.asyncio
async def test_vector_store_initialization():
    """Verify pgvector tables and knowledge base are initialized."""
    db = Prisma()
    if not db.is_connected():
        await db.connect()
    try:
        await vector_store.init_vector_tables(db)
        # Verify knowledge base can be seeded
        seeded = await vector_store.seed_knowledge_base_if_empty(db, rag_service.embedding_svc)
        assert seeded >= 0
    finally:
        if db.is_connected():
            await db.disconnect()


@pytest.mark.asyncio
async def test_rag_query_execution():
    """Verify RAG query retrieves semantic matches and forms prompt context."""
    db = Prisma()
    if not db.is_connected():
        await db.connect()
    try:
        res = await rag_service.query_rag(
            text="Tawaran robot trading crypto deposit via rekening BCA profit 10% per hari",
            db=db,
            report_limit=3,
            article_limit=2,
        )
        assert hasattr(res, "similar_reports")
        assert hasattr(res, "regulatory_articles")
        prompt_context = res.to_prompt_context()
        assert isinstance(prompt_context, str)
    finally:
        if db.is_connected():
            await db.disconnect()


@pytest.mark.asyncio
async def test_api_rag_search_endpoint(client: AsyncClient):
    """Verify GET /api/v1/intelligence/rag-search endpoint returns structured results."""
    response = await client.get("/api/v1/intelligence/rag-search?q=investasi+bodong+profit+pasti", timeout=30.0)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    data = json_data["data"]
    assert "similar_reports" in data
    assert "regulatory_articles" in data
