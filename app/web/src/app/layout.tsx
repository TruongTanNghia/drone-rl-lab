import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Instrument_Serif } from "next/font/google";
import Link from "next/link";
import ApiStatus from "@/components/ApiStatus";
import "./globals.css";

const plexSans = IBM_Plex_Sans({ variable: "--font-plex-sans", subsets: ["latin", "vietnamese"], weight: ["400", "500", "600"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin", "vietnamese"], weight: ["400", "500", "700"] });
const instrument = Instrument_Serif({ variable: "--font-instrument", subsets: ["latin"], weight: "400", style: ["normal", "italic"] });

export const metadata: Metadata = {
  title: "Drone RL Lab — Flight Test Range",
  description: "Huấn luyện drone bằng RL + DL theo giai đoạn. Dashboard chỉ đọc results/, mọi con số có nguồn gốc.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={`${plexSans.variable} ${plexMono.variable} ${instrument.variable} h-full`}>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-40 border-b border-line backdrop-blur-md" style={{ background: "rgba(13,12,10,0.82)" }}>
          <div className="max-w-[1480px] mx-auto px-6 h-14 flex items-center gap-6">
            <Link href="/" className="flex items-baseline gap-3 text-txt">
              <span className="display text-[22px] leading-none">
                Drone <i>RL</i> Lab
              </span>
              <span className="eyebrow hidden md:inline">Flight test range</span>
            </Link>
            <nav className="flex items-center gap-5 text-[12.5px] ml-4">
              <Link href="/" className="text-mut hover:text-txt">
                Lộ trình
              </Link>
              <Link href="/#runs" className="text-mut hover:text-txt">
                Sổ run
              </Link>
              <a href="/viewer/index.html" target="_blank" className="text-mut hover:text-txt">
                Viewer 3D ↗
              </a>
              <a href="/api/runs" target="_blank" className="text-mut hover:text-txt">
                API ↗
              </a>
            </nav>
            <span className="flex-1" />
            <ApiStatus />
          </div>
        </header>
        <main className="flex-1 w-full max-w-[1480px] mx-auto px-6 py-7">{children}</main>
        <footer className="border-t border-line">
          <div className="max-w-[1480px] mx-auto px-6 py-4 flex flex-wrap gap-x-6 gap-y-1 eyebrow" style={{ letterSpacing: "0.14em" }}>
            <span>Mọi con số đọc từ results/ · không có dữ liệu mẫu</span>
            <span>Rê chuột vào số để thấy run_id + file nguồn</span>
            <span>Seed train 0–8999 · seed đánh giá ≥ 9000</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
