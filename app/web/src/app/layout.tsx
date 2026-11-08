import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Instrument_Serif } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const plexSans = IBM_Plex_Sans({ variable: "--font-plex-sans", subsets: ["latin", "vietnamese"], weight: ["400", "500", "600"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin", "vietnamese"], weight: ["400", "500", "700"] });
const instrument = Instrument_Serif({ variable: "--font-instrument", subsets: ["latin"], weight: "400", style: ["normal", "italic"] });

export const metadata: Metadata = {
  title: "Drone Pilot Trainer",
  description: "Phần mềm huấn luyện học viên lái drone: tay cầm USB, giáo trình bài tập, AI chấm điểm thao tác.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={`${plexSans.variable} ${plexMono.variable} ${instrument.variable} h-full`}>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-40 border-b border-line backdrop-blur-md" style={{ background: "rgba(13,12,10,0.82)" }}>
          <div className="max-w-[1480px] mx-auto px-6 h-14 flex items-center gap-6">
            <Link href="/" className="flex items-baseline gap-3 text-txt">
              <span className="display text-[22px] leading-none">
                Drone <i>Pilot</i> Trainer
              </span>
              <span className="eyebrow hidden md:inline">sân tập mô phỏng</span>
            </Link>
            <nav className="flex items-center gap-5 text-[12.5px] ml-4">
              <Link href="/" className="text-mut hover:text-txt">
                Giáo trình
              </Link>
              <Link href="/fly/BT01" className="text-mut hover:text-txt">
                Bay ngay
              </Link>
              <span className="text-dim" title="sắp có: chấm thi, quản lý lớp">
                Giảng viên (sắp có)
              </span>
            </nav>
            <span className="flex-1" />
            <span className="eyebrow">bản thử nghiệm · cắm tay cầm USB rồi gạt cần</span>
          </div>
        </header>
        <main className="flex-1 w-full">{children}</main>
      </body>
    </html>
  );
}
