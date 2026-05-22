"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "motion/react";
import {
  ShieldCheck, ShieldAlert, ShieldQuestion,
  Building2, Globe, Newspaper, ExternalLink,
  AlertTriangle, Copy, Check, ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { FormattedText } from "@/components/ui/formatted-text";
import Navbar from "@/components/Navbar";
import { getSharedReport, getShareMeta } from "@/lib/api";
import type { AnalysisResult, RiskLevel, OjkStatus, ShareMeta } from "@/lib/types";

/* ─── Risk helpers ───────────────────────────────────────────────────── */
function getRiskConfig(level: RiskLevel) {
  const map: Record<RiskLevel, { label: string; color: string; icon: React.ElementType }> = {
    SAFE:     { label: "Aman",      color: "oklch(0.72 0.17 155)", icon: ShieldCheck },
    LOW:      { label: "Rendah",    color: "oklch(0.78 0.16 140)", icon: ShieldCheck },
    MEDIUM:   { label: "Waspada",   color: "oklch(0.80 0.16 75)",  icon: ShieldQuestion },
    HIGH:     { label: "Berbahaya", color: "oklch(0.68 0.20 35)",  icon: ShieldAlert },
    CRITICAL: { label: "Kritis!",   color: "oklch(0.60 0.24 22)",  icon: ShieldAlert },
  };
  return map[level] ?? map.MEDIUM;
}

const OJK_CONFIG: Record<OjkStatus, { label: string; color: string; bg: string }> = {
  TERDAFTAR:          { label: "Terdaftar OJK ✓",       color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200" },
  TIDAK_TERDAFTAR:    { label: "Tidak Terdaftar OJK",   color: "text-orange-600",  bg: "bg-orange-50 border-orange-200" },
  TERINDIKASI_ILEGAL: { label: "Terindikasi Ilegal ⚠️", color: "text-red-600",     bg: "bg-red-50 border-red-200" },
  TIDAK_DITEMUKAN:    { label: "Tidak Ditemukan di OJK",color: "text-zinc-500",    bg: "bg-zinc-50 border-zinc-200" },
};

/* ─── Page ───────────────────────────────────────────────────────────── */
export default function SharePage() {
  const { slug } = useParams<{ slug: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [meta, setMeta] = useState<ShareMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!slug) return;
    Promise.all([getSharedReport(slug), getShareMeta(slug)])
      .then(([r, m]) => { setResult(r); setMeta(m); })
      .catch(() => setError("Laporan tidak ditemukan atau sudah kadaluarsa."))
      .finally(() => setLoading(false));
  }, [slug]);

  const handleCopyWa = async () => {
    if (!meta) return;
    await navigator.clipboard.writeText(meta.whatsappText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  );

  if (error || !result) return (
    <>
      <Navbar />
      <main className="flex flex-col items-center justify-center min-h-screen gap-4 px-6">
        <ShieldQuestion className="w-12 h-12 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{error || "Laporan tidak ditemukan."}</p>
        <Link href="/analyze"
          className="flex items-center gap-2 px-5 py-2.5 rounded-2xl text-sm font-semibold bg-primary text-primary-foreground">
          Buat Analisis Baru <ArrowRight className="w-4 h-4" />
        </Link>
      </main>
    </>
  );

  const { label, color, icon: VerdictIcon } = getRiskConfig(result.riskLevel);
  const ojkCfg = result.ojkStatus ? OJK_CONFIG[result.ojkStatus] : null;

  return (
    <>
      <Navbar />
      <main className="flex flex-col flex-1 min-h-screen pt-24 pb-16 px-6 relative overflow-hidden">
        {/* Ambient */}
        <div className="orb w-[500px] h-[500px] opacity-10 -right-40 -top-20"
          style={{ background: `${color} / 30%` }} />

        <div className="max-w-2xl mx-auto w-full relative z-10">
          {/* Shared badge */}
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-center mb-8">
            <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-muted-foreground border border-black/5">
              <ShieldCheck className="w-3.5 h-3.5 text-primary" />
              Laporan publik dari CekInvest · Bukan keputusan hukum
            </div>
          </motion.div>

          {/* Main result card */}
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }} id="share-result-hero"
            className="glass rounded-3xl p-6 md:p-10 border border-black/5 mb-5 shadow-xl">
            {/* Score + verdict */}
            <div className="flex flex-col items-center text-center gap-4 pb-6 border-b border-black/5">
              <div className="flex items-center gap-3">
                <VerdictIcon className="w-8 h-8" style={{ color }} />
                <span className="text-4xl font-black tabular-nums" style={{ color }}>
                  {result.riskScore}
                </span>
                <span className="text-muted-foreground text-sm font-medium">/ 100</span>
              </div>
              <div>
                <p className="font-bold text-xl" style={{ color }}>{label}</p>
                <Badge variant="outline" className="text-[10px] mt-1 border-current" style={{ color }}>
                  {result.riskLevel}
                </Badge>
              </div>
              <FormattedText text={result.summary} className="text-sm text-muted-foreground leading-relaxed max-w-lg" />
            </div>

            {/* Intelligence findings */}
            <div className="pt-5 flex flex-col gap-3">
              {ojkCfg && (
                <div className={`flex items-center gap-2.5 p-3.5 rounded-2xl border text-xs font-semibold ${ojkCfg.bg} ${ojkCfg.color}`}>
                  <Building2 className="w-4 h-4 flex-shrink-0" />
                  <span>{ojkCfg.label}</span>
                  {result.ojkEntityName && <span className="opacity-70 font-normal">· {result.ojkEntityName}</span>}
                </div>
              )}

              {result.domainAgeDays !== null && result.domainAgeDays !== undefined && (
                <div className={`flex items-center gap-2.5 p-3.5 rounded-2xl border text-xs font-semibold ${result.domainAgeDays < 90
                  ? "bg-red-50 border-red-200 text-red-600" : "bg-zinc-50 border-zinc-200 text-zinc-500"}`}>
                  <Globe className="w-4 h-4 flex-shrink-0" />
                  <span>Domain berumur {result.domainAgeDays} hari{result.domainCountry ? ` · Hosting dari ${result.domainCountry}` : ""}</span>
                </div>
              )}

              {result.mediaHitCount !== null && result.mediaHitCount !== undefined && result.mediaHitCount > 0 && (
                <div className="flex items-center gap-2.5 p-3.5 rounded-2xl border text-xs font-semibold bg-orange-50 border-orange-200 text-orange-600">
                  <Newspaper className="w-4 h-4 flex-shrink-0" />
                  <span>Ditemukan {result.mediaHitCount} berita negatif di media Indonesia</span>
                </div>
              )}

              {/* Red flags summary */}
              {result.redFlags.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-semibold text-foreground/60 mb-2.5">
                    {result.redFlags.length} Red Flag Terdeteksi:
                  </p>
                  <div className="flex flex-col gap-2">
                    {result.redFlags.slice(0, 4).map((flag, i) => (
                      <div key={i} className="flex items-start gap-2.5 p-3 rounded-xl bg-black/3 border border-black/5">
                        <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-orange-500" />
                        <div>
                          <span className="text-[11px] font-semibold text-foreground/80">{flag.category}</span>
                          <p className="text-[11px] text-muted-foreground leading-relaxed">{flag.description}</p>
                        </div>
                      </div>
                    ))}
                    {result.redFlags.length > 4 && (
                      <p className="text-[10px] text-muted-foreground text-center">
                        +{result.redFlags.length - 4} red flag lainnya
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>

          {/* WhatsApp share copy (PRD 5.5) */}
          {meta && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }} id="wa-share-section"
              className="glass rounded-3xl p-5 border border-black/5 mb-5">
              <p className="text-xs font-semibold text-foreground/70 mb-3">
                📲 Salin pesan untuk dikirim ke grup WhatsApp:
              </p>
              <pre className="text-[11px] text-foreground/70 leading-relaxed whitespace-pre-wrap bg-black/3 rounded-2xl p-4 mb-3 font-sans">
                {meta.whatsappText}
              </pre>
              <button onClick={handleCopyWa} id="copy-wa-btn"
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 hover:bg-emerald-500/20 transition-colors">
                {copied ? <><Check className="w-3.5 h-3.5" /> Berhasil disalin!</> : <><Copy className="w-3.5 h-3.5" /> Salin Pesan WA</>}
              </button>
            </motion.div>
          )}

          {/* CTA: analyze your own */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }} className="flex flex-col sm:flex-row gap-3">
            <Link href="/analyze" id="cta-analyze"
              className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-semibold bg-primary text-primary-foreground shadow-md hover:scale-[1.02] transition-all duration-200">
              <ShieldCheck className="w-4 h-4" /> Cek Investasimu Sendiri
              <ArrowRight className="w-4 h-4" />
            </Link>
            <a href="https://sikapiuangmu.ojk.go.id/FrontEnd/CMS/Category/66"
              target="_blank" rel="noopener noreferrer" id="ojk-report-link"
              className="flex items-center justify-center gap-2 px-5 py-3.5 rounded-2xl text-sm font-semibold glass border border-black/5 text-muted-foreground hover:text-foreground transition-colors">
              <ExternalLink className="w-4 h-4" /> Lapor ke OJK
            </a>
          </motion.div>

          <p className="mt-6 text-center text-xs text-muted-foreground/40 leading-relaxed">
            Laporan ini dibuat oleh CekInvest — Platform deteksi scam investasi berbasis AI.<br />
            Hasil bersifat indikatif. Bukan keputusan hukum atau finansial resmi.
          </p>
        </div>
      </main>
    </>
  );
}
