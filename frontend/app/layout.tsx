import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "CekInvest — AI Scam Intelligence Platform",
  description:
    "Deteksi penipuan finansial secara cepat, sederhana, dan explainable menggunakan kecerdasan buatan. Lindungi investasimu dari scam AI.",
  keywords: ["cek invest", "investasi aman", "scam detector", "AI scam", "anti penipuan", "deteksi scam"],
  openGraph: {
    title: "CekInvest — AI Scam Intelligence Platform",
    description: "Deteksi penipuan finansial dengan AI. Paste chat, upload screenshot, atau cek URL sekarang.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="id"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground overflow-x-hidden" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
