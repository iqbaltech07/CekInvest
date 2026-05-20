"use client";

import { useRef } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "motion/react";
import { ArrowRight, Sparkles, ShieldCheck } from "lucide-react";

/* Floating particle orb */
function Orb({
  size,
  x,
  y,
  color,
  delay = 0,
}: {
  size: number;
  x: string;
  y: string;
  color: string;
  delay?: number;
}) {
  return (
    <motion.div
      className="orb pointer-events-none"
      style={{
        width: size,
        height: size,
        left: x,
        top: y,
        background: color,
      }}
      animate={{
        scale: [1, 1.15, 1],
        opacity: [0.6, 1, 0.6],
      }}
      transition={{
        duration: 6 + delay,
        repeat: Infinity,
        ease: "easeInOut",
        delay,
      }}
    />
  );
}

/* Floating badge chip */
function FloatingBadge({
  children,
  delay,
  className,
}: {
  children: React.ReactNode;
  delay: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: [0, -6, 0] }}
      transition={{
        opacity: { duration: 0.6, delay },
        y: { duration: 3.5, repeat: Infinity, ease: "easeInOut", delay },
      }}
      className={`glass rounded-2xl px-5 py-3 text-xs font-medium border border-black/4 shadow-sm backdrop-blur-3xl ${className ?? ""}`}
    >
      {children}
    </motion.div>
  );
}

export default function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref });
  const y = useTransform(scrollYProgress, [0, 1], [0, 80]);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  return (
    <section
      ref={ref}
      className="relative flex flex-col items-center justify-center sm:min-h-screen pb-16 overflow-hidden noise"
    >
      {/* Ambient orbs */}
      <Orb size={500} x="10%" y="-15%" color="oklch(0.62 0.22 275 / 18%)" delay={0} />
      <Orb size={350} x="65%" y="30%" color="oklch(0.72 0.19 310 / 12%)" delay={2} />
      <Orb size={280} x="5%" y="60%" color="oklch(0.75 0.18 155 / 8%)" delay={4} />

      {/* Radial grid */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(circle, oklch(0 0 0 / 4%) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse 80% 80% at 50% 50%, black, transparent)",
        }}
      />

      <motion.div
        style={{ y, opacity }}
        className="relative z-10 flex flex-col items-center text-center px-6 max-w-5xl mx-auto  mt-30 sm:-mt-20"
      >
        {/* Tag pill */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-8 inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-primary border border-primary/20"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Pelindung Pintar dari Penipuan Keuangan — Indonesia</span>
        </motion.div>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="text-[clamp(2.5rem,7vw,5.5rem)] font-extrabold leading-[1.02] tracking-[-0.04em] mb-6"
        >
          Lindungi Investasimu
          <br />
          <span className="text-gradient">dari Rayuan Penipu</span>
        </motion.h1>

        {/* Sub */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.35 }}
          className="text-[clamp(1.05rem,2vw,1.25rem)] text-muted-foreground max-w-[640px] leading-[1.6] mb-10 tracking-tight"
        >
          Tempel obrolan WhatsApp, unggah gambar tangkapan layar, atau cek alamat website investasi. 
          Sistem kami akan memeriksa{" "}
          <span className="text-foreground font-medium">
            rayuan manis, janji untung palsu, dan ciri penipuan
          </span>{" "}
          dalam hitungan detik — dengan penjelasan sederhana yang mudah dimengerti semua umur.
        </motion.p>

        {/* CTA group */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="flex flex-col sm:flex-row items-center gap-3"
        >
          <Link
            href="/analyze"
            id="hero-cta-primary"
            className="group inline-flex items-center gap-2 px-8 py-3.5 rounded-full text-[15px] font-semibold bg-primary text-primary-foreground shadow-[0_4px_14px_oklch(0.55_0.22_275/25%)] hover:shadow-[0_6px_20px_oklch(0.55_0.22_275/40%)] hover:-translate-y-0.5 transition-all duration-300"
          >
            Cek Sekarang (Gratis)
            <ArrowRight className="w-4.5 h-4.5 group-hover:translate-x-1 transition-transform duration-200" />
          </Link>
          <Link
            href="/scam-radar"
            id="hero-cta-secondary"
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full text-[15px] font-medium text-muted-foreground hover:text-foreground glass glass-hover"
          >
            Pantau Peta Rawan Penipuan
          </Link>
        </motion.div>

        {/* Trust line */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="mt-8 flex items-center gap-2 text-xs text-muted-foreground"
        >
          <ShieldCheck className="w-4 h-4 text-[--brand-emerald]" />
          <span>Gratis · Sangat Aman · Privasi Terjaga Penuh</span>
        </motion.div>
      </motion.div>

      {/* Floating stat badges */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute left-[8%] top-[38%] hidden lg:block">
          <FloatingBadge delay={0.9}>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[--brand-emerald]" />
              <span className="text-foreground/80">10.000+ Laporan Teratasi</span>
            </div>
          </FloatingBadge>
        </div>
        <div className="absolute right-[8%] top-[42%] hidden lg:block">
          <FloatingBadge delay={1.4}>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[--brand-amber]" />
              <span className="text-foreground/80">Sangat Cepat & Akurat</span>
            </div>
          </FloatingBadge>
        </div>
        <div className="absolute left-[12%] bottom-[22%] hidden lg:block">
          <FloatingBadge delay={1.1}>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary" />
              <span className="text-foreground/80">Hasil Cek &lt; 30 Detik</span>
            </div>
          </FloatingBadge>
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
    </section>
  );
}
