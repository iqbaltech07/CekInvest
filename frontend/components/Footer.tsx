import Link from "next/link";
import { Shield } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative border-t border-black/5 mt-auto">
      {/* Top glow separator */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[400px] h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent" />

      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4 group w-fit">
              <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-lg">
                <Shield className="w-4.5 h-4.5 text-primary-foreground" strokeWidth={2.5} />
              </div>
              <span className="font-semibold text-[17px] tracking-tight">
                <span className="text-gradient">Cek</span>
                <span className="text-foreground/90">Invest</span>
              </span>
            </Link>
            <p className="text-[14px] text-muted-foreground leading-relaxed max-w-sm">
              AI-powered financial scam intelligence untuk masyarakat digital Indonesia.
              Melindungi investasi, satu analisis dalam satu waktu.
            </p>
          </div>

          {/* Links */}
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.15em] text-muted-foreground/60 mb-5">
              Platform
            </p>
            <div className="flex flex-col gap-3">
              {["Analisis Sekarang", "Cara Kerja", "Fitur", "Statistik"].map((item) => (
                <Link
                  key={item}
                  href="#"
                  className="text-[14px] text-muted-foreground hover:text-foreground transition-colors duration-200"
                >
                  {item}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.15em] text-muted-foreground/60 mb-5">
              Info
            </p>
            <div className="flex flex-col gap-3">
              {["Tentang Kami", "Privacy Policy", "Terms of Use", "Kontak"].map((item) => (
                <Link
                  key={item}
                  href="#"
                  className="text-[14px] text-muted-foreground hover:text-foreground transition-colors duration-200"
                >
                  {item}
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-10 border-t border-black/5">
          <p className="text-[13px] text-muted-foreground/60">
            © 2026 CekInvest. Dibuat dengan ❤️ untuk Indonesia.
          </p>
          <p className="text-[13px] text-muted-foreground/60">
            CekInvest tidak memberikan saran investasi finansial.
            Semua analisis bersifat indikatif.
          </p>
        </div>
      </div>
    </footer>
  );
}
