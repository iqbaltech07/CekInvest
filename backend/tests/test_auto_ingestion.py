import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockRedFlag:
    def __init__(self, category="Robot Trading Scam"):
        self.category = category
        self.severity = MagicMock(value="HIGH")
        self.confidence = 0.95


class MockAnalysis:
    def __init__(self, risk_level="HIGH", risk_score=85, input_type="CHAT"):
        self.id = "test_analysis_id_001"
        self.riskLevel = MagicMock(value=risk_level)
        self.riskScore = risk_score
        self.inputType = MagicMock(value=input_type)
        self.redFlags = [MockRedFlag()]


@pytest.mark.asyncio
async def test_flywheel_triggers_on_critical():
    from app.services.analysis_service import _auto_feed_to_threat_intelligence
    mock_db = AsyncMock()
    mock_db.userreport.find_first = AsyncMock(return_value=None)
    mock_db.userreport.create = AsyncMock(return_value=MagicMock(id="rpt_001"))
    analysis = MockAnalysis(risk_level="CRITICAL", risk_score=92)
    with patch("app.services.embedding_service.embedding_service.embed_text", new_callable=AsyncMock) as mock_embed,          patch("app.services.vector_store.vector_store.upsert_report_embedding", new_callable=AsyncMock) as mock_upsert,          patch("ml.utils.extract_phone_numbers", return_value=[]),          patch("ml.utils.extract_bank_accounts", return_value=[("BCA","1234567890")]),          patch("ml.utils.extract_domains", return_value=[]):
        mock_embed.return_value = [0.1] * 768
        await _auto_feed_to_threat_intelligence(analysis, "scam text profit 50% per hari", mock_db)
        mock_db.userreport.create.assert_called_once()
        mock_embed.assert_called_once()
        mock_upsert.assert_called_once()


@pytest.mark.asyncio
async def test_flywheel_skips_low_risk():
    from app.services.analysis_service import _auto_feed_to_threat_intelligence
    mock_db = AsyncMock()
    analysis = MockAnalysis(risk_level="LOW", risk_score=35)
    with patch("app.services.embedding_service.embedding_service.embed_text", new_callable=AsyncMock) as mock_embed:
        await _auto_feed_to_threat_intelligence(analysis, "Safe text", mock_db)
        mock_embed.assert_not_called()


@pytest.mark.asyncio
async def test_flywheel_non_fatal():
    from app.services.analysis_service import _auto_feed_to_threat_intelligence
    mock_db = AsyncMock()
    mock_db.userreport.find_first = AsyncMock(side_effect=Exception("DB lost"))
    analysis = MockAnalysis(risk_level="CRITICAL", risk_score=95)
    await _auto_feed_to_threat_intelligence(analysis, "Scam content", mock_db)
