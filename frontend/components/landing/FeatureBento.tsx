"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import {
  MessageSquare,
  ImageIcon,
  Globe,
  Brain,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  Users,
} from "lucide-react";

const features = [
  {
    id: "multi-input",
    icon: MessageSquare,
    title: "Cek Lewat Apa Saja",
    description:
      "Cukup tempel obrolan WhatsApp, unggah foto bukti chat, atau masukkan alamat website. Sistem kami langsung memprosesnya seketika.",
    accent: "oklch(0.55 0.22 275)",
    size: "large",
    tags: ["Chat WA", "Foto Bukti", "Link Web"],
  },
  {
    id: "emotional-detection",
    icon: Brain,
    title: "Deteksi Rayuan Penipu",
    description:
      "Menyadari desakan buru-buru, kuota habis palsu, dan rayuan manis yang dirancang agar uang tabungan Anda melayang.",
    accent: "oklch(0.70 0.16 75)",
    size: "small",
    tags: ["Buru-buru", "Rayuan Manis"],
  },
  {
    id: "risk-scoring",
    icon: TrendingUp,
    title: "Tingkat Bahaya Jelas",
    description:
      "Dapatkan skor kepastian bahaya yang mudah dipahami siapa saja, dari 0 (Sangat Aman) hingga 100 (Sangat Bahaya).",
    accent: "oklch(0.60 0.22 22)",
    size: "small",
    tags: ["Aman", "Bahaya"],
  },
  {
    id: "intelligence-layers",
    icon: ShieldCheck,
    title: "Pemeriksaan Sangat Lengkap",
    description:
      "Memeriksa status resmi OJK, usia website, berita media massa, hingga riwayat laporan penipuan dari warga lainnya secara bersamaan.",
    accent: "oklch(0.65 0.18 155)",
    size: "wide",
    tags: ["Daftar OJK", "Usia Web", "Laporan Warga"],
  },
  {
    id: "shareable-report",
    icon: Users,
    title: "Kirim Hasil ke Keluarga",
    description:
      "Bagikan hasil analisis langsung ke grup WhatsApp keluarga dengan format tulisan yang sopan, ramah, dan mudah dibaca orang tua.",
    accent: "oklch(0.55 0.22 275)",
    size: "small",
    tags: ["Kirim WA", "Sopan & Jelas"],
  },
  {
    id: "ai-guardian",
    icon: AlertTriangle,
    title: "Asisten Keamanan 24 Jam",
    description:
      "Tanya jawab langsung dengan asisten pintar kami untuk tips menghadapi penawar, cara menolak dengan sopan, atau bantuan melapor.",
    accent: "oklch(0.65 0.19 310)",
    size: "full",
    tags: ["Tanya AI", "Bantuan 24/7"],
  },
];

type FeatureSize = "large" | "small" | "wide" | "full";

const sizeClasses: Record<FeatureSize, string> = {
  large: "md:col-span-2 md:row-span-2",
  small: "md:col-span-1",
  wide: "md:col-span-2",
  full: "md:col-span-3",
};

function FeatureCard({ feature, index }: { feature: (typeof features)[0]; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const Icon = feature.icon;
  const isLarge = feature.size === "large";

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.98 }}
      animate={inView ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.4, delay: index * 0.05, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`${sizeClasses[feature.size as FeatureSize]} glass glass-hover rounded-[1.75rem] p-6 md:p-7 flex flex-col gap-4 relative overflow-hidden group`}
      id={`feature-${feature.id}`}
    >
      {/* Background accent glow */}
      <div
        className="absolute -top-10 -right-10 w-48 h-48 rounded-full blur-[60px] opacity-0 group-hover:opacity-10 transition-opacity duration-700 pointer-events-none"
        style={{ background: feature.accent }}
      />

      {/* Header Info */}
      <div className="flex flex-col gap-3 relative z-10">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            background: `${feature.accent}10`,
            border: `1px solid ${feature.accent}15`,
          }}
        >
          <Icon className="w-5 h-5" style={{ color: feature.accent }} strokeWidth={1.5} />
        </div>

        <div className="flex flex-col gap-1.5">
          <h3 className={`font-bold tracking-tight ${isLarge ? "text-xl md:text-2xl" : "text-[17px]"}`}>
            {feature.title}
          </h3>
          <p className={`text-muted-foreground leading-snug ${isLarge ? "text-sm md:text-[15px] max-w-[95%]" : "text-[13px]"}`}>
            {feature.description}
          </p>
        </div>
      </div>

      {/* Visual Component */}
      <div className="mt-2 flex-1 flex items-center justify-center relative z-10 min-h-[60px]">
        {feature.id === "multi-input" && <MultiInputVisual />}
        {feature.id === "intelligence-layers" && <IntelligenceVisual accent={feature.accent} />}
        {feature.id === "ai-guardian" && <GuardianVisual accent={feature.accent} />}
        {feature.id === "risk-scoring" && <RiskVisual accent={feature.accent} />}
        {feature.id === "emotional-detection" && <EmotionalVisual accent={feature.accent} />}
        {feature.id === "shareable-report" && <ShareVisual />}
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mt-auto relative z-10">
        {feature.tags.map((tag) => (
          <span
            key={tag}
            className="text-[9px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider"
            style={{
              background: `${feature.accent}10`,
              color: feature.accent,
              border: `1px solid ${feature.accent}15`,
            }}
          >
            {tag}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

/* ─── Visual Components ─── */

function MultiInputVisual() {
  return (
    <div className="w-full h-full flex items-center justify-center gap-3 py-2">
      <motion.div
        animate={{ y: [0, -4, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="w-12 h-16 rounded-lg glass border-primary/20 flex flex-col p-1.5 gap-1.5"
      >
        <div className="w-full h-1 bg-primary/10 rounded-full" />
        <div className="w-2/3 h-1 bg-primary/10 rounded-full" />
        <div className="mt-auto w-full h-4 bg-primary/20 rounded-md" />
      </motion.div>
      <motion.div
        animate={{ y: [0, 4, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        className="w-14 h-20 rounded-lg glass border-primary/20 flex flex-col p-1.5 gap-1.5 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-primary/5" />
        <ImageIcon className="w-5 h-5 m-auto opacity-40 text-primary" />
      </motion.div>
      <motion.div
        animate={{ y: [0, -2, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        className="w-12 h-12 rounded-full glass border-primary/20 flex items-center justify-center"
      >
        <Globe className="w-5 h-5 opacity-40 text-primary" />
      </motion.div>
    </div>
  );
}

function IntelligenceVisual({ accent }: { accent: string }) {
  return (
    <div className="w-full h-full flex flex-col gap-1.5 p-3 justify-center">
      {[1, 2, 3, 4].map((i) => (
        <motion.div
          key={i}
          initial={{ width: "30%" }}
          animate={{ width: ["30%", "85%", "30%"] }}
          transition={{ duration: 4, repeat: Infinity, delay: i * 0.3 }}
          className="h-1.5 rounded-full bg-muted/90 overflow-hidden"
        >
          <div className="h-full w-4 bg-primary rounded-full" style={{ background: accent }} />
        </motion.div>
      ))}
    </div>
  );
}

function RiskVisual({ accent }: { accent: string }) {
  return (
    <div className="relative w-20 h-20 flex items-center justify-center">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="42" stroke="currentColor" strokeWidth="10" fill="transparent" className="text-muted/10" />
        <motion.circle
          cx="50" cy="50" r="42" stroke={accent} strokeWidth="10" fill="transparent"
          strokeDasharray={263.8}
          initial={{ strokeDashoffset: 263.8 }}
          animate={{ strokeDashoffset: 263.8 * 0.35 }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-lg font-bold" style={{ color: accent }}>85</span>
    </div>
  );
}

function GuardianVisual({ accent }: { accent: string }) {
  return (
    <div className="w-full h-full flex items-center justify-around px-6">
      <div className="flex flex-col gap-2 w-1/3">
        <div className="h-2 w-full bg-muted/15 rounded-full" />
        <div className="h-2 w-4/5 bg-muted/15 rounded-full" />
        <div className="h-2 w-3/5 bg-muted/15 rounded-full" />
      </div>
      <motion.div
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 3, repeat: Infinity }}
        className="w-16 h-16 rounded-full flex items-center justify-center relative"
        style={{ background: `${accent}10`, border: `1px solid ${accent}20` }}
      >
        <ShieldCheck className="w-8 h-8" style={{ color: accent }} />
        <div className="absolute inset-0 rounded-full animate-ping opacity-10" style={{ background: accent }} />
      </motion.div>
    </div>
  );
}

function EmotionalVisual({ accent }: { accent: string }) {
  return (
    <div className="relative">
      <Brain className="w-14 h-14 opacity-20" style={{ color: accent }} />
      <motion.div
        animate={{ scale: [1, 1.4, 1], opacity: [0, 0.4, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="absolute inset-0 flex items-center justify-center"
      >
        <div className="w-6 h-6 rounded-full" style={{ background: accent }} />
      </motion.div>
    </div>
  );
}

function ShareVisual() {
  return (
    <div className="w-28 h-16 glass rounded-md border-primary/20 p-2 flex flex-col gap-1.5 overflow-hidden shadow-md">
      <div className="flex items-center gap-1.5">
        <div className="w-3 h-3 rounded-full bg-emerald-500" />
        <div className="w-10 h-1 bg-muted/30 rounded-full" />
      </div>
      <div className="h-1 w-full bg-muted/15 rounded-full" />
      <div className="h-1 w-2/3 bg-muted/15 rounded-full" />
    </div>
  );
}

export default function FeatureBento() {
  const titleRef = useRef<HTMLDivElement>(null);
  const titleInView = useInView(titleRef, { once: true, margin: "-60px" });

  return (
    <section id="fitur" className="section px-6 relative bg-secondary/20">
      {/* Ambient orb */}
      <div
        className="orb w-[600px] h-[600px] opacity-5 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
        style={{ background: "oklch(0.55 0.22 275)" }}
      />

      <div className="max-w-6xl mx-auto relative z-10">
        {/* Header */}
        <motion.div
          ref={titleRef}
          initial={{ opacity: 0, y: 16 }}
          animate={titleInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-10 md:mb-12"
        >
          <p className="text-xs font-bold tracking-[0.25em] uppercase text-primary mb-3">
            Fitur Pintar Sentra
          </p>
          <h2 className="text-[clamp(2rem,4vw,3.5rem)] font-extrabold tracking-tight mb-4 leading-tight">
            Fitur Praktis yang Menjaga
            <br />
            <span className="text-muted-foreground font-medium italic">Tabungan & Masa Depan Keluarga Anda</span>
          </h2>
        </motion.div>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4 auto-rows-[minmax(140px,auto)]">
          {features.map((feature, i) => (
            <FeatureCard key={feature.id} feature={feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}

