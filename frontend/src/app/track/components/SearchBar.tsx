"use client";

import { useState } from "react";

interface Props {
  onResults: (results: any[]) => void;
  onProductAdded: () => void;
}

export default function SearchBar({ onResults, onProductAdded }: Props) {
  const [input, setInput] = useState("");
  const [platform, setPlatform] = useState("pchome");
  const [loading, setLoading] = useState(false);
  const [momoHint, setMomoHint] = useState(false);

  const isUrl = input.startsWith("http");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (isUrl) {
      const detectedPlatform = input.includes("pchome") ? "pchome" : "momo";
      const resp = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: detectedPlatform, url: input }),
      });
      if (resp.ok) onProductAdded();
    } else {
      if (platform === "momo") {
        const momoSearchUrl = `https://www.momoshop.com.tw/search/searchShop.jsp?keyword=${encodeURIComponent(input)}`;
        window.open(momoSearchUrl, "_blank", "noopener,noreferrer");
        setMomoHint(true);
      } else {
        const resp = await fetch("/api/products", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ platform, keyword: input }),
        });
        const data = await resp.json();
        onResults(data.results || []);
      }
    }

    setLoading(false);
  };

  return (
    <div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        {!isUrl && (
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="px-3 py-2 rounded-xl border bg-white/60 backdrop-blur"
          >
            <option value="pchome">PChome</option>
            <option value="momo">Momo</option>
          </select>
        )}
        <input
          value={input}
          onChange={(e) => { setInput(e.target.value); setMomoHint(false); }}
          placeholder="貼上商品連結或輸入關鍵字..."
          className="flex-1 px-4 py-2 rounded-xl border bg-white/60 backdrop-blur focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-5 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "搜尋中..." : isUrl ? "加入追蹤" : "搜尋"}
        </button>
      </form>
      {momoHint && (
        <div className="mt-2 flex items-start gap-2 rounded-lg bg-blue-50 border border-blue-100 px-3 py-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
          </svg>
          <p className="text-sm text-blue-700">
            已在新視窗開啟 Momo 搜尋，找到商品後請<strong>複製商品連結</strong>貼回此處追蹤
          </p>
        </div>
      )}
    </div>
  );
}
