"""
Tests for GNN fraud detection integration and Render Free Plan circuit breaker.
"""
from unittest.mock import patch
import pytest
from ml.gnn_service import gnn_service


@pytest.mark.asyncio
async def test_gnn_service_initialization():
    assert hasattr(gnn_service, "get_risk_boost")
    assert hasattr(gnn_service, "load_model")


@pytest.mark.asyncio
async def test_gnn_disabled_by_env_returns_zero():
    """Verify that when ENABLE_GNN=false (Render Free Plan mode), boost is 0.0 with zero overhead."""
    with patch("ml.constants.ENABLE_GNN", False):
        boost = await gnn_service.get_risk_boost("Ini penawaran investasi bodong rekening BCA 1234567890")
        assert boost == 0.0


@pytest.mark.asyncio
async def test_gnn_boost_range_when_enabled():
    """Verify that when ENABLE_GNN=true, boost is safely bounded between 0.0 and 25.0."""
    with patch("ml.constants.ENABLE_GNN", True):
        boost = await gnn_service.get_risk_boost("Ini penawaran investasi bodong.")
        assert 0.0 <= boost <= 25.0


@pytest.mark.asyncio
async def test_gnn_circuit_breaker_on_exception():
    """Verify that any exception inside inference returns 0.0 without crashing."""
    with patch("ml.constants.ENABLE_GNN", True):
        with patch.object(gnn_service, "load_model", side_effect=RuntimeError("Simulated OOM")):
            boost = await gnn_service.get_risk_boost("Test text")
            assert boost == 0.0
