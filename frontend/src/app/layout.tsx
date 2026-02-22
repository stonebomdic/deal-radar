import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "台灣信用卡查詢與推薦",
  description: "瀏覽台灣各大銀行信用卡資訊、優惠活動，取得個人化推薦",
};

function Navbar() {
  return (
    <nav className="fixed top-5 left-5 right-5 z-50 glass border border-white/30 rounded-2xl shadow-[0_8px_32px_rgba(15,118,110,0.08)]">
      <div className="max-w-7xl mx-auto px-6 py-3.5">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2.5 group"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0F766E] to-[#14B8A6] flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow duration-300">
              <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="4" width="22" height="16" rx="3" />
                <line x1="1" y1="10" x2="23" y2="10" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight text-[#134E4A] group-hover:text-[#0F766E] transition-colors duration-200">
              CardPick
            </span>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1.5">
            <Link
              href="/"
              className="px-4 py-2 text-[#475569] hover:text-[#0F766E] hover:bg-[#F0FDFA] rounded-lg transition-all duration-200 text-sm font-medium"
            >
              首頁
            </Link>
            <Link
              href="/cards"
              className="px-4 py-2 text-[#475569] hover:text-[#0F766E] hover:bg-[#F0FDFA] rounded-lg transition-all duration-200 text-sm font-medium"
            >
              信用卡
            </Link>
            <Link
              href="/track"
              className="px-4 py-2 text-[#475569] hover:text-[#0F766E] hover:bg-[#F0FDFA] rounded-lg transition-all duration-200 text-sm font-medium"
            >
              商品追蹤
            </Link>
            <Link
              href="/deals"
              className="px-4 py-2 text-[#475569] hover:text-[#0F766E] hover:bg-[#F0FDFA] rounded-lg transition-all duration-200 text-sm font-medium"
            >
              限時瘋搶
            </Link>
            <div className="w-px h-5 bg-[#E2E8F0] mx-1.5" />
            <Link
              href="/recommend"
              className="px-5 py-2.5 bg-gradient-to-r from-[#0F766E] to-[#0D9488] hover:from-[#0D9488] hover:to-[#14B8A6] text-white text-sm font-semibold rounded-xl transition-all duration-300 shadow-md hover:shadow-lg hover:shadow-[#0F766E]/20 cursor-pointer"
            >
              開始推薦
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW">
      <body className="bg-[#F0FDFA] min-h-screen grain">
        <Navbar />
        <main className="pt-24 pb-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
        <footer className="relative border-t border-[#99F6E4]/40">
          <div className="absolute inset-0 bg-gradient-to-t from-white/80 to-[#F0FDFA]/50" />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#0F766E] to-[#14B8A6] flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="1" y="4" width="22" height="16" rx="3" />
                    <line x1="1" y1="10" x2="23" y2="10" />
                  </svg>
                </div>
                <span className="text-[#134E4A] font-semibold tracking-tight">CardPick</span>
              </div>
              <div className="text-[#64748B] text-sm">
                台灣信用卡智能推薦平台
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
