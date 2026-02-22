"use client";

import { useEffect, useState } from "react";
import PriceChart from "./PriceChart";

export default function TrackingList() {
  const [products, setProducts] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [histories, setHistories] = useState<Record<number, any[]>>({});

  useEffect(() => {
    fetch("/api/products")
      .then((r) => r.json())
      .then((data) => setProducts(data.items || []));
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

  if (products.length === 0) {
    return (
      <p className="text-gray-400 text-center py-8">尚未追蹤任何商品</p>
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
