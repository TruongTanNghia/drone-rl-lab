import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Drone RL Lab",
  description: "Huấn luyện drone bằng RL + DL theo giai đoạn — dashboard chỉ đọc results/",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="flex items-center gap-4 px-5 py-3 border-b border-line bg-panel">
          <Link href="/" className="text-txt font-semibold tracking-wide no-underline">
            Drone RL Lab
          </Link>
          <nav className="flex gap-4 text-mut text-sm">
            <Link href="/" className="text-mut hover:text-txt">
              Lộ trình G0–G5
            </Link>
            <a href="/viewer/index.html" target="_blank" className="text-mut hover:text-txt">
              Viewer độc lập
            </a>
            <a href="/api/runs" target="_blank" className="text-mut hover:text-txt">
              API
            </a>
          </nav>
          <span className="flex-1" />
          <span className="text-xs text-mut">Mọi con số đọc từ results/ · rê chuột vào số để xem run_id + file nguồn</span>
        </header>
        <main className="flex-1 px-5 py-5 max-w-[1500px] w-full mx-auto">{children}</main>
      </body>
    </html>
  );
}
