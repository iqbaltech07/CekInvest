"""
Unit tests for Gemini API Key fallback and model rotation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings
from app.services.cache_service import (
    is_api_key_exhausted,
    mark_api_key_exhausted,
    cache_delete,
    make_api_key_hash,
)
from app.services.sentra_service import is_key_error, is_retryable_error, SentraService
from app.services.embedding_service import EmbeddingService


def test_settings_get_gemini_api_keys():
    """Verify get_gemini_api_keys parses comma-separated keys and deduplicates."""
    keys = settings.get_gemini_api_keys()
    assert isinstance(keys, list)
    assert len(keys) >= 2
    assert settings.GEMINI_API_KEY in keys
    assert settings.GEMINI_API_KEY_BACKUP_1 in keys


def test_settings_get_sentra_models():
    """Verify get_sentra_models returns prioritized list including 2.5-flash fallback."""
    models = settings.get_sentra_models()
    assert isinstance(models, list)
    assert len(models) >= 3
    assert "gemini-2.5-flash" in models


def test_error_classification():
    """Verify error detection identifies 429, quota, 401, 403, and invalid keys."""
    assert is_key_error(Exception("429 RESOURCE_EXHAUSTED: quota exceeded")) is True
    assert is_key_error(Exception("API_KEY_INVALID: Please pass a valid API key")) is True
    assert is_key_error(Exception("403 Forbidden: billing not enabled")) is True
    assert is_key_error(Exception("401 Unauthorized")) is True
    assert is_key_error(Exception("SyntaxError: unexpected token")) is False

    assert is_retryable_error(Exception("503 Service Unavailable")) is True
    assert is_retryable_error(Exception("Deadline exceeded")) is True
    assert is_retryable_error(Exception("ValueError: invalid param")) is False


@pytest.mark.asyncio
async def test_api_key_exhaustion_cache():
    """Verify marking a key as exhausted registers in cooldown state."""
    test_key = "AIzaSyTestMockKey1234567890"
    khash = make_api_key_hash(test_key)
    
    # Ensure clean state
    await cache_delete(f"sentra:key_exhausted:{khash}")
    assert await is_api_key_exhausted(test_key) is False

    # Mark exhausted for 60 seconds
    await mark_api_key_exhausted(test_key, cooldown_seconds=60)
    assert await is_api_key_exhausted(test_key) is True

    # Cleanup
    await cache_delete(f"sentra:key_exhausted:{khash}")


@pytest.mark.asyncio
async def test_sentra_fallback_on_key_error():
    """Verify that when primary key encounters 429/quota, Sentra switches to backup key."""
    service = SentraService()
    
    mock_primary_client = MagicMock()
    mock_primary_client.aio.models.generate_content = AsyncMock(
        side_effect=Exception("429 ResourceExhausted: Quota exceeded for project")
    )

    mock_backup_client = MagicMock()
    mock_backup_response = MagicMock()
    mock_backup_response.text = '{"risk_score": 85, "risk_level": "HIGH", "safe_to_invest": false, "summary": "Penipuan terdeteksi", "explanation": "Indikator penipuan tinggi", "red_flags": [], "emotion_signals": [], "trap_questions": []}'
    mock_backup_client.aio.models.generate_content = AsyncMock(return_value=mock_backup_response)

    async def fake_get_keys():
        return [("KEY_PRIMARY_FAKE", "PRIMARY"), ("KEY_BACKUP_FAKE", "BACKUP_1")]

    with patch.object(service, "_get_ordered_api_keys", side_effect=fake_get_keys), \
         patch("app.services.sentra_service.genai.Client") as mock_genai:
        
        # Return primary client first, then backup client
        mock_genai.side_effect = [mock_primary_client, mock_backup_client]

        result = await service.analyze("Investasi cuan 50% sehari")
        
        assert result.risk_score == 85
        assert result.summary == "Penipuan terdeteksi"
        assert result.safe_to_invest is False
        # Primary was called, failed, then backup was called and succeeded
        assert mock_primary_client.aio.models.generate_content.called
        assert mock_backup_client.aio.models.generate_content.called


@pytest.mark.asyncio
async def test_embedding_fallback_on_key_error():
    """Verify that when primary key encounters 429/quota, EmbeddingService switches to backup key."""
    service = EmbeddingService()

    mock_primary_client = MagicMock()
    mock_primary_client.aio.models.embed_content = AsyncMock(
        side_effect=Exception("429 ResourceExhausted: rate limit reached")
    )

    mock_backup_client = MagicMock()
    mock_backup_response = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * 768
    mock_backup_response.embeddings = [mock_embedding]
    mock_backup_client.aio.models.embed_content = AsyncMock(return_value=mock_backup_response)

    with patch("app.config.Settings.get_gemini_api_keys", return_value=["KEY_PRIM", "KEY_BACKUP"]), \
         patch("app.services.embedding_service.genai.Client") as mock_genai:
        
        mock_genai.side_effect = [mock_primary_client, mock_backup_client]

        result = await service.embed_text("Tes fallback embedding unik 98765")
        assert len(result) == 768
        assert result[0] == pytest.approx(0.1)
        assert mock_primary_client.aio.models.embed_content.called
        assert mock_backup_client.aio.models.embed_content.called
