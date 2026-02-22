import CardDetailClient from "./CardDetailClient";

export const dynamicParams = false;

export async function generateStaticParams() {
  try {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    const allIds: { id: string }[] = [];
    let page = 1;
    const size = 100;

    while (true) {
      const res = await fetch(`${apiUrl}/api/cards?page=${page}&size=${size}`);
      if (!res.ok) break;
      const data = await res.json();
      const items: { id: number }[] = data.items || [];
      allIds.push(...items.map((card) => ({ id: String(card.id) })));
      if (items.length < size) break;
      page++;
    }

    return allIds;
  } catch {
    return [];
  }
}

export default function CardDetailPage({ params }: { params: { id: string } }) {
  return <CardDetailClient id={params.id} />;
}
