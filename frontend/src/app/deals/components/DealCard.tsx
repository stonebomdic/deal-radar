"use client";

import { useState } from "react";

interface Deal {
  id: number;
  platform: string;
  product_name: string;
  product_url: string;
  sale_price: number;
  original_price?: number;
  discount_rate?: number;
  best_card?: { name: string; reward_amount: number; best_rate: number };
}

export default function DealCard({ deal }: { deal: Deal }) {
  const [showDetails, setShowDetails] = useState(false);

  const discountPct = deal.discount_rate
    ? Math.round(deal.discount_rate * 100)
    : null;

  return (
    <div className="rounded-xl border bg-white/60 backdrop-blur overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 flex-1 mr-2">
            {deal.product_name}
          </h3>
          {discountPct !== null && (
            <span className="text-xs font-bold text-red-500 bg-red-50 px-2 py-0.5 rounded-full shrink-0">
              {discountPct}折
            </span>
          )}
        </div>

        <div className="flex items-baseline gap-2 mb-3">
          <span className="text-xl font-bold text-blue-700">
            ${deal.sale_price.toLocaleString()}
          </span>
          {deal.original_price && (
            <span className="text-sm text-gray-400 line-through">
              ${deal.original_price.toLocaleString()}
            </span>
          )}
        </div>

        {deal.best_card && (
          <div className="bg-green-50 rounded-lg px-3 py-2 mb-3">
            <p className="text-xs text-green-700 flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z" />
              </svg>
              {deal.best_card.name}：回饋 {deal.best_card.best_rate}%
              = 省 <strong>${deal.best_card.reward_amount.toFixed(0)}</strong>
            </p>
          </div>
        )}

        <div className="flex justify-between items-center">
          <a
            href={deal.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            前往購買 →
          </a>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer"
          >
            {showDetails ? "收起" : "查看更多"}
          </button>
        </div>
      </div>
    </div>
  );
}
