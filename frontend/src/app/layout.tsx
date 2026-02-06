import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "台灣信用卡查詢與推薦",
  description: "瀏覽台灣各大銀行信用卡資訊、優惠活動，取得個人化推薦",
};

function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="text-xl font-bold text-gray-900">
            信用卡查詢
          </Link>
          <div className="flex space-x-8">
            <Link
              href="/"
              className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium"
            >
              首頁
            </Link>
            <Link
              href="/cards"
              className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium"
            >
              信用卡
            </Link>
            <Link
              href="/recommend"
              className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium"
            >
              推薦
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
      <body className="bg-gray-50 min-h-screen">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="bg-white border-t border-gray-200 mt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-gray-500 text-sm">
            台灣信用卡查詢與推薦系統
          </div>
        </footer>
      </body>
    </html>
  );
}
