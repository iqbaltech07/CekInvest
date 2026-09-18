"""
Tests for ML Dataset Export and Database-to-Graph Synchronization.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_export_dataset_csv(client: AsyncClient):
    """Verify that export dataset returns a downloadable CSV with all reports."""
    response = await client.get("/api/v1/ml/export-dataset?format=csv", timeout=30.0)
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "cekinvest_dataset_" in response.headers.get("content-disposition", "")
    content = response.text
    lines = content.strip().split("\n")
    # Must have header + at least 100 rows
    assert len(lines) > 50
    assert "text,is_scam,category" in lines[0]


@pytest.mark.asyncio
async def test_export_dataset_json(client: AsyncClient):
    """Verify that export dataset returns a downloadable JSON array."""
    response = await client.get("/api/v1/ml/export-dataset?format=json", timeout=30.0)
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 50
    first = data[0]
    assert "text" in first
    assert "is_scam" in first


@pytest.mark.asyncio
async def test_sync_database_graph(client: AsyncClient):
    """Verify that database reports can be directly synchronized into the graph."""
    response = await client.post("/api/v1/ml/sync-database-graph", timeout=60.0)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_reports"] > 50
