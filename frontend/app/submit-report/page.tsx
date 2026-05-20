"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import {
  ShieldAlert, Sparkles, MapPin, Phone, Globe, CreditCard,
  CheckCircle2, ArrowLeft, Send, AlertTriangle
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { submitReport } from "@/lib/api";

type InputType = "CHAT" | "SCREENSHOT" | "URL";

export default function SubmitReportPage() {
  const [inputType, setInputType] = useState<InputType>("CHAT");
  const [rawInput, setRawInput] = useState("");
  const [scamCategory, setScamCategory] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customCategory, setCustomCategory] = useState("");
  const [bankName, setBankName] = useState("");
  const [bankAccount, setBankAccount] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [domain, setDomain] = useState("");
  const [city, setCity] = useState("");
  const [province, setProvince] = useState("");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const categories = [
    "Robot Trading Scam",
    "Crypto Scam / Ponzi",
    "Phishing / Link Palsu",
    "Peluang Kerja Palsu / WFH",
    "Investasi Saham Bodong",
    "Arisan / Titip Dana",
    "Lainnya"
  ];

  const validate = () => {
    if (rawInput.trim().length < 10) {
      setError("Isi laporan (teks penawaran/kronologi) harus minimal 10 karakter.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setError("");
    setLoading(true);

    try {
      await submitReport({
        inputType,
        rawInput,
        isScam: true, // Community submits are treated as scams/suspicious
        notes: notes || undefined,
        scamCategory: scamCategory || undefined,
        bankName: bankName || undefined,
        bankAccount: bankAccount || undefined,
        phoneNumber: phoneNumber || undefined,
        domain: domain || undefined,
        city: city || undefined,
        province: province || undefined,
      });

      setSuccess(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError((err as Error).message || "Gagal mengirimkan laporan. Coba lagi nanti.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="flex flex-col flex-1 min-h-screen pt-24 pb-16 px-6 relative overflow-hidden bg-background">
        {/* Decorative Orbs */}
        <div className="orb w-[500px] h-[500px] opacity-15 -left-32 top-20"
          style={{ background: "oklch(0.55 0.22 275 / 20%)" }} />
        <div className="orb w-[350px] h-[350px] opacity-10 right-0 bottom-20"
          style={{ background: "oklch(0.65 0.19 310 / 20%)" }} />

        <div className="max-w-2xl mx-auto w-full relative z-10">
          {/* Back button */}
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 mb-8 font-medium group">
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
            Kembali ke Beranda
          </Link>

          <AnimatePresence mode="wait">
            {!success ? (
              <motion.div
                key="form"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4 }}
              >
                {/* Header */}
                <div className="mb-8">
                  <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-rose border border-rose/20 mb-4">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose" />
                    KONTRIBUSI INTELIJEN KOMUNITAS
                  </div>
                  <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2 text-foreground">
                    Laporkan Kasus Scam
                  </h1>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    Bantu lindungi sesama. Laporan Anda dianonimkan dan digunakan oleh mesin <strong>Clustering Engine</strong> untuk memetakan penipuan aktif secara nasional.
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="w-full glass rounded-3xl p-6 md:p-8 border border-black/5 shadow-xl space-y-6">
                  
                  {/* Tipe Input */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Tipe Laporan</label>
                    <div className="grid grid-cols-2 gap-2 bg-black/3 p-1 rounded-2xl">
                      {(["CHAT", "URL"] as InputType[]).map((type) => (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setInputType(type)}
                          className={`py-2 rounded-xl text-xs font-semibold transition-all ${
                            inputType === type
                              ? "bg-primary text-primary-foreground shadow-sm"
                              : "text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          {type === "CHAT" ? "Chat/Teks" : "Situs/Link"}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Isi Laporan Utama */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                      {inputType === "CHAT" ? "Isi Percakapan / Modus Penawaran" : "Link Website / Domain"} <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      required
                      value={rawInput}
                      onChange={(e) => setRawInput(e.target.value)}
                      placeholder={
                        inputType === "CHAT"
                          ? 'Salin percakapan penipu di sini...\nContoh: "Kak, klik link ini untuk cairkan bonus 50% dari investasi Robot Trading. Kuota tinggal 5 menit!"'
                          : "Masukkan link situs penipu...\nContoh: https://cuanrobot-vip.xyz/login"
                      }
                      className="input-clean w-full min-h-36 p-4 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/45 font-mono resize-none"
                    />
                  </div>

                   {/* Kategori Modus */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Kategori Modus Penipuan</label>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {categories.map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => {
                            if (cat === "Lainnya") {
                              setShowCustomInput(true);
                              setScamCategory(customCategory || "Lainnya");
                            } else {
                              setShowCustomInput(false);
                              setScamCategory(cat === scamCategory ? "" : cat);
                            }
                          }}
                          className={`py-2 px-3 rounded-xl border text-[11px] font-medium text-left transition-all ${
                            (cat === "Lainnya" && showCustomInput) || (scamCategory === cat && !showCustomInput)
                              ? "bg-primary/10 border-primary text-primary"
                              : "border-black/5 hover:border-black/10 hover:bg-black/3 text-muted-foreground"
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>

                    {showCustomInput && (
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        className="mt-3"
                      >
                        <input
                          type="text"
                          required
                          value={customCategory}
                          onChange={(e) => {
                            setCustomCategory(e.target.value);
                            setScamCategory(e.target.value);
                          }}
                          placeholder="Tulis kategori penipuan Anda di sini..."
                          className="input-clean w-full h-11 px-4 text-xs text-foreground placeholder:text-muted-foreground/35"
                        />
                      </motion.div>
                    )}
                  </div>

                  <hr className="border-black/5" />

                  {/* Bukti Akun / Rekening Bank */}
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                      <CreditCard className="w-3.5 h-3.5" />
                      Rekening Bank Penipu (Opsional)
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-medium text-muted-foreground mb-1">Nama Bank</label>
                        <input
                          type="text"
                          value={bankName}
                          onChange={(e) => setBankName(e.target.value)}
                          placeholder="e.g. BCA, Mandiri, BRI"
                          className="input-clean w-full h-11 px-3.5 text-xs text-foreground placeholder:text-muted-foreground/35"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-muted-foreground mb-1">Nomor Rekening</label>
                        <input
                          type="text"
                          value={bankAccount}
                          onChange={(e) => setBankAccount(e.target.value)}
                          placeholder="e.g. 1234567890"
                          className="input-clean w-full h-11 px-3.5 text-xs text-foreground placeholder:text-muted-foreground/35"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Kontak Penipu */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                        <Phone className="w-3.5 h-3.5" />
                        Nomor HP Penipu (Opsional)
                      </h3>
                      <input
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        placeholder="e.g. 081234567890"
                        className="input-clean w-full h-11 px-3.5 text-xs text-foreground placeholder:text-muted-foreground/35"
                      />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                        <Globe className="w-3.5 h-3.5" />
                        Domain Website (Opsional)
                      </h3>
                      <input
                        type="text"
                        value={domain}
                        onChange={(e) => setDomain(e.target.value)}
                        placeholder="e.g. cuanrobot.vip"
                        className="input-clean w-full h-11 px-3.5 text-xs text-foreground placeholder:text-muted-foreground/35"
                      />
                    </div>
                  </div>

                  <hr className="border-black/5" />

                  {/* Lokasi Asal Laporan */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5" />
                      Lokasi Terjadinya Penipuan (Opsional)
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-medium text-muted-foreground mb-1">Kota / Kabupaten</label>
                        <input
                          type="text"
                          value={city}
                          onChange={(e) => setCity(e.target.value)}
                          placeholder="e.g. Bandung, Surabaya"
                          className="input-clean w-full h-11 px-3.5 text-xs text-foreground placeholder:text-muted-foreground/35"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-muted-foreground mb-1">Provinsi</label>
                        <input
                          type="text"
                          value={province}
                          onChange={(e) => setProvince(e.target.value)}
                          placeholder="e.g. Jawa Barat, Jawa Timur"
                          className="input-clean w-full h-11 px-3.5 text-xs text-foreground placeholder:text-muted-foreground/35"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Catatan Tambahan */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Catatan Tambahan (Kronologi/Detail Tambahan)</label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Tambahkan detail lain yang sekiranya dapat membantu (misal: nominal kerugian, nama komplotan, dsb)"
                      className="input-clean w-full min-h-24 p-3.5 text-xs leading-relaxed text-foreground placeholder:text-muted-foreground/35 resize-none"
                    />
                  </div>

                  {/* Error Alert */}
                  {error && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className="flex items-center gap-2 p-3.5 rounded-2xl bg-rose/5 border border-rose/10 text-xs text-rose">
                      <AlertTriangle className="w-4 h-4 text-rose" />
                      <span>{error}</span>
                    </motion.div>
                  )}

                  {/* Submit Button */}
                  <motion.button
                    type="submit"
                    disabled={loading}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    className="w-full flex items-center justify-center gap-2.5 py-4 rounded-2xl bg-primary text-primary-foreground font-semibold shadow-lg hover:shadow-[0_8px_24px_oklch(0.55_0.22_275/25%)] transition-all"
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground animate-spin" />
                        <span>Mengirim Laporan…</span>
                      </>
                    ) : (
                      <>
                        <Send className="w-4.5 h-4.5 text-primary-foreground" />
                        <span className="text-primary-foreground">Kirim Laporan Anonim</span>
                      </>
                    )}
                  </motion.button>

                </form>
              </motion.div>
            ) : (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="w-full glass rounded-3xl p-8 border border-black/5 shadow-2xl text-center space-y-6"
              >
                <div className="w-16 h-16 rounded-3xl bg-emerald/10 text-emerald flex items-center justify-center mx-auto shadow-md">
                  <CheckCircle2 className="w-8 h-8 text-emerald animate-bounce" />
                </div>
                
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold tracking-tight text-foreground">Laporan Berhasil Dikirim!</h2>
                  <p className="text-sm text-muted-foreground leading-relaxed max-w-md mx-auto">
                    Terima kasih atas kontribusi Anda. Laporan Anda telah kami terima secara <strong>anonim</strong> dan secara otomatis dimasukkan ke dalam basis data <strong>Radar Intelijen Sentra</strong> untuk dianalisis lebih lanjut.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-primary/5 border border-primary/10 text-xs text-primary max-w-md mx-auto leading-relaxed flex items-center gap-3 text-left">
                  <Sparkles className="w-5 h-5 flex-shrink-0 text-primary" />
                  <span>
                    Laporan Anda telah diproses oleh <strong>Rule-Based Clustering Engine</strong> secara instan untuk memperkuat pemetaan wilayah radar scam aktif di Indonesia.
                  </span>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
                  <Link href="/scam-radar" className="px-6 py-3 rounded-2xl bg-primary text-primary-foreground font-semibold text-sm shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all text-center font-semibold">
                    Pantau Radar Scam
                  </Link>
                  <button
                    onClick={() => {
                      setSuccess(false);
                      setRawInput("");
                      setBankName("");
                      setBankAccount("");
                      setPhoneNumber("");
                      setDomain("");
                      setCity("");
                      setProvince("");
                      setNotes("");
                      setScamCategory("");
                      setShowCustomInput(false);
                      setCustomCategory("");
                    }}
                    className="px-6 py-3 rounded-2xl glass border border-black/5 hover:bg-black/3 text-muted-foreground text-sm font-semibold transition-all"
                  >
                    Kirim Laporan Lain
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
      <Footer />
    </>
  );
}
