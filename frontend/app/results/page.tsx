"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, useInView, animate, AnimatePresence } from "motion/react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";
import {
  AlertTriangle, ShieldCheck, ShieldAlert, ShieldQuestion,
  ArrowLeft, RotateCcw, Share2, ExternalLink,
  MessageCircle, ChevronDown, ChevronUp, Send, X,
  Building2, Globe, Newspaper, HelpCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import Navbar from "@/components/Navbar";
import type { AnalysisResult, EmotionSignal, OjkStatus, RiskLevel } from "@/lib/types";
import { sendChatMessage } from "@/lib/api";

/* ─── Risk helpers ───────────────────────────────────────────────────── */
function getRiskConfig(level: RiskLevel) {
  const map: Record<RiskLevel, { label: string; color: string; icon: React.ElementType }> = {
    SAFE: { label: "Aman", color: "oklch(0.72 0.17 155)", icon: ShieldCheck },
    LOW: { label: "Rendah", color: "oklch(0.78 0.16 140)", icon: ShieldCheck },
    MEDIUM: { label: "Waspada", color: "oklch(0.80 0.16 75)", icon: ShieldQuestion },
    HIGH: { label: "Berbahaya", color: "oklch(0.68 0.20 35)", icon: ShieldAlert },
    CRITICAL: { label: "Kritis!", color: "oklch(0.60 0.24 22)", icon: ShieldAlert },
  };
  return map[level] ?? map.MEDIUM;
}

const OJK_CONFIG: Record<OjkStatus, { label: string; color: string; bg: string }> = {
  TERDAFTAR: { label: "Terdaftar OJK ✓", color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200" },
  TIDAK_TERDAFTAR: { label: "Tidak Terdaftar OJK", color: "text-orange-600", bg: "bg-orange-50 border-orange-200" },
  TERINDIKASI_ILEGAL: { label: "Terindikasi Ilegal ⚠️", color: "text-red-600", bg: "bg-red-50 border-red-200" },
  TIDAK_DITEMUKAN: { label: "Tidak Ditemukan di OJK", color: "text-zinc-500", bg: "bg-zinc-50 border-zinc-200" },
};

const SEVERITY_CONFIG = {
  HIGH: { label: "Tinggi", cls: "bg-red-500/10 border-red-500/20 text-red-600" },
  MEDIUM: { label: "Sedang", cls: "bg-orange-500/10 border-orange-500/20 text-orange-600" },
  LOW: { label: "Rendah", cls: "bg-yellow-500/10 border-yellow-500/20 text-yellow-600" },
};

const EMOTION_LABELS: Record<string, string> = {
  URGENCY: "Buru-buru",
  FAKE_SCARCITY: "Takut Habis",
  FAKE_AUTHORITY: "Mengaku Resmi",
  UNREALISTIC_RETURN: "Untung Tinggi",
  EMOTIONAL_PRESSURE: "Rayuan",
  SOCIAL_PROOF_MANIPULATION: "Bukti Palsu",
};

const EMOTION_SHORT_LABELS: Record<string, string> = {
  URGENCY: "Buru-buru",
  FAKE_SCARCITY: "Takut Habis",
  FAKE_AUTHORITY: "Mengaku Resmi",
  UNREALISTIC_RETURN: "Untung Tinggi",
  EMOTIONAL_PRESSURE: "Rayuan",
  SOCIAL_PROOF_MANIPULATION: "Bukti Palsu",
};

const CONFIDENCE_CONFIG = {
  NONE: {
    label: "Bersih",
    cls: "bg-zinc-500/10 border-zinc-500/20 text-zinc-500",
    bar: "bg-zinc-300",
  },
  LOW: {
    label: "Rendah",
    cls: "bg-yellow-500/10 border-yellow-500/20 text-yellow-600",
    bar: "bg-yellow-500",
  },
  MEDIUM: {
    label: "Sedang",
    cls: "bg-orange-500/10 border-orange-500/20 text-orange-600",
    bar: "bg-orange-500",
  },
  HIGH: {
    label: "Tinggi",
    cls: "bg-red-500/10 border-red-500/20 text-red-600",
    bar: "bg-red-500",
  },
};

/* ─── Animated score orb ─────────────────────────────────────────────── */
function RiskOrb({ score, color }: { score: number; color: string }) {
  const [displayed, setDisplayed] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  const radius = 88;
  const circ = 2 * Math.PI * radius;
  const dash = (displayed / 100) * circ;

  useEffect(() => {
    if (!inView) return;
    const ctrl = animate(0, score, {
      duration: 1.8, ease: [0.25, 0.46, 0.45, 0.94],
      onUpdate: (v) => setDisplayed(Math.round(v)),
    });
    return ctrl.stop;
  }, [inView, score]);

  return (
    <div ref={ref} className="relative flex items-center justify-center w-56 h-56">
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={inView ? { opacity: 1, scale: 1 } : {}}
        transition={{ duration: 0.6 }}
        className="absolute -inset-12 opacity-30 pointer-events-none"
        style={{ background: `radial-gradient(circle at 50% 50%, ${color} 0%, transparent 60%)` }} />
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 200 200">
        <circle cx="100" cy="100" r={radius} fill="none" stroke="oklch(0 0 0 / 8%)" strokeWidth="10" />
        <motion.circle cx="100" cy="100" r={radius} fill="none" stroke={color} strokeWidth="10"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ - dash}
          style={{ filter: `drop-shadow(0 0 8px ${color})` }} />
      </svg>
      <div className="relative flex flex-col items-center gap-1 z-10">
        <span className="text-5xl font-black tabular-nums tracking-tight" style={{ color }}>{displayed}</span>
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Risk Score</span>
      </div>
    </div>
  );
}

/* ─── Emotion radar ──────────────────────────────────────────────────── */
function EmotionRadar({ signals }: { signals: EmotionSignal[] }) {
  const data = signals.map((s) => ({
    subject: EMOTION_SHORT_LABELS[s.signalType] ?? s.signalType,
    value: getEmotionScore(s),
    fullMark: 100,
  }));
  if (data.length === 0) {
    return (
      <p className="text-xs text-muted-foreground text-center py-8">
        Data sinyal emosi belum tersedia.
      </p>
    );
  }
  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 12, right: 36, bottom: 12, left: 36 }}>
          <PolarGrid stroke="oklch(0 0 0 / 8%)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: "oklch(0.50 0.01 265)", fontSize: 10, fontWeight: 600 }}
          />
          <Radar
            name="Confidence"
            dataKey="value"
            stroke="oklch(0.55 0.22 275)"
            fill="oklch(0.55 0.22 275)"
            fillOpacity={0.22}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function EmotionSignalsPanel({ signals }: { signals: EmotionSignal[] }) {
  const detectedCount = signals.filter((signal) => signal.detected).length;
  const strongest = signals.reduce<EmotionSignal | null>(
    (best, signal) => (!best || getEmotionScore(signal) > getEmotionScore(best) ? signal : best),
    null
  );
  const strongestScore = strongest ? getEmotionScore(strongest) : 0;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      id="emotion-radar"
      className="glass rounded-3xl p-6 border border-black/5 mb-5"
    >
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">
        <div>
          <h2 className="text-sm font-semibold text-foreground/80">
            Sinyal Manipulasi Emosional
          </h2>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed max-w-xl">
            Confidence dihitung dari gabungan analisis AI, pola kalimat, dan bukti teks yang
            ditemukan. Gunakan sebagai sinyal kehati-hatian, bukan vonis final.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 min-w-48">
          <div className="rounded-2xl bg-black/3 border border-black/5 px-3 py-2">
            <p className="text-[10px] text-muted-foreground uppercase font-bold">Terdeteksi</p>
            <p className="text-xl font-bold text-foreground">{detectedCount}/6</p>
          </div>
          <div className="rounded-2xl bg-black/3 border border-black/5 px-3 py-2">
            <p className="text-[10px] text-muted-foreground uppercase font-bold">Tertinggi</p>
            <p className="text-xl font-bold text-foreground">{strongestScore}%</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[0.95fr_1.25fr] gap-5 items-start">
        <div className="rounded-2xl bg-white/60 border border-black/5 p-3">
          <EmotionRadar signals={signals} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {signals.map((signal) => (
            <EmotionSignalCard key={signal.signalType} signal={signal} />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function EmotionSignalCard({ signal }: { signal: EmotionSignal }) {
  const confidenceLevel = signal.confidenceLevel ?? (signal.detected ? "LOW" : "NONE");
  const cfg = CONFIDENCE_CONFIG[confidenceLevel];
  const score = getEmotionScore(signal);
  const examples = signal.examples?.filter(Boolean).slice(0, 1) ?? [];

  return (
    <div className="rounded-2xl border border-black/5 bg-black/3 p-3.5 min-h-34">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold text-foreground/85 leading-snug">
            {EMOTION_LABELS[signal.signalType] ?? signal.signalType}
          </p>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            {signal.detected ? `${score}% confidence` : "Tidak ada bukti kuat"}
          </p>
        </div>
        <Badge variant="outline" className={`text-[9px] border shrink-0 ${cfg.cls}`}>
          {cfg.label}
        </Badge>
      </div>

      <div className="h-1.5 rounded-full bg-black/5 overflow-hidden mb-2.5">
        <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${score}%` }} />
      </div>

      {signal.detected && signal.description ? (
        <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
          {signal.description}
        </p>
      ) : (
        <p className="text-[11px] text-muted-foreground/70 leading-relaxed">
          Sistem tidak menemukan bukti yang cukup untuk sinyal ini.
        </p>
      )}

      {examples.map((example, index) => (
        <p
          key={`${signal.signalType}-${index}`}
          className="mt-2 text-[10px] italic text-muted-foreground/70 font-mono border-l-2 border-current/20 pl-2 line-clamp-2"
        >
          &quot;{example}&quot;
        </p>
      ))}
    </div>
  );
}

function getEmotionScore(signal: EmotionSignal): number {
  if (!signal.detected) return 0;
  return Math.max(35, Math.round((signal.confidenceScore ?? 0.65) * 100));
}

/* ─── AI Guardian Chat panel ─────────────────────────────────────────── */
function GuardianChat({ analysisId }: { analysisId: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: "user" | "ai"; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    try {
      const reply = await sendChatMessage(analysisId, text);
      setMessages((prev) => [...prev, { role: "ai", content: reply.content }]);
    } catch {
      setMessages((prev) => [...prev, { role: "ai", content: "Maaf, AI Guardian sedang tidak tersedia. Silakan coba lagi." }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
      className="glass rounded-3xl border border-black/5 overflow-hidden" id="ai-guardian">
      <button onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-3 p-5 hover:bg-black/3 transition-colors">
        <div className="w-9 h-9 rounded-2xl bg-primary/10 flex items-center justify-center flex-shrink-0">
          <MessageCircle className="w-4.5 h-4.5 text-primary" />
        </div>
        <div className="flex-1 text-left">
          <p className="text-sm font-semibold text-foreground">AI Scam Guardian</p>
          <p className="text-xs text-muted-foreground">Tanya lebih dalam tentang hasil analisis ini</p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }}
            className="overflow-hidden border-t border-black/5">
            <div className="p-4 flex flex-col gap-3 max-h-80 overflow-y-auto">
              {messages.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">
                  Tanya apa saja tentang hasil analisis ini. Contoh: <em>&quot;Apa artinya domain baru?&quot;</em> atau <em>&quot;Bagaimana cara menolak tawaran ini dengan sopan?&quot;</em>
                </p>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${m.role === "user"
                    ? "bg-primary text-primary-foreground" : "bg-black/5 text-foreground"}`}>
                    {m.content}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-black/5 rounded-2xl px-4 py-3 flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <span key={i} className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            <div className="p-3 border-t border-black/5 flex gap-2">
              <input value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                placeholder="Tanya AI Guardian…" id="guardian-input"
                className="flex-1 bg-black/5 rounded-xl px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 outline-none focus:ring-1 focus:ring-primary/30" />
              <button onClick={send} disabled={sending || !input.trim()} id="guardian-send"
                className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center flex-shrink-0 disabled:opacity-40 transition-opacity">
                <Send className="w-3.5 h-3.5 text-primary-foreground" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ─── Main page ──────────────────────────────────────────────────────── */
export default function ResultsPage() {
  const router = useRouter();
  const [result] = useState<AnalysisResult | null>(() => {
    if (typeof window === "undefined") return null;
    const raw = sessionStorage.getItem("ia_result");
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AnalysisResult;
    } catch {
      return null;
    }
  });
  const [showExplanation, setShowExplanation] = useState(false);
  const [copying, setCopying] = useState(false);

  useEffect(() => {
    if (!result) router.replace("/analyze");
  }, [result, router]);

  if (!result) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  );

  const { label, color, icon: VerdictIcon } = getRiskConfig(result.riskLevel);
  const ojkCfg = result.ojkStatus ? OJK_CONFIG[result.ojkStatus] : null;

  const handleShare = async () => {
    if (!result.shareSlug) return;
    setCopying(true);
    try {
      // Build the frontend share page URL, NOT the API endpoint
      const shareUrl = `${window.location.origin}/share/${result.shareSlug}`;
      await navigator.clipboard.writeText(shareUrl);
      setTimeout(() => setCopying(false), 2000);
    } catch {
      setTimeout(() => setCopying(false), 2000);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex flex-col flex-1 min-h-screen pt-24 pb-16 px-6 relative overflow-hidden">
        <div className="orb w-[600px] h-[600px] opacity-10 -right-40 -top-20"
          style={{ background: `${color} / 30%` }} />

        <div className="max-w-220 mx-auto w-full relative z-10">
          {/* Back */}
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="mb-8">
            <Link href="/analyze" id="back-btn"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft className="w-4 h-4" /> Analisis Ulang
            </Link>
          </motion.div>

          {/* ── Hero Result Card ── */}
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }} id="result-hero"
            className="glass rounded-3xl p-6 md:p-10 border border-black/5 mb-5 shadow-xl">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-8 w-full">
              <div className="shrink-0"><RiskOrb score={result.riskScore} color={color} /></div>
              <div className="flex flex-col gap-3 text-center md:text-left flex-1 min-w-0 w-full">
                <div className="flex items-center justify-center md:justify-start gap-2">
                  <VerdictIcon className="w-5 h-5" style={{ color }} />
                  <span className="font-bold text-2xl tracking-tight" style={{ color }}>{label}</span>
                  <Badge variant="outline" className="text-[10px] border-current ml-1" style={{ color }}>
                    {result.riskLevel}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{result.summary}</p>

                {/* OJK Status badge */}
                {ojkCfg && (
                  <div className={`inline-flex items-center gap-2 self-center md:self-start px-3 py-1.5 rounded-xl border text-xs font-semibold ${ojkCfg.bg} ${ojkCfg.color}`}>
                    <Building2 className="w-3.5 h-3.5" />
                    {ojkCfg.label}
                    {result.ojkEntityName && <span className="opacity-70">· {result.ojkEntityName}</span>}
                  </div>
                )}

                {/* Intelligence badges */}
                <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                  {result.domainAgeDays !== null && result.domainAgeDays !== undefined && (
                    <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2.5 py-1 rounded-full border ${result.domainAgeDays < 90 ? "bg-red-50 border-red-200 text-red-600" : "bg-zinc-50 border-zinc-200 text-zinc-500"}`}>
                      <Globe className="w-3 h-3" />
                      Domain {result.domainAgeDays} hari
                      {result.domainCountry && ` · ${result.domainCountry}`}
                    </span>
                  )}
                  {result.mediaHitCount !== null && result.mediaHitCount !== undefined && result.mediaHitCount > 0 && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2.5 py-1 rounded-full border bg-orange-50 border-orange-200 text-orange-600">
                      <Newspaper className="w-3 h-3" />
                      {result.mediaHitCount} berita negatif
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Explanation (collapsible) */}
            {result.explanation && (
              <div className="mt-6 border-t border-black/5 pt-5">
                <button onClick={() => setShowExplanation((p) => !p)}
                  className="flex items-center gap-2 text-xs font-semibold text-foreground/70 hover:text-foreground transition-colors w-full">
                  {showExplanation ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  Lihat penjelasan langkah demi langkah dari AI
                </button>
                <AnimatePresence>
                  {showExplanation && (
                    <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-3 text-xs text-muted-foreground leading-relaxed overflow-hidden whitespace-pre-wrap">
                      {result.explanation}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>
            )}
          </motion.div>

          {/* ── Trap Questions (PRD 5.1) ── */}
          {result.trapQuestions?.length > 0 && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }} id="trap-questions"
              className="glass rounded-3xl p-6 border border-black/5 mb-5">
              <div className="flex items-center gap-2 mb-4">
                <HelpCircle className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-semibold text-foreground/80">Pertanyaan untuk Mengetes Penawar</h2>
              </div>
              <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
                Tanyakan pertanyaan ini langsung ke penawar investasi. Jika mereka menghindari atau menjawab tidak jelas, itu tanda bahaya.
              </p>
              <div className="flex flex-col gap-2.5">
                {result.trapQuestions.map((q, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + i * 0.06 }}
                    className="flex gap-3 p-3.5 rounded-2xl bg-primary/5 border border-primary/10">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <p className="text-xs text-foreground/80 leading-relaxed">{q}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ── Grid: Radar + Red Flags ── */}
          <EmotionSignalsPanel signals={result.emotionSignals} />

          <div className="grid grid-cols-1 mb-5">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }} id="red-flags-section"
              className="glass rounded-3xl p-6 border border-black/5">
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-sm font-semibold text-foreground/80">Red Flags</h2>
                <Badge variant="outline" className="text-[10px] ml-auto border-black/10">
                  {result.redFlags.length} ditemukan
                </Badge>
              </div>
              <div className="flex flex-col gap-2.5 max-h-64 overflow-y-auto pr-1">
                {result.redFlags.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-4">Tidak ada red flag signifikan.</p>
                )}
                {result.redFlags.map((flag, i) => {
                  const sev = SEVERITY_CONFIG[flag.severity];
                  return (
                    <motion.div key={flag.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.06 }} id={`red-flag-${i}`}
                      className={`rounded-xl p-3.5 border flex gap-3 ${sev.cls}`}>
                      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" strokeWidth={2} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap mb-1">
                          <span className="font-semibold text-[11px]">{flag.category}</span>
                          <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-current">{sev.label}</Badge>
                          {flag.confidence > 0 && (
                            <span className="text-[9px] opacity-60">{Math.round(flag.confidence * 100)}%</span>
                          )}
                        </div>
                        <p className="text-[11px] leading-relaxed opacity-80">{flag.description}</p>
                        {flag.excerpt && (
                          <p className="mt-1.5 text-[10px] italic opacity-60 font-mono border-l-2 border-current/30 pl-2">
                            &quot;{flag.excerpt}&quot;
                          </p>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          </div>

          {/* ── AI Guardian Chat (PRD 5.4) ── */}
          <div className="mb-5">
            <GuardianChat analysisId={result.id} />
          </div>

          {/* ── Action footer ── */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 }} className="flex flex-col sm:flex-row gap-3">
            <Link href="/analyze" id="re-analyze-btn"
              className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-semibold glass border border-black/5 text-muted-foreground hover:text-foreground transition-colors">
              <RotateCcw className="w-4 h-4" /> Analisis Lagi
            </Link>
            <button id="share-btn" onClick={handleShare}
              className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-semibold bg-primary text-primary-foreground shadow-md hover:shadow-[0_8px_20px_oklch(0.55_0.22_275/30%)] hover:scale-[1.02] transition-all duration-300">
              {copying ? <><X className="w-4 h-4" /> Link Disalin!</> : <><Share2 className="w-4 h-4" /> Bagikan Hasil</>}
            </button>
            <a href="https://sikapiuangmu.ojk.go.id/FrontEnd/CMS/Category/66"
              target="_blank" rel="noopener noreferrer" id="ojk-link"
              className="flex items-center justify-center gap-2 px-5 py-3.5 rounded-2xl text-sm font-semibold glass border border-black/5 text-muted-foreground hover:text-foreground transition-colors">
              <ExternalLink className="w-4 h-4" /> Lapor OJK
            </a>
          </motion.div>

          <p className="mt-4 text-center text-xs text-muted-foreground/40 leading-relaxed">
            Hasil analisis bersifat indikatif berdasarkan pola yang dikenali AI. Bukan keputusan hukum atau finansial resmi.
          </p>
        </div>
      </main>
    </>
  );
}
