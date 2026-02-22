"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface HistoryPoint {
  price: number;
  snapshot_at: string;
}

export default function PriceChart({ data }: { data: HistoryPoint[] }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400 text-sm">尚無價格記錄</p>;
  }

  const chartData = data.map((d) => ({
    date: new Date(d.snapshot_at).toLocaleDateString("zh-TW", {
      month: "short",
      day: "numeric",
    }),
    price: d.price,
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => `$${v.toLocaleString()}`}
          width={70}
        />
        <Tooltip formatter={(v: number | undefined) => [`$${(v ?? 0).toLocaleString()}`, "價格"]} />
        <Line
          type="monotone"
          dataKey="price"
          stroke="#3B82F6"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
