"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchBanks, fetchCards } from "@/lib/api";

export default function Home() {
  const [bankCount, setBankCount] = useState<number | null>(null);
  const [cardCount, setCardCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const [banks, cards] = await Promise.all([
          fetchBanks(),
          fetchCards({ page: 1, size: 1 }),
        ]);
        setBankCount(banks.length);
        setCardCount(cards.total);
      } catch {
        // Stats are non-critical; silently fail
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="py-8">
      {/* Hero */}
      <section className="text-center mb-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[#134E4A] mb-6 leading-tight">
          找到最適合你的信用卡
        </h1>
        <p className="text-lg text-[#475569] max-w-2xl mx-auto mb-8 leading-relaxed">
          匯集台灣各大銀行信用卡資訊與最新優惠活動，
          透過個人化推薦引擎，幫助您找到最適合的信用卡。
        </p>
        <Link
          href="/recommend"
          className="inline-flex items-center px-8 py-4 bg-[#0369A1] hover:bg-[#0284C7] text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#0369A1]/50 focus:ring-offset-2"
        >
          開始個人化推薦
          <svg
            className="w-5 h-5 ml-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Link>
      </section>

      {/* Stats */}
      {loading ? (
        <section className="flex justify-center gap-6 mb-16">
          <div className="bg-white rounded-2xl shadow-sm border border-[#E2E8F0] px-10 py-8 text-center animate-pulse">
            <div className="h-10 w-16 bg-gray-200 rounded mx-auto mb-2"></div>
            <div className="h-4 w-20 bg-gray-200 rounded mx-auto"></div>
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-[#E2E8F0] px-10 py-8 text-center animate-pulse">
            <div className="h-10 w-16 bg-gray-200 rounded mx-auto mb-2"></div>
            <div className="h-4 w-20 bg-gray-200 rounded mx-auto"></div>
          </div>
        </section>
      ) : (
        bankCount !== null &&
        cardCount !== null && (
          <section className="flex justify-center gap-6 mb-16">
            <div className="bg-white rounded-2xl shadow-sm border border-[#99F6E4] px-10 py-8 text-center">
              <div className="text-4xl font-bold text-[#0F766E]">
                {bankCount}
              </div>
              <div className="text-sm text-[#64748B] mt-2 font-medium">
                合作銀行
              </div>
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-[#99F6E4] px-10 py-8 text-center">
              <div className="text-4xl font-bold text-[#0F766E]">
                {cardCount}
              </div>
              <div className="text-sm text-[#64748B] mt-2 font-medium">
                信用卡
              </div>
            </div>
          </section>
        )
      )}

      {/* Quick links */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
        <Link
          href="/cards"
          className="group block bg-white rounded-2xl shadow-sm border border-[#E2E8F0] p-8 hover:shadow-md hover:border-[#99F6E4] transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#0F766E]/50"
        >
          <div className="w-12 h-12 bg-[#F0FDFA] rounded-xl flex items-center justify-center mb-4 group-hover:bg-[#99F6E4]/30 transition-colors duration-200">
            <svg
              className="w-6 h-6 text-[#0F766E]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-[#134E4A] mb-2 group-hover:text-[#0F766E] transition-colors duration-200">
            瀏覽信用卡
          </h2>
          <p className="text-[#64748B] text-sm leading-relaxed">
            依銀行、卡片類型篩選，瀏覽完整信用卡列表與優惠活動。
          </p>
        </Link>
        <Link
          href="/recommend"
          className="group block bg-white rounded-2xl shadow-sm border border-[#E2E8F0] p-8 hover:shadow-md hover:border-[#99F6E4] transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#0F766E]/50"
        >
          <div className="w-12 h-12 bg-[#F0FDFA] rounded-xl flex items-center justify-center mb-4 group-hover:bg-[#99F6E4]/30 transition-colors duration-200">
            <svg
              className="w-6 h-6 text-[#0F766E]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-[#134E4A] mb-2 group-hover:text-[#0F766E] transition-colors duration-200">
            個人化推薦
          </h2>
          <p className="text-[#64748B] text-sm leading-relaxed">
            輸入您的消費習慣與偏好，取得最適合的信用卡推薦。
          </p>
        </Link>
      </section>

      {/* Features */}
      <section className="mt-20">
        <h2 className="text-2xl font-semibold text-[#134E4A] text-center mb-10">
          為什麼選擇我們
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          <div className="text-center p-6">
            <div className="w-14 h-14 bg-[#F0FDFA] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-7 h-7 text-[#0F766E]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-[#134E4A] mb-2">即時更新</h3>
            <p className="text-sm text-[#64748B]">
              每日自動抓取最新優惠資訊
            </p>
          </div>
          <div className="text-center p-6">
            <div className="w-14 h-14 bg-[#F0FDFA] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-7 h-7 text-[#0F766E]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-[#134E4A] mb-2">智能評分</h3>
            <p className="text-sm text-[#64748B]">
              根據您的消費習慣計算最佳回饋
            </p>
          </div>
          <div className="text-center p-6">
            <div className="w-14 h-14 bg-[#F0FDFA] rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-7 h-7 text-[#0F766E]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
            <h3 className="font-semibold text-[#134E4A] mb-2">安全可靠</h3>
            <p className="text-sm text-[#64748B]">
              不儲存任何個人敏感資料
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
