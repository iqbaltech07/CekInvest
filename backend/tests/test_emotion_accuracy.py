"""
Tests for Indonesian Scam Slang Dictionary, Negation Guard,
Dynamic Confidence Calculation, and Multi-Signal Risk Scorer Boost.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.schemas.analysis import EmotionSignalType, SentraEmotionSignal, EmotionSignalResponse
from app.services.emotion_signal_service import (
    normalize_emotion_signals,
    _is_negated,
    _KEYWORD_RULES,
)
from app.services.risk_scorer import boost_score_from_patterns


def test_slang_detection_coverage():
    """Verify that Indonesian Telegram/WA scam slang triggers proper emotion signals."""
    sample_text = (
        "Halo kak, mau sampai kapan jadi penonton? "
        "Titip dana trading modal receh hasil sultan amanah pasti profit 30% per hari! "
        "Slot tipis sisa 3 kuota lagi ya, gercep sekarang juga. "
        "Alhamdulillah barusan cair 15 juta ke rekening BCA member VIP kami!"
    )
    
    signals = normalize_emotion_signals(sample_text)
    detected_types = {s.type for s in signals if s.detected}
    
    # Must catch multiple manipulation tactics
    assert EmotionSignalType.URGENCY in detected_types
    assert EmotionSignalType.FAKE_SCARCITY in detected_types
    assert EmotionSignalType.UNREALISTIC_RETURN in detected_types
    assert EmotionSignalType.SOCIAL_PROOF_MANIPULATION in detected_types
    assert EmotionSignalType.EMOTIONAL_PRESSURE in detected_types


def test_negation_guard_prevents_false_positives():
    """Educational or warning texts containing negative prefixes must not trigger detections."""
    warning_text = (
        "Peringatan Resmi Satgas PASTI OJK: "
        "Waspada modus penipuan investasi ilegal di Telegram! "
        "Jangan percaya tawaran titip dana yang mengklaim pasti profit tanpa risiko. "
        "Hindari pihak yang memaksa transfer dengan alasan slot terbatas atau kuota menipis. "
        "OJK tidak pernah memberikan jaminan keuntungan pasti."
    )
    
    content_lower = warning_text.lower()
    titip_idx = content_lower.find("titip dana")
    profit_idx = content_lower.find("pasti profit")
    slot_idx = content_lower.find("slot terbatas")
    
    # Individual negation check
    assert titip_idx != -1
    assert _is_negated(content_lower, titip_idx) is True
    assert profit_idx != -1
    assert _is_negated(content_lower, profit_idx) is True
    assert slot_idx != -1
    assert _is_negated(content_lower, slot_idx) is True

    signals = normalize_emotion_signals(warning_text)
    # Since all mentions are explicitly warned against / negated, none should be falsely flagged as active scam tactics
    unrealistic = next(s for s in signals if s.type == EmotionSignalType.UNREALISTIC_RETURN)
    assert unrealistic.detected is False or len(unrealistic.examples) == 0


def test_dynamic_confidence_calculation():
    """Confidence score must scale dynamically based on evidence count and intensity."""
    # Signal with 1 evidence
    sig_low = EmotionSignalResponse(
        id="sig-1",
        signalType=EmotionSignalType.URGENCY,
        detected=True,
        description="Tekanan waktu",
        examples=["buruan"],
        confidenceScore=0.0,
    )
    assert 0.40 <= sig_low.confidenceScore <= 0.65
    assert sig_low.confidenceLevel in ("LOW", "MEDIUM")

    # Signal with 4 evidences
    sig_high = EmotionSignalResponse(
        id="sig-2",
        signalType=EmotionSignalType.URGENCY,
        detected=True,
        description="Tekanan waktu berulang",
        examples=["buruan", "sekarang juga", "hari ini saja", "kesempatan terakhir"],
        confidenceScore=0.0,
    )
    assert sig_high.confidenceScore > sig_low.confidenceScore
    assert sig_high.confidenceScore >= 0.75
    assert sig_high.confidenceLevel == "HIGH"

    # Unrealistic return with high percentage (e.g. 50% per hari)
    sig_return = EmotionSignalResponse(
        id="sig-3",
        signalType=EmotionSignalType.UNREALISTIC_RETURN,
        detected=True,
        description="Janji keuntungan ekstrem",
        examples=["profit 50% per hari"],
        confidenceScore=0.0,
    )
    assert sig_return.confidenceScore >= 0.85
    assert sig_return.confidenceLevel == "HIGH"


@pytest.mark.asyncio
async def test_risk_scorer_multi_signal_boost():
    """Verify that multi-signal psychological manipulation adds a weighted boost to risk score."""
    mock_db = MagicMock()
    mock_db.scampattern.find_many = AsyncMock(return_value=[])

    # Case 1: 0 signals detected -> No boost
    score_0 = await boost_score_from_patterns(
        text="Normal text",
        base_score=40,
        db=mock_db,
        emotion_signals=[],
    )
    assert score_0 == 40

    # Case 2: 1 signal detected (< 2 threshold) -> No multi-signal boost
    sig_single = [
        SentraEmotionSignal(
            type=EmotionSignalType.URGENCY,
            detected=True,
            examples=["buruan"],
            confidence=0.80,
        )
    ]
    score_1 = await boost_score_from_patterns(
        text="Normal text",
        base_score=40,
        db=mock_db,
        emotion_signals=sig_single,
    )
    assert score_1 == 40

    # Case 3: 3 signals detected (base +12, avg conf 0.80 -> ~9.6 boost)
    sig_triple = [
        SentraEmotionSignal(type=EmotionSignalType.URGENCY, detected=True, examples=["buruan"], confidence=0.80),
        SentraEmotionSignal(type=EmotionSignalType.FAKE_SCARCITY, detected=True, examples=["slot terbatas"], confidence=0.80),
        SentraEmotionSignal(type=EmotionSignalType.UNREALISTIC_RETURN, detected=True, examples=["profit 100%"], confidence=0.80),
    ]
    score_3 = await boost_score_from_patterns(
        text="Scam text",
        base_score=40,
        db=mock_db,
        emotion_signals=sig_triple,
    )
    assert score_3 > 40
    # Expected boost: 12 * 0.8 = 9.6 -> final score ~ 49
    assert 48 <= score_3 <= 50

    # Case 4: 4+ signals detected (base +18, avg conf 0.825 -> ~14.8 boost)
    sig_quad = sig_triple + [
        SentraEmotionSignal(type=EmotionSignalType.SOCIAL_PROOF_MANIPULATION, detected=True, examples=["testimoni"], confidence=0.90),
    ]
    score_4 = await boost_score_from_patterns(
        text="Scam text",
        base_score=40,
        db=mock_db,
        emotion_signals=sig_quad,
    )
    assert score_4 >= 54
