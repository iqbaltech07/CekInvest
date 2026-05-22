import Link from "next/link";
import { Shield } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative border-t border-black/5 mt-auto">
      {/* Top glow separator */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          {/* Brand */}
          <div className="col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4 group w-fit">
              <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-lg">
                <Shield className="w-4 h-4 text-primary-foreground" strokeWidth={2.5} />
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
            <p className="text-[12px] font-semibold uppercase tracking-[0.15em] text-muted-foreground/60 mb-4 sm:mb-5">
              Platform
            </p>
            <div className="flex flex-col gap-2.5 sm:gap-3">
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
            <p className="text-[12px] font-semibold uppercase tracking-[0.15em] text-muted-foreground/60 mb-4 sm:mb-5">
              Info
            </p>
            <div className="flex flex-col gap-2.5 sm:gap-3">
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

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-8 border-t border-black/5">
          <p className="text-[13px] text-muted-foreground/60 text-center sm:text-left">
            © 2026 CekInvest. Dibuat dengan ❤️ untuk Indonesia.
          </p>
          <p className="text-[13px] text-muted-foreground/60 text-center sm:text-right">
            CekInvest tidak memberikan saran investasi finansial.
            Semua analisis bersifat indikatif.
          </p>
        </div>
      </div>
    </footer>
  );
}
