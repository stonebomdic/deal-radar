import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "台灣信用卡查詢與推薦",
  description: "瀏覽台灣各大銀行信用卡資訊、優惠活動，取得個人化推薦",
};

function Navbar() {
  return (
    <nav className="fixed top-4 left-4 right-4 z-50 bg-white/90 backdrop-blur-lg border border-[#99F6E4] rounded-2xl shadow-sm">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link
            href="/"
            className="text-xl font-bold text-[#0F766E] hover:text-[#0D9488] transition-colors duration-200"
          >
            信用卡推薦
          </Link>
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="text-[#475569] hover:text-[#0F766E] transition-colors duration-200 text-sm font-medium"
            >
              首頁
            </Link>
            <Link
              href="/cards"
              className="text-[#475569] hover:text-[#0F766E] transition-colors duration-200 text-sm font-medium"
            >
              信用卡
            </Link>
            <Link
              href="/recommend"
              className="px-4 py-2 bg-[#0369A1] hover:bg-[#0284C7] text-white text-sm font-medium rounded-lg transition-colors duration-200 cursor-pointer"
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
      <body className="bg-[#F0FDFA] min-h-screen">
        <Navbar />
        <main className="pt-24 pb-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
        <footer className="bg-white border-t border-[#E2E8F0]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="text-[#134E4A] font-semibold">
                台灣信用卡推薦平台
              </div>
              <div className="text-[#64748B] text-sm">
                幫助您找到最適合的信用卡
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
