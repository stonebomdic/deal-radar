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
      const resp = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform, keyword: input }),
      });
      const data = await resp.json();
      onResults(data.results || []);
    }

    setLoading(false);
  };

  return (
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
        onChange={(e) => setInput(e.target.value)}
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
  );
}
