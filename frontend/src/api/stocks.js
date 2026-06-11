// 종목 검색 및 가격 이력 API 클라이언트
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export async function searchStocks(q) {
    const params = new URLSearchParams({ q });
    const res = await fetch(`${API_BASE}/stocks/search?${params.toString()}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
export async function fetchStockPrices(krxCode, days = 30) {
    const params = new URLSearchParams({ days: String(days) });
    const res = await fetch(`${API_BASE}/stocks/${krxCode}/prices?${params.toString()}`);
    if (!res.ok)
        throw new Error(`API 오류: ${res.status}`);
    return res.json();
}
