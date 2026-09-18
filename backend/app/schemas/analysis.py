"""
Pydantic v2 schemas for the analysis endpoints and SENTRA AI output v2.1.
Adds: explanation, trapQuestions, ojkStatus, shareSlug, shareUrl.
"""
import enum
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Enums (mirror Prisma schema) ──────────────────────────────────────────────

class InputType(str, enum.Enum):
    CHAT = "CHAT"
    SCREENSHOT = "SCREENSHOT"
    URL = "URL"


class RiskLevel(str, enum.Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FlagSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EmotionSignalType(str, enum.Enum):
    URGENCY = "URGENCY"
    FAKE_SCARCITY = "FAKE_SCARCITY"
    FAKE_AUTHORITY = "FAKE_AUTHORITY"
    UNREALISTIC_RETURN = "UNREALISTIC_RETURN"
    EMOTIONAL_PRESSURE = "EMOTIONAL_PRESSURE"
    SOCIAL_PROOF_MANIPULATION = "SOCIAL_PROOF_MANIPULATION"


class OjkStatus(str, enum.Enum):
    TERDAFTAR = "TERDAFTAR"
    TIDAK_TERDAFTAR = "TIDAK_TERDAFTAR"
    TERINDIKASI_ILEGAL = "TERINDIKASI_ILEGAL"
    TIDAK_DITEMUKAN = "TIDAK_DITEMUKAN"


# ── Request Schemas ───────────────────────────────────────────────────────────

class ChatAnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=50_000,
        description="Paste the chat conversation or suspicious message text.",
        examples=["Bergabunglah sekarang! Keuntungan 50% per bulan dijamin! Slot terbatas!"],
    )


class UrlAnalysisRequest(BaseModel):
    url: str = Field(
        ...,
        description="URL of the investment offer or suspicious link to analyze.",
        examples=["https://investasi-super.xyz/daftar"],
    )


# ── SENTRA AI Internal Schemas (structured Gemini output) ─────────────────────

class SentraRedFlag(BaseModel):
    category: str
    description: str
    severity: FlagSeverity
    confidence: float = Field(..., ge=0.0, le=1.0)
    excerpt: str | None = None


class SentraEmotionSignal(BaseModel):
    type: EmotionSignalType
    detected: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str | None = None
    examples: list[str] = Field(default_factory=list)


class SentraAnalysisResult(BaseModel):
    """Structured output that SENTRA returns from Gemini 2.5 Flash."""

    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    safe_to_invest: bool
    summary: str = Field(..., description="Calm, human-friendly summary in Bahasa Indonesia")
    explanation: str = Field(default="", description="Step-by-step reasoning in Bahasa Indonesia")
    red_flags: list[SentraRedFlag] = Field(default_factory=list)
    emotion_signals: list[SentraEmotionSignal] = Field(default_factory=list)
    trap_questions: list[str] = Field(
        default_factory=list,
        description="3–5 polite trap questions to ask the investment offerer (PRD 5.1)",
    )


# ── Response Schemas ──────────────────────────────────────────────────────────

class RedFlagResponse(BaseModel):
    id: str
    category: str
    description: str
    severity: FlagSeverity
    confidence: float
    excerpt: str | None

    model_config = {"from_attributes": True}


class EmotionSignalResponse(BaseModel):
    id: str
    signalType: EmotionSignalType
    detected: bool
    description: str | None
    examples: list[str]
    confidenceScore: float = Field(default=0.0, ge=0.0, le=1.0)
    confidenceLevel: Literal["NONE", "LOW", "MEDIUM", "HIGH"] = "NONE"
    evidenceCount: int = 0

    @model_validator(mode="after")
    def derive_confidence(self) -> "EmotionSignalResponse":
        self.evidenceCount = len(self.examples or [])
        if not self.detected:
            self.confidenceScore = 0.0
            self.confidenceLevel = "NONE"
            return self

        # Use incoming confidenceScore if already present, otherwise calculate baseline
        base_score = self.confidenceScore if self.confidenceScore > 0 else 0.45
        score = base_score
        if self.evidenceCount:
            score += min(0.30, self.evidenceCount * 0.08)
        if self.description and not (self.confidenceScore > 0):
            score += 0.10
        if self.signalType == EmotionSignalType.UNREALISTIC_RETURN and self.examples:
            score = max(score, _unrealistic_return_confidence(self.examples))

        self.confidenceScore = round(min(score, 0.98), 2)
        if self.confidenceScore >= 0.75:
            self.confidenceLevel = "HIGH"
        elif self.confidenceScore >= 0.50:
            self.confidenceLevel = "MEDIUM"
        else:
            self.confidenceLevel = "LOW"
        return self

    model_config = {"from_attributes": True}


def _unrealistic_return_confidence(examples: list[str]) -> float:
    highest_monthly_return = 0.0
    pattern = re.compile(r"(\d+(?:[,.]\d+)?)\s*%", re.IGNORECASE)
    for example in examples:
        match = pattern.search(example)
        if not match:
            continue
        value = float(match.group(1).replace(",", "."))
        lowered = example.lower()
        if "hari" in lowered or "/hari" in lowered or "harian" in lowered:
            value *= 30
        elif "minggu" in lowered or "/minggu" in lowered or "mingguan" in lowered:
            value *= 4
        highest_monthly_return = max(highest_monthly_return, value)

    if highest_monthly_return >= 30:
        return 0.95
    if highest_monthly_return >= 10:
        return 0.85
    return 0.75


class AnalysisResponse(BaseModel):
    id: str
    inputType: InputType
    riskScore: int
    riskLevel: RiskLevel
    safeToInvest: bool
    summary: str | None
    explanation: str | None              # PRD: step-by-step AI reasoning
    trapQuestions: list[str]             # PRD 5.1: 3–5 questions to ask the offerer
    ojkStatus: OjkStatus | None         # PRD Check #01: OJK registry result
    ojkEntityName: str | None           # Matched entity name in OJK database
    shareSlug: str | None               # PRD 5.5: public shareable URL slug
    domainAgeDays: int | None           # PRD Check #15: domain age
    domainCountry: str | None           # PRD Check #16: hosting country
    mediaHitCount: int | None           # PRD Check #20: negative news count
    redFlags: list[RedFlagResponse]
    emotionSignals: list[EmotionSignalResponse]
    createdAt: datetime

    model_config = {"from_attributes": True}
