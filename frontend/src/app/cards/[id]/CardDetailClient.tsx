"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCard, fetchCardPromotions } from "@/lib/api";
import type { CreditCardDetail, Promotion } from "@/lib/types";

export default function CardDetailClient({ id }: { id: string }) {
  const cardId = Number(id);

  const [card, setCard] = useState<CreditCardDetail | null>(null);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cardId || isNaN(cardId)) return;

    setLoading(true);
    setError(null);

    Promise.all([fetchCard(cardId), fetchCardPromotions(cardId)])
      .then(([cardData, promoData]) => {
        setCard(cardData);
        setPromotions(promoData);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "載入失敗");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [cardId]);

  if (!cardId || isNaN(cardId)) {
    return <div className="text-center py-12 text-red-600" role="alert">無效的信用卡 ID</div>;
  }

  if (loading) {
    return <div className="text-center py-12 text-gray-500" role="status" aria-live="polite">載入中...</div>;
  }

  if (error) {
    return <div className="text-center py-12 text-red-600" role="alert" aria-live="assertive">{error}</div>;
  }

  if (!card) {
    return <div className="text-center py-12 text-gray-500">找不到此信用卡</div>;
  }

  return (
    <div>
      <Link
        href="/cards"
        className="text-blue-600 hover:text-blue-800 text-sm mb-4 inline-block"
      >
        &larr; 返回列表
      </Link>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 lg:p-8">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Card image */}
            <div className="flex-shrink-0 flex justify-center">
              {card.image_url ? (
                <img
                  src={card.image_url}
                  alt={card.name}
                  className="h-48 lg:h-56 object-contain rounded"
                  onError={(e) => {
                    const target = e.currentTarget;
                    target.style.display = "none";
                    target.parentElement!.innerHTML =
                      `<div class="h-48 lg:h-56 w-64 flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 rounded text-gray-400 text-base px-4 text-center">${card.name}</div>`;
                  }}
                />
              ) : (
                <div className="h-48 lg:h-56 w-64 flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200 rounded text-gray-400 text-base px-4 text-center">
                  {card.name}
                </div>
              )}
            </div>

            {/* Card info */}
            <div className="flex-1 space-y-4">
              <div>
                <p className="text-sm text-gray-500">{card.bank.name}</p>
                <h1 className="text-2xl font-bold text-gray-900">{card.name}</h1>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                {card.card_type && (
                  <div>
                    <span className="text-gray-500">卡片類型</span>
                    <p className="font-medium text-gray-900">{card.card_type}</p>
                  </div>
                )}
                <div>
                  <span className="text-gray-500">年費</span>
                  <p className="font-medium text-gray-900">
                    {card.annual_fee === 0 || card.annual_fee === null
                      ? "免年費"
                      : `$${card.annual_fee.toLocaleString()}`}
                  </p>
                </div>
                {card.annual_fee_waiver && (
                  <div>
                    <span className="text-gray-500">年費減免</span>
                    <p className="font-medium text-gray-900">
                      {card.annual_fee_waiver}
                    </p>
                  </div>
                )}
                {card.base_reward_rate !== null && (
                  <div>
                    <span className="text-gray-500">基本回饋</span>
                    <p className="font-medium text-gray-900">
                      {card.base_reward_rate}%
                    </p>
                  </div>
                )}
                {card.min_income !== null && (
                  <div>
                    <span className="text-gray-500">最低年收入</span>
                    <p className="font-medium text-gray-900">
                      ${card.min_income.toLocaleString()}
                    </p>
                  </div>
                )}
              </div>

              {card.apply_url && (
                <a
                  href={card.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="立即申辦 (在新視窗開啟)"
                  className="inline-block bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors"
                >
                  立即申辦
                </a>
              )}
            </div>
          </div>

          {/* Features section */}
          {card.features && Object.keys(card.features).length > 0 && (
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">
                卡片特色
              </h2>
              <div className="flex flex-wrap gap-2">
                {Object.entries(card.features).map(([key, value]) => {
                  const label =
                    typeof value === "string"
                      ? `${key}: ${value}`
                      : Array.isArray(value)
                        ? `${key}: ${value.join(", ")}`
                        : String(key);
                  return (
                    <span
                      key={key}
                      className="bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-sm"
                    >
                      {label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Promotions section */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          優惠活動 ({promotions.length})
        </h2>

        {promotions.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
            目前沒有進行中的優惠活動
          </div>
        ) : (
          <div className="space-y-4">
            {promotions.map((promo) => (
              <div
                key={promo.id}
                className="bg-white rounded-lg shadow p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">
                      {promo.title}
                    </h3>
                    {promo.description && (
                      <p className="text-sm text-gray-600 mt-1">
                        {promo.description}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-2 text-xs">
                      {promo.category && (
                        <span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                          {promo.category}
                        </span>
                      )}
                      {promo.reward_type && (
                        <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded">
                          {promo.reward_type}
                        </span>
                      )}
                      {promo.reward_rate !== null && (
                        <span className="bg-green-100 text-green-800 px-2 py-0.5 rounded">
                          回饋 {promo.reward_rate}%
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right text-xs text-gray-400 flex-shrink-0">
                    {promo.start_date && <div>{promo.start_date}</div>}
                    {promo.end_date && <div>~ {promo.end_date}</div>}
                  </div>
                </div>
                {promo.terms && (
                  <p className="text-xs text-gray-400 mt-2 border-t border-gray-100 pt-2">
                    {promo.terms}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
