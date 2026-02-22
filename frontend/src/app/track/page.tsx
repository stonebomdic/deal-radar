"use client";

import { useState } from "react";
import SearchBar from "./components/SearchBar";
import TrackingList from "./components/TrackingList";

export default function TrackPage() {
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSearchResults = (results: any[]) => {
    setSearchResults(results);
  };

  const handleProductAdded = () => {
    setRefreshKey((k) => k + 1);
    setSearchResults([]);
  };

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">商品追蹤</h1>
      <p className="text-gray-500 mb-8">
        貼上 PChome / Momo 商品連結，或輸入關鍵字搜尋，降價立即通知
      </p>

      <SearchBar
        onResults={handleSearchResults}
        onProductAdded={handleProductAdded}
      />

      {searchResults.length > 0 && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold mb-3">搜尋結果</h2>
          <div className="space-y-2">
            {searchResults.map((result: any, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-4 rounded-xl border bg-white/60 backdrop-blur"
              >
                <div>
                  <p className="font-medium">{result.name}</p>
                  <p className="text-sm text-gray-500">{result.platform.toUpperCase()}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-lg font-bold text-green-600">
                    ${result.price?.toLocaleString()}
                  </span>
                  <button
                    onClick={async () => {
                      await fetch("/api/products", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                          platform: result.platform,
                          url: result.url,
                        }),
                      });
                      handleProductAdded();
                    }}
                    className="px-3 py-1 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                  >
                    追蹤
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold mb-3">我的追蹤清單</h2>
        <TrackingList key={refreshKey} />
      </section>
    </main>
  );
}
