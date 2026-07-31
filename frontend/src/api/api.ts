import { API_BASE } from '../config';

async function request(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// Portfolios
export const listPortfolios = () => request("/portfolios");
export const getPortfolio = (id: number) => request(`/portfolios/${id}`);
export const createPortfolio = (name: string, cash: number, description = "") =>
  request("/portfolios", { method: "POST", body: JSON.stringify({ name, cash, description }) });
export const deletePortfolio = (id: number) =>
  request(`/portfolios/${id}`, { method: "DELETE" });

// Orders
export const placeOrder = (portfolioId: number, order: {
  symbol: string; side: string; usd?: number; qty?: number;
  limit?: number; target?: number; stoploss?: number;
}) => request(`/portfolios/${portfolioId}/orders`, {
  method: "POST", body: JSON.stringify(order),
});
export const listOrders = (portfolioId: number) =>
  request(`/portfolios/${portfolioId}/orders`);
export const cancelOrder = (orderId: number) =>
  request(`/orders/${orderId}`, { method: "DELETE" });

// Positions
export const listPositions = (portfolioId: number) =>
  request(`/portfolios/${portfolioId}/positions`);
export const closePosition = (positionId: number) =>
  request(`/positions/${positionId}`, { method: "DELETE" });

// PnL
export const getPnl = (portfolioId: number) =>
  request(`/portfolios/${portfolioId}/pnl`);
export const getHistory = (portfolioId: number) =>
  request(`/portfolios/${portfolioId}/history`);

// Prices
export const getPrices = (symbols?: string[]) =>
  request(`/prices${symbols ? `?symbols=${symbols.join(",")}` : ""}`);
export const getPrice = (symbol: string) => request(`/prices/${symbol}`);
