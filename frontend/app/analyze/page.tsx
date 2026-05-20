"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import {
  MessageSquare, ImageIcon, Globe, Upload, X,
  ArrowRight, Shield, Sparkles, CheckCircle2,
  Search, Brain, Database, Wifi,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Navbar from "@/components/Navbar";
import {
  streamAnalyzeChat, analyzeScreenshot, analyzeUrl,
} from "@/lib/api";
import type { AnalysisResult, StreamStage } from "@/lib/types";

type TabType = "chat" | "screenshot" | "url";

/* ─── Stage config ──────────────────────────────────────────────────── */
const STAGE_LABELS: Record<StreamStage, { label: string; icon: React.ElementType }> = {
  received:             { label: "Input diterima…",                    icon: CheckCircle2 },
  intelligence:         { label: "Memeriksa OJK, domain & berita…",    icon: Search },
  intelligence_complete:{ label: "Data intelijen terkumpul",            icon: Database },
  cache_hit:            { label: "Hasil ditemukan di cache — instan!",  icon: Wifi },
  analyzing:            { label: "SENTRA AI menganalisis pola…",        icon: Brain },
  saving:               { label: "Menyimpan hasil analisis…",           icon: Database },
  complete:             { label: "Analisis selesai!",                   icon: CheckCircle2 },
  error:                { label: "Terjadi kesalahan",                   icon: Shield },
};

/* ─── Tab config ────────────────────────────────────────────────────── */
const tabConfig = [
  {
    id: "chat" as TabType, icon: MessageSquare, label: "Paste Chat",
    placeholder: `Paste percakapan WhatsApp, Telegram, atau teks penawaran investasi di sini...\n\nContoh:\n"Halo kak, investasi kami sudah terbukti memberikan 30% profit per bulan! Jangan sampai ketinggalan, slot terbatas!"`,
  },
  { id: "screenshot" as TabType, icon: ImageIcon, label: "Upload Screenshot", placeholder: "" },
  { id: "url" as TabType, icon: Globe, label: "Cek URL", placeholder: "https://investasi-cepatkaya.com" },
];

/* ─── Upload zone ───────────────────────────────────────────────────── */
function UploadZone({ onFile, file, onRemove }: {
  onFile: (f: File) => void; file: File | null; onRemove: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/")) onFile(f);
  }, [onFile]);
  const preview = file ? URL.createObjectURL(file) : null;

  return (
    <div className="relative w-full">
      {file && preview ? (
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
          className="relative rounded-2xl overflow-hidden border border-black/5 group">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Preview" className="w-full max-h-72 object-contain bg-black/5" />
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <button onClick={onRemove} className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent">
            <p className="text-xs text-white/80 truncate">{file.name}</p>
          </div>
        </motion.div>
      ) : (
        <motion.div animate={dragging ? { scale: 1.02 } : { scale: 1 }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)} onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`w-full min-h-48 rounded-2xl border-2 border-dashed cursor-pointer flex flex-col items-center justify-center gap-3 transition-all duration-200 ${dragging ? "border-primary bg-primary/10" : "border-black/5 hover:border-black/15 hover:bg-black/5"}`}
          id="upload-drop-zone">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${dragging ? "bg-primary/20" : "bg-black/5"}`}>
            <Upload className={`w-7 h-7 ${dragging ? "text-primary" : "text-muted-foreground"}`} strokeWidth={1.8} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground/80">{dragging ? "Lepaskan di sini" : "Drag & drop screenshot"}</p>
            <p className="text-xs text-muted-foreground mt-1">atau klik untuk pilih file · JPG, PNG, WEBP · Max 10MB</p>
          </div>
        </motion.div>
      )}
      <input ref={inputRef} type="file" accept="image/*" className="hidden"
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
    </div>
  );
}

/* ─── Streaming progress panel ──────────────────────────────────────── */
function StreamingProgress({ stages, currentStage }: {
  stages: string[]; currentStage: StreamStage | null;
}) {
  return (
    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3 }}
      className="mt-4 rounded-2xl border border-black/5 bg-black/3 p-4 overflow-hidden">
      <div className="flex flex-col gap-2">
        {stages.map((msg, i) => {
          const stage = Object.entries(STAGE_LABELS).find(([, v]) => v.label === msg);
          const StageIcon = stage ? stage[1].icon : CheckCircle2;
          const isLast = i === stages.length - 1;
          return (
            <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`flex items-center gap-2.5 text-xs ${isLast ? "text-foreground font-medium" : "text-muted-foreground"}`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${isLast ? "bg-primary/20 text-primary" : "bg-black/5 text-muted-foreground"}`}>
                {isLast && currentStage !== "complete" ? (
                  <div className="w-2.5 h-2.5 rounded-full border border-current border-t-transparent animate-spin" />
                ) : (
                  <StageIcon className="w-2.5 h-2.5" />
                )}
              </div>
              {msg}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

/* ─── Main page ─────────────────────────────────────────────────────── */
export default function AnalyzePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>("chat");
  const [chatText, setChatText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [streamStages, setStreamStages] = useState<string[]>([]);
  const [currentStage, setCurrentStage] = useState<StreamStage | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const canSubmit = () => {
    if (activeTab === "chat") return chatText.trim().length > 10;
    if (activeTab === "screenshot") return file !== null;
    if (activeTab === "url") return url.trim().length > 5;
    return false;
  };

  const pushStage = (msg: string) =>
    setStreamStages((prev) => [...prev, msg]);

  const saveAndRedirect = (result: AnalysisResult) => {
    sessionStorage.setItem("ia_result", JSON.stringify(result));
    router.push("/results");
  };

  const handleAnalyze = async () => {
    if (!canSubmit() || loading) return;
    setError("");
    setLoading(true);
    setStreamStages([]);
    setCurrentStage(null);

    try {
      if (activeTab === "chat") {
        // Use SSE streaming for chat (PRD: real-time progressive feedback)
        const abort = streamAnalyzeChat(
          chatText,
          (event) => {
            setCurrentStage(event.stage);
            const label = STAGE_LABELS[event.stage]?.label ?? event.message ?? event.stage;
            setStreamStages((prev) =>
              prev[prev.length - 1] === label ? prev : [...prev, label]
            );
          },
          (result) => {
            setLoading(false);
            abortRef.current = null;
            saveAndRedirect(result);
          },
          () => {
            // Fallback to regular chat if SSE fails
            setStreamStages([]);
            analyzeChat_fallback(chatText);
          }
        );
        abortRef.current = abort;
        return;
      }

      if (activeTab === "screenshot" && file) {
        pushStage(STAGE_LABELS.received.label);
        pushStage("Mengekstrak teks dari screenshot (OCR)…");
        setCurrentStage("analyzing");
        const result = await analyzeScreenshot(file);
        saveAndRedirect(result);
        return;
      }

      if (activeTab === "url") {
        pushStage(STAGE_LABELS.received.label);
        pushStage("Mengambil konten halaman web…");
        pushStage(STAGE_LABELS.intelligence.label);
        setCurrentStage("analyzing");
        const result = await analyzeUrl(url);
        saveAndRedirect(result);
        return;
      }
    } catch (err) {
      setError((err as Error).message || "Terjadi kesalahan. Silakan coba lagi.");
    } finally {
      if (activeTab !== "chat") setLoading(false);
    }
  };

  const analyzeChat_fallback = async (text: string) => {
    try {
      const { analyzeChat } = await import("@/lib/api");
      const result = await analyzeChat(text);
      saveAndRedirect(result);
    } catch (err) {
      setError((err as Error).message || "Terjadi kesalahan. Silakan coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.();
    abortRef.current = null;
    setLoading(false);
    setStreamStages([]);
    setCurrentStage(null);
  };

  return (
    <>
      <Navbar />
      <main className="flex flex-col flex-1 min-h-screen pt-24 pb-16 px-6 relative overflow-hidden">
        {/* Ambient orbs */}
        <div className="orb w-[500px] h-[500px] opacity-15 -left-32 top-20"
          style={{ background: "oklch(0.55 0.22 275 / 20%)" }} />
        <div className="orb w-[350px] h-[350px] opacity-10 right-0 bottom-20"
          style={{ background: "oklch(0.65 0.19 310 / 20%)" }} />

        <div className="max-w-2xl mx-auto w-full relative z-10 flex flex-col items-center">
          {/* Header */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }} className="text-center mb-10">
            <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-primary border border-primary/20 mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              SENTRA AI · 23-Layer Intelligence · Google Grounding
            </div>
            <h1 className="text-[clamp(2rem,5vw,3rem)] font-bold tracking-tight leading-tight mb-3">
              Analisis Investasimu
            </h1>
            <p className="text-muted-foreground text-sm leading-relaxed">
              Cek OJK real-time, analisis domain, & deteksi manipulasi psikologis.<br />
              Hasil dalam hitungan detik. Gratis. Tidak perlu akun.
            </p>
          </motion.div>

          {/* Analyzer card */}
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="w-full glass rounded-3xl p-6 md:p-8 border border-black/5 shadow-xl">
            <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v as TabType); setError(""); setStreamStages([]); }}>
              <TabsList className="w-full rounded-2xl p-1 mb-6 h-auto" style={{ background: "oklch(0 0 0 / 3%)" }}>
                {tabConfig.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <TabsTrigger key={tab.id} value={tab.id} id={`tab-${tab.id}`}
                      className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-xs font-medium transition-all duration-200 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-[0_0_20px_oklch(0.62_0.22_275/30%)]">
                      <Icon className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">{tab.label}</span>
                    </TabsTrigger>
                  );
                })}
              </TabsList>

              {/* Chat */}
              <TabsContent value="chat" className="mt-0">
                <AnimatePresence mode="wait">
                  <motion.div key="chat" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }} transition={{ duration: 0.2 }}>
                    <textarea id="chat-input" value={chatText}
                      onChange={(e) => setChatText(e.target.value)}
                      placeholder={tabConfig[0].placeholder}
                      className="input-clean w-full min-h-52 p-4 text-sm leading-relaxed resize-none text-foreground placeholder:text-muted-foreground/50 font-mono" />
                    <p className="mt-2 text-xs text-muted-foreground/60 text-right">{chatText.length.toLocaleString()} / 50.000 karakter</p>
                  </motion.div>
                </AnimatePresence>
              </TabsContent>

              {/* Screenshot */}
              <TabsContent value="screenshot" className="mt-0">
                <AnimatePresence mode="wait">
                  <motion.div key="screenshot" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }} transition={{ duration: 0.2 }}>
                    <UploadZone onFile={setFile} file={file} onRemove={() => setFile(null)} />
                  </motion.div>
                </AnimatePresence>
              </TabsContent>

              {/* URL */}
              <TabsContent value="url" className="mt-0">
                <AnimatePresence mode="wait">
                  <motion.div key="url" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }} transition={{ duration: 0.2 }}>
                    <div className="relative">
                      <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/60" />
                      <input id="url-input" type="url" value={url}
                        onChange={(e) => setUrl(e.target.value)} placeholder={tabConfig[2].placeholder}
                        className="input-clean w-full h-14 pl-11 pr-4 text-sm text-foreground placeholder:text-muted-foreground/50" />
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground/60 leading-relaxed">
                      Sistem akan menganalisis konten halaman, umur domain (WHOIS), hosting negara, dan mencari berita negatif dari media Indonesia.
                    </p>
                  </motion.div>
                </AnimatePresence>
              </TabsContent>
            </Tabs>

            {/* Error */}
            {error && (
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="text-xs text-red-500 mt-3 p-3 rounded-xl bg-red-500/5 border border-red-500/10">
                ⚠️ {error}
              </motion.p>
            )}

            {/* Streaming progress */}
            <AnimatePresence>
              {loading && streamStages.length > 0 && (
                <StreamingProgress stages={streamStages} currentStage={currentStage} />
              )}
            </AnimatePresence>

            {/* Submit / Cancel */}
            <div className="flex gap-3 mt-6">
              <motion.button id="analyze-btn" onClick={handleAnalyze}
                disabled={!canSubmit() || loading}
                whileHover={canSubmit() && !loading ? { scale: 1.02 } : {}}
                whileTap={canSubmit() && !loading ? { scale: 0.98 } : {}}
                className={`flex-1 flex items-center justify-center gap-2.5 py-4 rounded-2xl text-base font-semibold transition-all duration-300 ${canSubmit() && !loading
                  ? "bg-primary text-primary-foreground shadow-lg hover:shadow-[0_8px_20px_oklch(0.55_0.22_275/30%)]"
                  : "bg-black/5 text-muted-foreground cursor-not-allowed"}`}>
                {loading ? (
                  <>
                    <div className="w-5 h-5 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                    <span>Menganalisis…</span>
                  </>
                ) : (
                  <>
                    <Shield className="w-5 h-5 text-primary-foreground" />
                    <span className="text-primary-foreground">Analisis Sekarang</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </motion.button>
              {loading && activeTab === "chat" && (
                <button onClick={handleCancel}
                  className="px-4 rounded-2xl text-sm font-medium glass border border-black/5 text-muted-foreground hover:text-foreground transition-colors">
                  Batal
                </button>
              )}
            </div>

            <p className="mt-4 text-center text-xs text-muted-foreground/50 leading-relaxed">
              Data diproses secara aman. Tidak perlu akun. Hasil bersifat indikatif, bukan keputusan hukum.
            </p>
          </motion.div>

          {/* Feature badges */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
            className="flex flex-wrap items-center justify-center gap-2 mt-6">
            {["OJK Real-time", "WHOIS Intel", "Berita Media", "AI Guardian", "Shareable Report"].map((feat) => (
              <span key={feat}
                className="glass rounded-full px-3 py-1 text-[10px] font-medium text-muted-foreground border border-black/5">
                ✓ {feat}
              </span>
            ))}
          </motion.div>
        </div>
      </main>
    </>
  );
}
