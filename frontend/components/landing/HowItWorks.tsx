"use client";

import { useRef } from "react";
import { motion, useInView } from "motion/react";
import {
  ClipboardPaste,
  BrainCircuit,
  BarChart3,
} from "lucide-react";

const steps = [
  {
    number: "01",
    icon: ClipboardPaste,
    title: "Input Data Investasi",
    description:
      "Paste percakapan WhatsApp/Telegram, upload screenshot penawaran, atau masukkan URL website investasi.",
    subItems: ["Chat / percakapan", "Screenshot gambar", "Link URL"],
    accent: "oklch(0.55 0.22 275)",
  },
  {
    number: "02",
    icon: BrainCircuit,
    title: "AI Analisis Mendalam",
    description:
      "SENTRA AI memindai pola manipulasi psikologis, fake urgency, social proof palsu, dan 40+ red flag finansial.",
    subItems: ["OCR ekstraksi konten", "Behavioral analysis", "Pattern matching"],
    accent: "oklch(0.65 0.19 310)",
  },
  {
    number: "03",
    icon: BarChart3,
    title: "Risk Score & Laporan",
    description:
      "Dapatkan skor risiko 0–100 dan penjelasan yang jelas — bukan jargon teknis, tapi bahasa yang bisa kamu pahami.",
    subItems: ["Risk Score 0–100", "Red flag breakdown", "Rekomendasi tindakan"],
    accent: "oklch(0.65 0.18 155)",
  },
];

function StepCard({
  step,
  index,
}: {
  step: (typeof steps)[0];
  index: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const Icon = step.icon;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="relative flex flex-col"
    >
      {/* Connector line (desktop xl+) */}
      {index < steps.length - 1 && (
        <div className="absolute top-14 left-full w-full h-px hidden xl:block">
          <motion.div
            initial={{ scaleX: 0 }}
            animate={inView ? { scaleX: 1 } : {}}
            transition={{ duration: 0.8, delay: index * 0.15 + 0.4 }}
            className="h-px origin-left"
            style={{
              background: `linear-gradient(90deg, ${step.accent}60, transparent)`,
            }}
          />
        </div>
      )}

      {/* Card */}
      <div className="glass glass-hover rounded-2xl sm:rounded-[2rem] p-6 sm:p-8 flex flex-col gap-5 sm:gap-6 h-full">
        {/* Step number + icon */}
        <div className="flex items-start justify-between">
          <div
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center shadow-md"
            style={{
              background: `${step.accent}20`,
              border: `1px solid ${step.accent}40`,
            }}
          >
            <Icon className="w-6 h-6 sm:w-7 sm:h-7" style={{ color: step.accent }} strokeWidth={1.8} />
          </div>
          <span
            className="text-4xl sm:text-5xl font-black tabular-nums leading-none"
            style={{ color: `${step.accent}20` }}
          >
            {step.number}
          </span>
        </div>

        {/* Text */}
        <div>
          <h3 className="text-base sm:text-lg font-semibold mb-2 tracking-tight">{step.title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
        </div>

        {/* Sub items */}
        <div className="mt-auto flex flex-col gap-1.5">
          {step.subItems.map((item) => (
            <div key={item} className="flex items-center gap-2 text-xs text-muted-foreground">
              <div
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: step.accent }}
              />
              {item}
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

export default function HowItWorks() {
  const titleRef = useRef<HTMLDivElement>(null);
  const titleInView = useInView(titleRef, { once: true, margin: "-60px" });

  return (
    <section id="cara-kerja" className="section relative px-4 sm:px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <motion.div
          ref={titleRef}
          initial={{ opacity: 0, y: 24 }}
          animate={titleInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-12 sm:mb-16"
        >
          <p className="text-[13px] font-semibold tracking-[0.15em] uppercase text-primary mb-4">
            Cara Kerja
          </p>
          <h2 className="text-[clamp(1.75rem,4vw,3.25rem)] font-bold tracking-tight mb-5 leading-tight">
            Tiga langkah, satu keputusan
            <br />
            <span className="text-muted-foreground font-normal">yang lebih aman</span>
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto text-sm leading-relaxed">
            Tidak perlu pengetahuan investasi atau teknis. CekInvest dirancang
            untuk semua orang — dari pelajar hingga profesional.
          </p>
        </motion.div>

        {/* Steps grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 xl:gap-8 relative">
          {steps.map((step, i) => (
            <StepCard key={step.number} step={step} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
