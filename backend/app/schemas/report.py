"""
Pydantic v2 schemas for community reports, intelligence stats, and AI Guardian chat.
"""
import enum
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.analysis import InputType


# ── Report Schemas ────────────────────────────────────────────────────────────

class CreateReportRequest(BaseModel):
    inputType: InputType
    rawInput: str = Field(..., min_length=5, max_length=10_000)
    isScam: bool
    notes: str | None = Field(None, max_length=2000)

    # Structured data — used by the rule-based clustering engine
    scamCategory: str | None = Field(None, description="Kategori penipuan, e.g. 'Robot Trading Scam'")
    bankName: str | None = Field(None, description="Nama bank penipu, e.g. 'BCA'")
    bankAccount: str | None = Field(None, description="Nomor rekening penipu")
    phoneNumber: str | None = Field(None, description="Nomor HP penipu")
    domain: str | None = Field(None, description="Website/domain penipu, e.g. 'cuanrobot.vip'")
    city: str | None = Field(None, description="Kota asal laporan, e.g. 'Bandung'")
    province: str | None = Field(None, description="Provinsi asal laporan, e.g. 'Jawa Barat'")


class ReportResponse(BaseModel):
    id: str
    inputType: InputType
    isScam: bool
    notes: str | None
    scamCategory: str | None = None
    bankName: str | None = None
    bankAccount: str | None = None
    phoneNumber: str | None = None
    domain: str | None = None
    city: str | None = None
    province: str | None = None
    createdAt: datetime

    model_config = {"from_attributes": True}


# ── Intelligence Schemas ──────────────────────────────────────────────────────

class ScamPatternResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    riskWeight: float
    reportCount: int

    model_config = {"from_attributes": True}


class IntelligenceStatsResponse(BaseModel):
    totalAnalyses: int
    totalReports: int
    totalScamPatterns: int
    highRiskAnalysesToday: int
    mostCommonScamCategory: str | None
    # v2.1 additions
    totalOjkCachedEntities: int = 0
    totalCommunityPhoneReports: int = 0
    totalCommunityBankReports: int = 0


# ── AI Scam Guardian Chat Schemas (PRD 5.4) ───────────────────────────────────

class ChatMessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class SendChatMessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's question or follow-up about the analysis.",
        examples=["Apa artinya return 50% per bulan yang mereka janjikan?"],
    )


class ChatMessageResponse(BaseModel):
    id: str
    role: ChatMessageRole
    content: str
    createdAt: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: str
    analysisId: str
    messages: list[ChatMessageResponse]
    createdAt: datetime

    model_config = {"from_attributes": True}


# ── Shareable Report Schemas (PRD 5.5) ────────────────────────────────────────

class ShareableReportMeta(BaseModel):
    """Metadata for a shareable report link."""
    shareUrl: str
    shareSlug: str
    whatsappText: str                   # Ready-to-paste WhatsApp message
    analysisId: str
