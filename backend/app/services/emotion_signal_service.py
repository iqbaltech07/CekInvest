"""
Emotion signal normalization and deterministic safety checks.

SENTRA is asked to return all six emotional manipulation signals, but model
outputs can be partial. This module makes the persisted shape stable and adds
low-cost rule checks for obvious manipulation phrases.
"""
import re
from dataclasses import dataclass

from app.config import settings
from app.schemas.analysis import EmotionSignalType, SentraEmotionSignal


_SIGNAL_ORDER = [
    EmotionSignalType.URGENCY,
    EmotionSignalType.FAKE_SCARCITY,
    EmotionSignalType.FAKE_AUTHORITY,
    EmotionSignalType.UNREALISTIC_RETURN,
    EmotionSignalType.EMOTIONAL_PRESSURE,
    EmotionSignalType.SOCIAL_PROOF_MANIPULATION,
]


@dataclass(frozen=True)
class _Rule:
    signal_type: EmotionSignalType
    patterns: tuple[str, ...]
    description: str


_KEYWORD_RULES = [
    _Rule(
        signal_type=EmotionSignalType.URGENCY,
        patterns=(
            "hari ini",
            "sekarang juga",
            "cepat",
            "buruan",
            "jangan sampai terlambat",
            "closing malam ini",
            "waktu terbatas",
        ),
        description="Terdapat bahasa yang mendorong keputusan cepat tanpa waktu berpikir.",
    ),
    _Rule(
        signal_type=EmotionSignalType.FAKE_SCARCITY,
        patterns=(
            "slot terbatas",
            "kuota terbatas",
            "tinggal sedikit",
            "sisa slot",
            "hanya untuk",
            "batch terakhir",
        ),
        description="Terdapat klaim kelangkaan yang dapat menekan pengguna agar segera masuk.",
    ),
    _Rule(
        signal_type=EmotionSignalType.FAKE_AUTHORITY,
        patterns=(
            "resmi ojk",
            "diawasi ojk",
            "didukung pemerintah",
            "izin ojk",
            "terdaftar ojk",
            "legalitas lengkap",
        ),
        description="Terdapat klaim otoritas/regulasi yang perlu diverifikasi langsung.",
    ),
    _Rule(
        signal_type=EmotionSignalType.EMOTIONAL_PRESSURE,
        patterns=(
            "jangan kasih tahu",
            "rahasia",
            "kesempatan emas",
            "kamu akan menyesal",
            "jangan ragu",
            "percaya saja",
        ),
        description="Terdapat tekanan emosional yang dapat mengurangi kewaspadaan pengguna.",
    ),
    _Rule(
        signal_type=EmotionSignalType.SOCIAL_PROOF_MANIPULATION,
        patterns=(
            "testimoni",
            "sudah banyak yang profit",
            "member kami",
            "bukti transfer",
            "artis",
            "influencer",
            "grup vip",
        ),
        description="Terdapat social proof yang perlu diverifikasi karena mudah direkayasa.",
    ),
]

_FINANCIAL_CONTEXT_PATTERNS = (
    "investasi",
    "profit",
    "return",
    "modal",
    "deposit",
    "transfer",
    "rekening",
    "ojk",
    "trading",
    "saham",
    "crypto",
    "cuan",
    "bonus referral",
    "withdraw",
    "keuntungan",
    "per bulan",
    "per minggu",
    "per hari",
    "dana",
)

_NON_INVESTMENT_PERCENT_CONTEXT = (
    "diskon",
    "potongan",
    "cashback",
    "voucher",
    "promo belanja",
)


def normalize_emotion_signals(
    content: str,
    ai_signals: list[SentraEmotionSignal],
) -> list[SentraEmotionSignal]:
    """Return all six emotion signals, enriched by deterministic text checks."""
    by_type: dict[EmotionSignalType, SentraEmotionSignal] = {}

    for signal in ai_signals:
        existing = by_type.get(signal.type)
        if existing is None or (signal.detected and not existing.detected):
            by_type[signal.type] = signal

    has_financial_context = _has_financial_context(content)
    if has_financial_context:
        for rule in _KEYWORD_RULES:
            examples = _find_keyword_examples(content, rule.patterns)
            if examples:
                _mark_detected(by_type, rule.signal_type, rule.description, examples)

    return_examples = _find_unrealistic_return_examples(content)
    if return_examples:
        _mark_detected(
            by_type,
            EmotionSignalType.UNREALISTIC_RETURN,
            (
                "Terdapat klaim return di atas ambang wajar "
                f"({settings.UNREALISTIC_RETURN_THRESHOLD:g}% per bulan)."
            ),
            return_examples,
        )

    for signal_type in _SIGNAL_ORDER:
        by_type.setdefault(
            signal_type,
            SentraEmotionSignal(
                type=signal_type,
                detected=False,
                description=None,
                examples=[],
            ),
        )

    return [by_type[signal_type] for signal_type in _SIGNAL_ORDER]


def _mark_detected(
    signals: dict[EmotionSignalType, SentraEmotionSignal],
    signal_type: EmotionSignalType,
    description: str,
    examples: list[str],
) -> None:
    existing = signals.get(signal_type)
    merged_examples = list(dict.fromkeys((existing.examples if existing else []) + examples))[:5]
    signals[signal_type] = SentraEmotionSignal(
        type=signal_type,
        detected=True,
        description=existing.description if existing and existing.description else description,
        examples=merged_examples,
    )


def _find_keyword_examples(content: str, patterns: tuple[str, ...]) -> list[str]:
    lowered = content.lower()
    examples = []
    for pattern in patterns:
        idx = lowered.find(pattern)
        if idx == -1:
            continue
        start = max(0, idx - 35)
        end = min(len(content), idx + len(pattern) + 35)
        examples.append(content[start:end].strip())
    return examples[:5]


def _find_unrealistic_return_examples(content: str) -> list[str]:
    examples = []
    pattern = re.compile(
        r"(?P<value>\d+(?:[,.]\d+)?)\s*%[^\n\r.]{0,40}"
        r"(?P<period>per\s*(?:bulan|minggu|hari)|/bulan|/minggu|/hari|bulanan|mingguan|harian)?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(content):
        matched_str = match.group(0)
        # Skip if match looks like CSS, programming syntax, or markup code
        if any(char in matched_str for char in (";", "{", "}", "!", "/*", "*/", ":", "opacity", "width", "height", "display", "important")):
            continue
        if _looks_like_non_investment_percent(matched_str):
            continue
        value = float(match.group("value").replace(",", "."))
        period = (match.group("period") or "").lower()
        monthly_value = _to_monthly_return(value, period)
        if monthly_value > settings.UNREALISTIC_RETURN_THRESHOLD:
            examples.append(matched_str.strip())
    return examples[:5]


def _has_financial_context(content: str) -> bool:
    lowered = content.lower()
    return any(pattern in lowered for pattern in _FINANCIAL_CONTEXT_PATTERNS)


def _looks_like_non_investment_percent(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in _NON_INVESTMENT_PERCENT_CONTEXT)


def _to_monthly_return(value: float, period: str) -> float:
    if "hari" in period or "/hari" in period or "harian" in period:
        return value * 30
    if "minggu" in period or "/minggu" in period or "mingguan" in period:
        return value * 4
    return value
