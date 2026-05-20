/**
 * TypeScript types aligned with backend Pydantic schemas v2.1.
 * Source of truth: backend/app/schemas/analysis.py + report.py
 */

// ── Enums ─────────────────────────────────────────────────────────────────────

export type InputType = "CHAT" | "SCREENSHOT" | "URL";

export type RiskLevel = "SAFE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type FlagSeverity = "LOW" | "MEDIUM" | "HIGH";

export type EmotionSignalType =
  | "URGENCY"
  | "FAKE_SCARCITY"
  | "FAKE_AUTHORITY"
  | "UNREALISTIC_RETURN"
  | "EMOTIONAL_PRESSURE"
  | "SOCIAL_PROOF_MANIPULATION";

export type OjkStatus =
  | "TERDAFTAR"
  | "TIDAK_TERDAFTAR"
  | "TERINDIKASI_ILEGAL"
  | "TIDAK_DITEMUKAN";

export type ChatMessageRole = "USER" | "ASSISTANT";

export type ConfidenceLevel = "NONE" | "LOW" | "MEDIUM" | "HIGH";

// ── Core Analysis Types ───────────────────────────────────────────────────────

export interface RedFlag {
  id: string;
  category: string;
  description: string;
  severity: FlagSeverity;
  confidence: number;
  excerpt: string | null;
}

export interface EmotionSignal {
  id: string;
  signalType: EmotionSignalType;
  detected: boolean;
  description: string | null;
  examples: string[];
  confidenceScore?: number;
  confidenceLevel?: ConfidenceLevel;
  evidenceCount?: number;
}

export interface AnalysisResult {
  id: string;
  inputType: InputType;
  riskScore: number;
  riskLevel: RiskLevel;
  safeToInvest: boolean;
  summary: string | null;
  explanation: string | null;
  trapQuestions: string[];
  ojkStatus: OjkStatus | null;
  ojkEntityName: string | null;
  shareSlug: string | null;
  domainAgeDays: number | null;
  domainCountry: string | null;
  mediaHitCount: number | null;
  redFlags: RedFlag[];
  emotionSignals: EmotionSignal[];
  createdAt: string;
}

// ── API Wrapper ───────────────────────────────────────────────────────────────

export interface APIResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
  };
}

// ── Chat Types (PRD 5.4) ─────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  createdAt: string;
}

// ── Share Meta (PRD 5.5) ─────────────────────────────────────────────────────

export interface ShareMeta {
  shareUrl: string;
  shareSlug: string;
  whatsappText: string;
  analysisId: string;
}

// ── SSE Streaming Stage Events ────────────────────────────────────────────────

export type StreamStage =
  | "received"
  | "intelligence"
  | "intelligence_complete"
  | "cache_hit"
  | "analyzing"
  | "saving"
  | "complete"
  | "error";

export interface StreamStageEvent {
  stage: StreamStage;
  message?: string;
  ojk_status?: OjkStatus;
  has_young_domain?: boolean;
  negative_news_count?: number;
}

// ── Intelligence Stats ────────────────────────────────────────────────────────

export interface IntelligenceStats {
  totalAnalyses: number;
  totalReports: number;
  totalScamPatterns: number;
  highRiskAnalysesToday: number;
  mostCommonScamCategory: string | null;
  totalOjkCachedEntities: number;
  totalCommunityPhoneReports: number;
  totalCommunityBankReports: number;
}
