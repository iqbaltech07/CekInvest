"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  Radio, MapPin, Phone, Globe, CreditCard,
  Search, Flame, TrendingUp, Calendar, Info,
  AlertCircle, Activity, ChevronRight, ShieldAlert, Sparkles
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { getScamClusters, getRegionalRadar } from "@/lib/api";
import type { ScamCluster, RegionalRadarRegion } from "@/lib/api";

type TabType = "clusters" | "regions";

export default function ScamRadarPage() {
  const [activeTab, setActiveTab] = useState<TabType>("clusters");
  const [clusters, setClusters] = useState<ScamCluster[]>([]);
  const [regions, setRegions] = useState<RegionalRadarRegion[]>([]);
  const [totalMonitored, setTotalMonitored] = useState(0);

  // Filters
  const [riskFilter, setRiskFilter] = useState<string>("ALL");
  const [searchRegion, setSearchRegion] = useState<string>("");
  const [debouncedSearchRegion, setDebouncedSearchRegion] = useState<string>("");
  
  // Loading and Errors
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const riskLevels = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

  // Debounce search query to prevent spamming the backend API
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchRegion(searchRegion);
    }, 500); // 500ms delay

    return () => {
      clearTimeout(handler);
    };
  }, [searchRegion]);

  // Fetch regional data once on mount
  useEffect(() => {
    let cancelled = false;

    async function loadRegionalData() {
      try {
        const radarRes = await getRegionalRadar();
        if (cancelled) return;
        setRegions(radarRes.all_regions || []);
        setTotalMonitored(radarRes.total_monitored_regions || 0);
      } catch (err) {
        console.error("Gagal memuat data radar wilayah", err);
      }
    }

    void loadRegionalData();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch clusters dynamically when search or filters change
  useEffect(() => {
    const controller = new AbortController();

    async function loadRadarData() {
      try {
        setLoading(true);
        const clusterRes = await getScamClusters(
          {
            risk_level: riskFilter === "ALL" ? undefined : riskFilter,
            region: debouncedSearchRegion || undefined,
          },
          controller.signal
        );

        setClusters(clusterRes.clusters);
        setError("");
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError("Gagal memuat data radar penipuan. Silakan periksa koneksi internet Anda.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadRadarData();
    return () => {
      controller.abort();
    };
  }, [riskFilter, debouncedSearchRegion]);

  const getRiskColor = (level: string) => {
    switch (level.toUpperCase()) {
      case "CRITICAL":
        return "text-rose bg-rose/10 border-rose/20 shadow-[0_0_15px_oklch(0.60_0.22_22/10%)]";
      case "HIGH":
        return "text-amber bg-amber/10 border-amber/20 shadow-[0_0_15px_oklch(0.70_0.16_75/10%)]";
      case "MEDIUM":
        return "text-indigo bg-indigo/10 border-indigo/20";
      case "LOW":
        return "text-emerald bg-emerald/10 border-emerald/20";
      default:
        return "text-muted-foreground bg-black/5 border-black/5";
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend.toUpperCase()) {
      case "VIRAL":
        return "text-rose bg-rose/10 border-rose/20 animate-pulse";
      case "SPIKING":
        return "text-amber bg-amber/10 border-amber/20";
      case "RISING":
        return "text-indigo bg-indigo/10 border-indigo/20";
      default:
        return "text-muted-foreground bg-black/5 border-black/5";
    }
  };

  const getSpreadColor = (spread: string) => {
    switch (spread.toUpperCase()) {
      case "NASIONAL":
        return "text-rose bg-rose/10 border-rose/25";
      case "REGIONAL":
        return "text-amber bg-amber/10 border-amber/25";
      default:
        return "text-emerald bg-emerald/10 border-emerald/25";
    }
  };

  const getRiskFriendlyLabel = (level: string) => {
    switch (level.toUpperCase()) {
      case "CRITICAL":
        return "Sangat Bahaya";
      case "HIGH":
        return "Bahaya";
      case "MEDIUM":
        return "Waspada";
      case "LOW":
        return "Rendah";
      default:
        return level;
    }
  };

  const getTrendFriendlyLabel = (trend: string) => {
    switch (trend.toUpperCase()) {
      case "VIRAL":
        return "Ramai Dilaporkan";
      case "SPIKING":
        return "Meningkat Tajam";
      case "RISING":
        return "Naik";
      default:
        return trend;
    }
  };

  const getSpreadFriendlyLabel = (spread: string) => {
    switch (spread.toUpperCase()) {
      case "NASIONAL":
        return "Luas (Nasional)";
      case "REGIONAL":
        return "Lokal (Daerah)";
      default:
        return "Satu Kota";
    }
  };

  const signalLabel = (sig: string) => {
    const labels: Record<string, string> = {
      same_bank_account: "Rekening Bank Sama",
      same_phone: "Nomor HP Sama",
      same_domain: "Website Sama",
      behavioral_pattern: "Tanda Kalimat Rayuan",
      high_similarity: "Kemiripan Kalimat Tinggi",
      young_domain: "Website Sangat Baru (<90 hari)"
    };
    return labels[sig] || sig;
  };

  return (
    <>
      <Navbar />
      <main className="flex flex-col flex-1 min-h-screen pt-24 pb-16 px-6 relative overflow-hidden bg-background">
        {/* Decorative Ambient Orbs */}
        <div className="orb w-[500px] h-[500px] opacity-15 -left-32 top-20"
          style={{ background: "oklch(0.55 0.22 275 / 20%)" }} />
        <div className="orb w-[350px] h-[350px] opacity-10 right-0 bottom-20"
          style={{ background: "oklch(0.65 0.19 310 / 20%)" }} />

        <div className="max-w-5xl mx-auto w-full relative z-10">
          
          {/* Header */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-rose border border-rose/20 mb-4 shadow-[0_0_12px_oklch(0.60_0.22_22/10%)]">
              <span className="w-2 h-2 rounded-full bg-rose animate-ping" />
              <Radio className="w-3.5 h-3.5 text-rose" />
              RADAR ANCAMAN PENIPUAN NASIONAL
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-3 text-foreground">
              Radar Penipuan Nasional
            </h1>
            <p className="text-muted-foreground text-sm leading-relaxed max-w-xl mx-auto">
              Pantau penyebaran kelompok penipu dan peta wilayah rawan investasi bodong secara langsung berdasarkan laporan masyarakat.
            </p>
          </div>

          {/* Quick stats board */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            <div className="glass rounded-[2rem] p-6 border border-black/5 flex items-center gap-4 transition-all duration-300 hover:-translate-y-1">
              <div className="w-12 h-12 rounded-2xl bg-rose/10 text-rose flex items-center justify-center flex-shrink-0 shadow-inner">
                <Flame className="w-5.5 h-5.5 text-rose" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Kelompok Terlacak</p>
                <h3 className="text-2xl font-black text-foreground mt-0.5">{clusters.length} Kelompok</h3>
              </div>
            </div>
            <div className="glass rounded-[2rem] p-6 border border-black/5 flex items-center gap-4 transition-all duration-300 hover:-translate-y-1">
              <div className="w-12 h-12 rounded-2xl bg-indigo/10 text-indigo flex items-center justify-center flex-shrink-0 shadow-inner">
                <MapPin className="w-5.5 h-5.5 text-indigo" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Wilayah Terpantau</p>
                <h3 className="text-2xl font-black text-foreground mt-0.5">{totalMonitored} Kota</h3>
              </div>
            </div>
            <div className="glass rounded-[2rem] p-6 border border-black/5 flex items-center gap-4 transition-all duration-300 hover:-translate-y-1">
              <div className="w-12 h-12 rounded-2xl bg-emerald/10 text-emerald flex items-center justify-center flex-shrink-0 shadow-inner">
                <TrendingUp className="w-5.5 h-5.5 text-emerald" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Laporan Warga</p>
                <Link href="/submit-report" className="text-xs font-bold text-primary hover:underline flex items-center gap-1 mt-1 group">
                  Kirim Laporan Baru 
                  <ChevronRight className="w-4 h-4 text-primary group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            </div>
          </div>

          {/* Main Content & Navigation Tabs */}
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 border-b border-black/5 pb-5">
              
              {/* Apple Segmented Controls */}
              <div className="flex bg-black/3 p-1 rounded-2xl w-full md:w-auto shadow-inner border border-black/5">
                <button
                  onClick={() => setActiveTab("clusters")}
                  className={`flex-1 md:flex-none px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                    activeTab === "clusters"
                      ? "bg-white text-foreground shadow-md font-extrabold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Activity className="w-3.5 h-3.5" />
                  Kelompok Penipu
                </button>
                <button
                  onClick={() => setActiveTab("regions")}
                  className={`flex-1 md:flex-none px-6 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
                    activeTab === "regions"
                      ? "bg-white text-foreground shadow-md font-extrabold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <MapPin className="w-3.5 h-3.5" />
                  Peta Rawan Wilayah
                </button>
              </div>

              {/* Filters for clusters */}
              {activeTab === "clusters" && (
                <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
                  
                  {/* Search box with perfect padding */}
                  <div className="relative w-full sm:w-[180px]">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
                    <input
                      type="text"
                      value={searchRegion}
                      onChange={(e) => setSearchRegion(e.target.value)}
                      placeholder="Cari kota..."
                      className="input-clean pl-9.5 pr-4 w-full h-11 text-xs text-foreground placeholder:text-muted-foreground/35 font-medium"
                    />
                  </div>

                  {/* Filter Pills with elegant layout */}
                  <div className="flex items-center gap-1 bg-black/3 rounded-2xl p-1 w-full sm:w-auto overflow-x-auto border border-black/5 shadow-inner">
                    {riskLevels.map((lvl) => (
                      <button
                        key={lvl}
                        onClick={() => setRiskFilter(lvl)}
                        className={`flex-shrink-0 px-3.5 py-1.5 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all ${
                          riskFilter === lvl
                            ? "bg-white text-foreground shadow-sm font-extrabold"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {lvl === "ALL" ? "Semua" : lvl}
                      </button>
                    ))}
                  </div>

                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-3 p-4 rounded-3xl bg-rose/5 border border-rose/10 text-sm text-rose">
                <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose" />
                <span>{error}</span>
              </div>
            )}

            {/* Content Display Panels */}
            {loading ? (
              /* Apple style premium scanning pulse */
              <div className="flex flex-col items-center justify-center py-24 gap-6">
                <div className="relative flex items-center justify-center w-36 h-36">
                  <div className="absolute inset-0 rounded-full border border-primary/20 animate-ping opacity-60" style={{ animationDuration: "2.5s" }} />
                  <div className="absolute inset-4 rounded-full border border-primary/30 animate-ping opacity-45" style={{ animationDuration: "2.5s", animationDelay: "0.6s" }} />
                  <div className="absolute inset-8 rounded-full border border-primary/40 animate-ping opacity-30" style={{ animationDuration: "2.5s", animationDelay: "1.2s" }} />
                  <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center border border-primary/25 shadow-inner">
                    <Radio className="w-8 h-8 text-primary animate-pulse" />
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <p className="text-sm font-bold text-foreground">Sedang Memeriksa Radar Penipuan...</p>
                  <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">Mengumpulkan laporan dari warga di seluruh Indonesia untuk menemukan kelompok penipu.</p>
                </div>
              </div>
            ) : activeTab === "clusters" ? (
              <div className="space-y-4">
                <AnimatePresence mode="popLayout">
                  {clusters.length > 0 ? (
                    clusters.map((cluster) => (
                      <motion.div
                        key={cluster.id}
                        layout
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.98 }}
                        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                        className="glass rounded-[2rem] p-6 border border-black/5 shadow-md flex flex-col lg:flex-row lg:items-stretch justify-between gap-6 hover:shadow-xl hover:border-black/10 transition-all duration-300 group"
                      >
                        <div className="space-y-4 flex-1 flex flex-col justify-between">
                          
                          {/* Heading badges */}
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`px-3 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider border flex items-center gap-1 ${getRiskColor(cluster.risk_level)}`}>
                              <ShieldAlert className="w-3.5 h-3.5" />
                              Bahaya: {getRiskFriendlyLabel(cluster.risk_level)}
                            </span>
                            <span className={`px-3 py-1 rounded-full text-[9px] font-bold uppercase tracking-wider border flex items-center gap-1 ${getTrendColor(cluster.regional_status)}`}>
                              <Flame className="w-3.5 h-3.5" />
                              Tren: {getTrendFriendlyLabel(cluster.regional_status)}
                            </span>
                            <span className="px-3 py-1 rounded-full text-[9px] font-bold bg-primary/5 text-primary border border-primary/10">
                              Tingkat Kemiripan: {cluster.similarity_score}%
                            </span>
                          </div>

                          {/* Cluster Details */}
                          <div>
                            <h3 className="text-xl font-extrabold text-foreground group-hover:text-primary transition-colors">{cluster.group_name}</h3>
                            <p className="text-xs text-muted-foreground mt-1">
                              Modus Utama: <span className="font-bold text-foreground/80">{cluster.category}</span>
                            </p>
                          </div>

                          {/* Beautiful Meta Grid for Indicators */}
                          {(cluster.domains.length > 0 || cluster.bank_accounts.length > 0 || cluster.phone_numbers.length > 0) && (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-black/2 p-4 rounded-2xl border border-black/5 mt-1 shadow-inner">
                              
                              {/* Domains */}
                              <div className="space-y-1.5">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                                  <Globe className="w-3.5 h-3.5 text-primary" /> Website Penipu
                                </p>
                                <div className="flex flex-wrap gap-1">
                                  {cluster.domains.length > 0 ? (
                                    cluster.domains.map((dom) => (
                                      <span key={dom} className="px-2 py-0.5 rounded bg-white text-[10px] font-mono text-foreground border border-black/5 shadow-xs">{dom}</span>
                                    ))
                                  ) : (
                                    <span className="text-[10px] text-muted-foreground/60 italic">Tidak terdeteksi</span>
                                  )}
                                </div>
                              </div>
                              
                              {/* Bank accounts */}
                              <div className="space-y-1.5">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                                  <CreditCard className="w-3.5 h-3.5 text-primary" /> Rekening Terkait
                                </p>
                                <div className="flex flex-wrap gap-1">
                                  {cluster.bank_accounts.length > 0 ? (
                                    cluster.bank_accounts.map((bank) => (
                                      <span key={bank} className="px-2 py-0.5 rounded bg-white text-[10px] font-mono text-foreground border border-black/5 shadow-xs">{bank}</span>
                                    ))
                                  ) : (
                                    <span className="text-[10px] text-muted-foreground/60 italic">Tidak terdeteksi</span>
                                  )}
                                </div>
                              </div>

                              {/* Phone Numbers */}
                              <div className="space-y-1.5">
                                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                                  <Phone className="w-3.5 h-3.5 text-primary" /> Kontak Terkait
                                </p>
                                <div className="flex flex-wrap gap-1">
                                  {cluster.phone_numbers.length > 0 ? (
                                    cluster.phone_numbers.map((phone) => (
                                      <span key={phone} className="px-2 py-0.5 rounded bg-white text-[10px] font-mono text-foreground border border-black/5 shadow-xs">{phone}</span>
                                    ))
                                  ) : (
                                    <span className="text-[10px] text-muted-foreground/60 italic">Tidak terdeteksi</span>
                                  )}
                                </div>
                              </div>

                            </div>
                          )}

                          {/* Matched Signal List */}
                          <div className="pt-1">
                            <p className="text-[9px] font-extrabold text-muted-foreground uppercase tracking-wider mb-2">Tanda Kemiripan Modus</p>
                            <div className="flex flex-wrap gap-1.5">
                              {cluster.matched_signals.map((sig) => (
                                <span key={sig} className="px-2.5 py-1 rounded-xl bg-primary/5 text-primary text-[10px] font-semibold border border-primary/10 shadow-xs flex items-center gap-1">
                                  <Sparkles className="w-3 h-3 text-primary/80" />
                                  {signalLabel(sig)}
                                </span>
                              ))}
                            </div>
                          </div>

                        </div>

                        {/* Right side stats badge with Premium Glass design */}
                        <div className="flex flex-row lg:flex-col items-center justify-between lg:justify-center p-5 bg-primary/[0.03] rounded-2xl border border-primary/5 lg:min-w-[150px] text-center gap-2 mt-4 lg:mt-0 relative overflow-hidden">
                          <div className="absolute top-0 right-0 w-16 h-16 rounded-full bg-primary/5 blur-xl pointer-events-none" />
                          <div className="z-10">
                            <span className="text-4xl font-black text-primary leading-none tracking-tight block">{cluster.total_reports}</span>
                            <span className="text-[9px] font-bold text-muted-foreground uppercase block mt-1 tracking-wider">Laporan Warga</span>
                          </div>
                          <div className="w-full border-t border-primary/5 hidden lg:block my-1.5" />
                          <div className="text-[9px] text-muted-foreground flex items-center gap-1 z-10 font-medium">
                            <Calendar className="w-3 h-3 text-muted-foreground/60" />
                            <span>Masih Aktif</span>
                          </div>
                        </div>

                      </motion.div>
                    ))
                  ) : (
                    <div className="glass rounded-[2rem] p-12 text-center border border-black/5 shadow-md space-y-4">
                      <div className="w-16 h-16 bg-black/3 rounded-full flex items-center justify-center mx-auto">
                        <Radio className="w-8 h-8 text-muted-foreground/40" />
                      </div>
                      <div className="space-y-1">
                        <h3 className="text-lg font-bold text-foreground">Tidak Ada Kelompok Penipu</h3>
                        <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                          Belum ada kelompok penipu yang terdeteksi untuk pencarian ini. Silakan cari kota lain atau atur ulang pilihan.
                        </p>
                      </div>
                    </div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              /* Regions hotspots Telemetry Dashboard */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AnimatePresence mode="popLayout">
                  {regions.length > 0 ? (
                    regions.map((reg) => (
                      <motion.div
                        key={reg.region}
                        layout
                        initial={{ opacity: 0, scale: 0.97 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.97 }}
                        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                        className="glass rounded-[2rem] p-6 border border-black/5 shadow-sm flex flex-col justify-between gap-5 hover:shadow-md hover:border-black/10 transition-all duration-300"
                      >
                        <div className="space-y-3.5">
                          
                          {/* Province + City */}
                          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-bold uppercase tracking-wider">
                            <div className="flex items-center gap-1.5">
                              <MapPin className="w-3.5 h-3.5 text-primary" />
                              <span>{reg.region}</span>
                              {reg.province && (
                                <>
                                  <span className="text-muted-foreground/30">·</span>
                                  <span>{reg.province}</span>
                                </>
                              )}
                            </div>
                            <span className={`px-2.5 py-0.5 rounded-lg text-[9px] font-bold border ${getTrendColor(reg.status)}`}>
                              {getTrendFriendlyLabel(reg.status)}
                            </span>
                          </div>

                          <div>
                            <h4 className="text-lg font-extrabold text-foreground">{reg.region}</h4>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Dominasi Pola: <span className="font-bold text-foreground/80">{reg.dominant_scam || "Investasi Bodong"}</span>
                            </p>
                          </div>

                          {/* Growth telemetry progress bar */}
                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-[10px] font-bold text-muted-foreground tracking-wider uppercase">
                              <span>Kenaikan Laporan</span>
                              <span className={reg.growth_percentage > 0 ? "text-rose" : "text-emerald"}>
                                {reg.growth_percentage > 0 ? "+" : ""}{reg.growth_percentage.toFixed(1)}% Kenaikan Laporan
                              </span>
                            </div>
                            <div className="h-2 w-full bg-black/3 rounded-full overflow-hidden border border-black/5">
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(Math.max(reg.growth_percentage, 5), 100)}%` }}
                                transition={{ duration: 1, ease: "easeOut" }}
                                className={`h-full rounded-full ${reg.growth_percentage > 100 ? "bg-rose" : reg.growth_percentage > 50 ? "bg-amber" : "bg-primary"}`} 
                              />
                            </div>
                          </div>

                          {/* Weekly report analysis stats with styled telemetry */}
                          <div className="grid grid-cols-3 gap-2 border-t border-black/5 pt-4 text-center mt-2">
                            <div className="space-y-0.5">
                              <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">Laporan Warga</p>
                              <p className="font-black text-foreground text-sm">{reg.total_reports}</p>
                            </div>
                            <div className="space-y-0.5 border-l border-black/5">
                              <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">Luas Sebaran</p>
                              <p className={`font-bold text-xs uppercase tracking-wider block mt-0.5 px-2 py-0.5 rounded-full inline-block mx-auto ${getSpreadColor(reg.spread_level)}`}>
                                {getSpreadFriendlyLabel(reg.spread_level)}
                              </p>
                            </div>
                            <div className="space-y-0.5 border-l border-black/5">
                              <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">Kondisi Tren</p>
                              <p className="font-extrabold text-foreground text-sm">{getTrendFriendlyLabel(reg.status)}</p>
                            </div>
                          </div>

                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="col-span-2 glass rounded-[2rem] p-12 text-center border border-black/5 shadow-md space-y-4">
                      <div className="w-16 h-16 bg-black/3 rounded-full flex items-center justify-center mx-auto">
                        <MapPin className="w-8 h-8 text-muted-foreground/40" />
                      </div>
                      <div className="space-y-1">
                        <h3 className="text-lg font-bold text-foreground">Wilayah Masih Aman</h3>
                        <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                          Belum ada wilayah yang terdeteksi rawan penipuan. Setiap laporan warga yang masuk akan dipetakan otomatis di sini.
                        </p>
                      </div>
                    </div>
                  )}
                </AnimatePresence>
              </div>
            )}

            {/* Information panel */}
            <div className="p-6 rounded-[2rem] bg-primary/[0.02] border border-primary/10 flex items-start gap-4 max-w-3xl mx-auto leading-relaxed mt-4 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 rounded-full bg-primary/5 blur-2xl pointer-events-none" />
              <Info className="w-5.5 h-5.5 text-primary flex-shrink-0 mt-0.5" />
              <div className="space-y-1.5 z-10">
                <h4 className="text-xs font-black text-primary uppercase tracking-wider">Bagaimana Sistem Radar Bekerja?</h4>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Setiap laporan penipuan yang Anda kirimkan lewat fitur <strong>Laporkan Scam</strong> akan otomatis dianalisis oleh sistem pencocokan kami. Sistem akan langsung membandingkan kesamaan nomor rekening bank, nomor HP, atau alamat website penipu yang dilaporkan warga lainnya. Dengan cara ini, kita bisa saling menjaga dan memperingatkan sesama agar terhindar dari modus penipuan yang sama!
                </p>
              </div>
            </div>

          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
