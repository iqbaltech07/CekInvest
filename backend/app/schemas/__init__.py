"""Schemas package — v2.1."""
from app.schemas.common import APIResponse, ErrorResponse, PaginatedResponse
from app.schemas.analysis import (
    InputType,
    RiskLevel,
    FlagSeverity,
    EmotionSignalType,
    OjkStatus,
    ChatAnalysisRequest,
    UrlAnalysisRequest,
    SentraAnalysisResult,
    SentraRedFlag,
    SentraEmotionSignal,
    AnalysisResponse,
    RedFlagResponse,
    EmotionSignalResponse,
)
from app.schemas.report import (
    CreateReportRequest,
    ReportResponse,
    ScamPatternResponse,
    IntelligenceStatsResponse,
    SendChatMessageRequest,
    ChatMessageResponse,
    ChatMessageRole,
    ChatSessionResponse,
    ShareableReportMeta,
)

__all__ = [
    "APIResponse",
    "ErrorResponse",
    "PaginatedResponse",
    # Analysis
    "InputType",
    "RiskLevel",
    "FlagSeverity",
    "EmotionSignalType",
    "OjkStatus",
    "ChatAnalysisRequest",
    "UrlAnalysisRequest",
    "SentraAnalysisResult",
    "SentraRedFlag",
    "SentraEmotionSignal",
    "AnalysisResponse",
    "RedFlagResponse",
    "EmotionSignalResponse",
    # Reports
    "CreateReportRequest",
    "ReportResponse",
    "ScamPatternResponse",
    "IntelligenceStatsResponse",
    # Chat (PRD 5.4)
    "SendChatMessageRequest",
    "ChatMessageResponse",
    "ChatMessageRole",
    "ChatSessionResponse",
    # Share (PRD 5.5)
    "ShareableReportMeta",
]
