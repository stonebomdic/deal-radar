"use client";

import { useEffect, useState } from "react";
import PriceChart from "./PriceChart";

export default function TrackingList() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [histories, setHistories] = useState<Record<number, any[]>>({});

  useEffect(() => {
    setLoading(true);
    fetch("/api/products")
      .then((r) => r.json())
      .then((data) => setProducts(data.items || []))
      .finally(() => setLoading(false));
  }, []);

  const loadHistory = async (id: number) => {
    if (histories[id]) return;
    const resp = await fetch(`/api/products/${id}/history`);
    const data = await resp.json();
    setHistories((prev) => ({ ...prev, [id]: data }));
  };

  const toggle = (id: number) => {
    if (expanded === id) {
      setExpanded(null);
    } else {
      setExpanded(id);
      loadHistory(id);
    }
  };

  const removeProduct = async (id: number) => {
    await fetch(`/api/products/${id}`, { method: "DELETE" });
    setProducts((prev) => prev.filter((p) => p.id !== id));
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <svg className="animate-spin w-6 h-6 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <svg xmlns="http://www.w3.org/2000/svg" className="w-10 h-10 mx-auto mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <p className="mb-1">尚未追蹤任何商品</p>
        <p className="text-sm">貼上商品連結或搜尋關鍵字開始追蹤</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {products.map((p) => (
        <div
          key={p.id}
          className="rounded-xl border bg-white/60 backdrop-blur overflow-hidden"
        >
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/80"
            onClick={() => toggle(p.id)}
          >
            <div>
              <p className="font-medium">{p.name}</p>
              <p className="text-sm text-gray-400">
                {p.platform.toUpperCase()}
                {p.target_price && ` · 目標價 $${p.target_price.toLocaleString()}`}
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                removeProduct(p.id);
              }}
              className="text-red-400 hover:text-red-600 text-sm px-2"
            >
              移除
            </button>
          </div>

          {expanded === p.id && histories[p.id] && (
            <div className="px-4 pb-4">
              <PriceChart data={histories[p.id]} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
