"use client";

import { useRef, useEffect, useState } from "react";
import { motion, useInView, animate } from "motion/react";

const stats = [
  { value: 10000, suffix: "+", label: "Scam terdeteksi", accent: "oklch(0.55 0.22 275)" },
  { value: 98, suffix: "%", label: "Tingkat akurasi AI", accent: "oklch(0.65 0.18 155)" },
  { value: 30, suffix: "s", label: "Waktu analisis rata-rata", accent: "oklch(0.70 0.16 75)" },
  { value: 500, suffix: "+", label: "Pola scam dikenali", accent: "oklch(0.65 0.19 310)" },
];

function CountUp({
  target,
  suffix,
  accent,
  inView,
}: {
  target: number;
  suffix: string;
  accent: string;
  inView: boolean;
}) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, target, {
      duration: 2,
      ease: [0.25, 0.46, 0.45, 0.94],
      onUpdate(v) {
        setValue(Math.round(v));
      },
    });
    return controls.stop;
  }, [inView, target]);

  return (
    <span className="stat-number tracking-tighter" style={{ color: accent }}>
      {value.toLocaleString("id-ID")}
      {suffix}
    </span>
  );
}

export default function Stats() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const titleRef = useRef<HTMLDivElement>(null);
  const titleInView = useInView(titleRef, { once: true, margin: "-60px" });

  return (
    <section id="statistik" className="section px-6 relative">
      {/* Separator glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div
          ref={titleRef}
          initial={{ opacity: 0, y: 24 }}
          animate={titleInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-14"
        >
          <p className="text-[13px] font-semibold tracking-[0.15em] uppercase text-primary mb-4">
            Dampak Nyata
          </p>
          <h2 className="text-[clamp(2rem,4vw,3.25rem)] font-bold tracking-tight leading-tight">
            Dipercaya ribuan pengguna
            <br />
            <span className="text-muted-foreground font-normal">di seluruh Indonesia</span>
          </h2>
        </motion.div>

        {/* Stats grid */}
        <div ref={ref} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass glass-hover rounded-[2rem] p-8 flex flex-col gap-3 text-center items-center relative overflow-hidden group"
              id={`stat-${i}`}
            >
              {/* Glow */}
              <div
                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-[2rem] pointer-events-none"
                style={{
                  background: `radial-gradient(circle at 50% 50%, ${stat.accent}08, transparent 70%)`,
                }}
              />

              <CountUp
                target={stat.value}
                suffix={stat.suffix}
                accent={stat.accent}
                inView={inView}
              />
              <p className="text-xs text-muted-foreground font-medium leading-snug">
                {stat.label}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center mt-14"
        >
          <p className="text-sm text-muted-foreground mb-6">
            Bergabung bersama pengguna yang sudah terlindungi dari scam finansial
          </p>
          <a
            href="/analyze"
            id="stats-cta"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full text-sm font-semibold bg-primary text-primary-foreground shadow-lg hover:shadow-[0_8px_20px_oklch(0.55_0.22_275/30%)] hover:scale-105 transition-all duration-300"
          >
            Mulai Analisis Gratis
          </a>
        </motion.div>
      </div>
    </section>
  );
}
