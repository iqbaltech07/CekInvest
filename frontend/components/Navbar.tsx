"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { Shield, Menu, X } from "lucide-react";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { href: "/#cara-kerja", label: "Cara Kerja" },
    { href: "/scam-radar", label: "Radar Scam" },
    { href: "/submit-report", label: "Laporkan" },
    { href: "/#statistik", label: "Statistik" },
  ];

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${scrolled
        ? "glass border-b border-black/5 py-3.5"
        : "bg-transparent py-6"
        }`}
    >
      <nav className="max-w-6xl mx-auto px-6 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative">
            <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-md group-hover:shadow-[0_4px_12px_oklch(0.55_0.22_275/30%)] transition-shadow duration-300">
              <Shield className="w-4.5 h-4.5 text-primary-foreground" strokeWidth={2.5} />
            </div>
            <div className="absolute -inset-1 rounded-xl bg-primary opacity-0 group-hover:opacity-20 blur-sm transition-opacity duration-300" />
          </div>
          <span className="font-semibold text-[17px] tracking-tight">
            <span className="text-gradient">Cek</span>
            <span className="text-foreground/90">Invest</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 font-medium"
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/analyze"
            id="nav-cta"
            className="px-5 py-2 rounded-full text-[14px] font-semibold bg-primary text-primary-foreground shadow-[0_2px_10px_oklch(0.55_0.22_275/20%)] hover:shadow-[0_4px_14px_oklch(0.55_0.22_275/30%)] hover:-translate-y-0.5 transition-all duration-300"
          >
            Cek Sekarang
          </Link>
        </div>

        {/* Mobile burger */}
        <button
          className="md:hidden p-2 rounded-xl glass text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="md:hidden glass border-t border-black/5 overflow-hidden"
          >
            <div className="max-w-6xl mx-auto px-6 py-4 flex flex-col gap-3">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors py-2 font-medium"
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href="/analyze"
                onClick={() => setMobileOpen(false)}
                className="mt-2 px-5 py-2.5 rounded-full text-sm font-semibold bg-primary text-primary-foreground text-center hover:opacity-90 transition-opacity"
              >
                Cek Sekarang
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
