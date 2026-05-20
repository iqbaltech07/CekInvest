/**
 * Typed API client for CekInvest backend v2.1.
 * Base URL: http://localhost:8000/api/v1
 */
import type {
  AnalysisResult,
  APIResponse,
  ChatMessage,
  ShareMeta,
  StreamStageEvent,
  IntelligenceStats,
  InputType,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      msg = err?.error?.message ?? msg;
    } catch { }
    throw new Error(msg);
  }
  const json: APIResponse<T> = await res.json();
  if (!json.success) throw new Error(json.error?.message ?? "Unknown error");
  return json.data;
}

// ── Analysis Endpoints ────────────────────────────────────────────────────────

export async function analyzeChat(text: string): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>("/analysis/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function analyzeScreenshot(file: File): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<AnalysisResult>("/analysis/screenshot", {
    method: "POST",
    body: form,
  });
}

export async function analyzeUrl(url: string): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>("/analysis/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export async function getAnalysis(id: string): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>(`/analysis/${id}`);
}

// ── SSE Streaming (PRD: progressive analysis feedback) ────────────────────────

export function streamAnalyzeChat(
  text: string,
  onStage: (event: StreamStageEvent) => void,
  onComplete: (result: AnalysisResult) => void,
  onError: (message: string) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE}/analysis/stream/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        onError(`Server error: HTTP ${res.status}`);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE lines
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            if (eventType === "complete") {
              onComplete(data as AnalysisResult);
            } else if (eventType === "error") {
              onError(data.message ?? "Analysis failed");
            } else {
              onStage(data as StreamStageEvent);
            }
            eventType = "";
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError((err as Error).message);
      }
    }
  })();

  return () => controller.abort();
}

// ── Share Endpoints (PRD 5.5) ─────────────────────────────────────────────────

export async function getSharedReport(slug: string): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>(`/share/${slug}`);
}

export async function getShareMeta(slug: string): Promise<ShareMeta> {
  return apiFetch<ShareMeta>(`/share/${slug}/meta`);
}

// ── Chat Endpoints (PRD 5.4) ──────────────────────────────────────────────────

export async function sendChatMessage(
  analysisId: string,
  message: string
): Promise<ChatMessage> {
  return apiFetch<ChatMessage>(`/chat/${analysisId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export async function getChatHistory(analysisId: string): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(`/chat/${analysisId}/history`);
}

// ── Intelligence Stats ────────────────────────────────────────────────────────

export async function getIntelligenceStats(): Promise<IntelligenceStats> {
  return apiFetch<IntelligenceStats>("/intelligence/stats");
}

// ── Clustering & Community Reports (v2.1) ───────────────────────────────────

export interface SubmitReportData {
  inputType: InputType;
  rawInput: string;
  isScam: boolean;
  notes?: string;
  scamCategory?: string;
  bankName?: string;
  bankAccount?: string;
  phoneNumber?: string;
  domain?: string;
  city?: string;
  province?: string;
}

export interface ScamCluster {
  id: string;
  group_name: string;
  category: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  total_reports: number;
  similarity_score: number;
  matched_signals: string[];
  dominant_region: string | null;
  regional_status: string;
  bank_accounts: string[];
  phone_numbers: string[];
  domains: string[];
  created_at: string;
  updated_at: string;
}

export interface ScamClustersResponse {
  total: number;
  clusters: ScamCluster[];
}

export interface RegionalRadarRegion {
  region: string;
  province: string | null;
  dominant_scam: string | null;
  growth_percentage: number;
  status: string;
  spread_level: string;
  total_reports: number;
  current_week?: number;
  previous_week?: number;
}

export interface RegionalRadarResponse {
  total_monitored_regions: number;
  most_viral_regions: RegionalRadarRegion[];
  all_regions: RegionalRadarRegion[];
}

export interface SubmitReportResponse {
  id: string;
  inputType: InputType;
  rawInput: string;
  isScam: boolean;
  notes?: string | null;
  scamCategory?: string | null;
  bankName?: string | null;
  bankAccount?: string | null;
  phoneNumber?: string | null;
  domain?: string | null;
  city?: string | null;
  province?: string | null;
  createdAt: string;
}

export async function submitReport(data: SubmitReportData): Promise<SubmitReportResponse> {
  return apiFetch<SubmitReportResponse>("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getScamClusters(
  filters?: {
    risk_level?: string;
    region?: string;
  },
  signal?: AbortSignal
): Promise<ScamClustersResponse> {
  const query = new URLSearchParams();
  if (filters?.risk_level) query.append("risk_level", filters.risk_level);
  if (filters?.region) query.append("region", filters.region);

  return apiFetch<ScamClustersResponse>(`/clustering/clusters?${query.toString()}`, { signal });
}

export async function getRegionalRadar(
  trend?: string,
  signal?: AbortSignal
): Promise<RegionalRadarResponse> {
  const query = new URLSearchParams();
  if (trend) query.append("trend", trend);

  return apiFetch<RegionalRadarResponse>(`/clustering/regional?${query.toString()}`, { signal });
}
