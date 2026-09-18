"""
Tests for ML / GNN Router endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ml_dashboard_html(client: AsyncClient):
    """Verify that the GNN training visualizer dashboard is served."""
    response = await client.get("/api/v1/ml/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "HeteroGraphSAGE" in response.text
    assert "Kurva Konvergensi Model" in response.text


@pytest.mark.asyncio
async def test_ml_graph_topology(client: AsyncClient):
    """Verify that the graph topology endpoint returns nodes and edges."""
    response = await client.get("/api/v1/ml/graph-topology")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0
    assert "stats" in data


@pytest.mark.asyncio
async def test_ml_training_status(client: AsyncClient):
    """Verify that training status returns valid JSON metadata."""
    response = await client.get("/api/v1/ml/training-status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["has_model"] is True


@pytest.mark.asyncio
async def test_ml_visualization_plot(client: AsyncClient):
    """Verify that the generated training visualization plot is retrievable."""
    response = await client.get("/api/v1/ml/visualization-plot")
    assert response.status_code == 200
    assert "image/png" in response.headers.get("content-type", "")
