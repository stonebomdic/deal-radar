"use client";

import { useEffect, useState } from "react";
import DealCard from "./components/DealCard";

export default function DealsPage() {
  const [platform, setPlatform] = useState<"pchome" | "momo">("pchome");
  const [deals, setDeals] = useState<any[]>([]);
  const [sortBy, setSortBy] = useState<"discount" | "time">("discount");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/flash-deals?platform=${platform}`)
      .then((r) => r.json())
      .then((data) => {
        const sorted = [...data];
        if (sortBy === "discount") {
          sorted.sort((a, b) => (a.discount_rate || 1) - (b.discount_rate || 1));
        }
        setDeals(sorted);
        setLoading(false);
      });
  }, [platform, sortBy]);

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">限時瘋搶</h1>
      <p className="text-gray-500 mb-6">
        即時追蹤 PChome / Momo 最夯限時特賣，並推薦最佳刷卡方式
      </p>

      <div className="flex gap-3 mb-6">
        <div className="flex rounded-xl overflow-hidden border">
          {(["pchome", "momo"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`px-5 py-2 text-sm font-medium transition-colors ${
                platform === p
                  ? "bg-blue-600 text-white"
                  : "bg-white/60 text-gray-600 hover:bg-white"
              }`}
            >
              {p === "pchome" ? "PChome 24h" : "Momo 購物"}
            </button>
          ))}
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as "discount" | "time")}
          className="px-3 py-2 rounded-xl border bg-white/60 text-sm"
        >
          <option value="discount">折扣最高</option>
          <option value="time">最新上架</option>
        </select>
      </div>

      {loading ? (
        <p className="text-center text-gray-400 py-12">載入中...</p>
      ) : deals.length === 0 ? (
        <p className="text-center text-gray-400 py-12">目前無限時瘋搶資料</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {deals.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      )}
    </main>
  );
}
