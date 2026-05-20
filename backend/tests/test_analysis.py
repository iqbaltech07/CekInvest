"""
Tests for the risk scorer utility (no DB required).
"""
import pytest

from app.services.risk_scorer import classify_risk_level
from app.schemas.analysis import EmotionSignalType, RiskLevel, SentraEmotionSignal
from app.services.emotion_signal_service import normalize_emotion_signals


@pytest.mark.parametrize(
    "score, expected_level",
    [
        (0, RiskLevel.SAFE),
        (20, RiskLevel.SAFE),
        (21, RiskLevel.LOW),
        (40, RiskLevel.LOW),
        (41, RiskLevel.MEDIUM),
        (60, RiskLevel.MEDIUM),
        (61, RiskLevel.HIGH),
        (80, RiskLevel.HIGH),
        (81, RiskLevel.CRITICAL),
        (100, RiskLevel.CRITICAL),
    ],
)
def test_classify_risk_level(score: int, expected_level: RiskLevel):
    assert classify_risk_level(score) == expected_level


def test_normalize_emotion_signals_always_returns_all_six_types():
    signals = normalize_emotion_signals("Penawaran investasi biasa.", [])

    assert [signal.type for signal in signals] == [
        EmotionSignalType.URGENCY,
        EmotionSignalType.FAKE_SCARCITY,
        EmotionSignalType.FAKE_AUTHORITY,
        EmotionSignalType.UNREALISTIC_RETURN,
        EmotionSignalType.EMOTIONAL_PRESSURE,
        EmotionSignalType.SOCIAL_PROOF_MANIPULATION,
    ]
    assert all(signal.detected is False for signal in signals)


def test_normalize_emotion_signals_detects_obvious_rules_and_preserves_ai_signal():
    signals = normalize_emotion_signals(
        "Slot terbatas hari ini. Profit 30% per bulan dijamin. Sudah banyak yang profit.",
        [
            SentraEmotionSignal(
                type=EmotionSignalType.EMOTIONAL_PRESSURE,
                detected=True,
                description="AI detected pressure.",
                examples=["jangan ragu"],
            )
        ],
    )
    by_type = {signal.type: signal for signal in signals}

    assert by_type[EmotionSignalType.URGENCY].detected is True
    assert by_type[EmotionSignalType.FAKE_SCARCITY].detected is True
    assert by_type[EmotionSignalType.UNREALISTIC_RETURN].detected is True
    assert by_type[EmotionSignalType.SOCIAL_PROOF_MANIPULATION].detected is True
    assert by_type[EmotionSignalType.EMOTIONAL_PRESSURE].description == "AI detected pressure."


def test_normalize_emotion_signals_ignores_generic_urgency_without_financial_context():
    signals = normalize_emotion_signals("Promo makanan hari ini, stok terbatas.", [])
    by_type = {signal.type: signal for signal in signals}

    assert by_type[EmotionSignalType.URGENCY].detected is False
    assert by_type[EmotionSignalType.FAKE_SCARCITY].detected is False
