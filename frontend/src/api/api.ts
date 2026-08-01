import { API_BASE } from '../config';

async function request(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

export const listPortfolios = () => request('/portfolio');
export const createPortfolio = (name: string, cash: number, description = '') =>
  request('/portfolio', { method: 'POST', body: JSON.stringify({ name, description, available_cash: cash }) });
export const deletePortfolio = (id: number) => request(`/portfolio/${id}`, { method: 'DELETE' });

export const placeOrder = (portfolioId: number, order: {
  symbol: string; side: string; quantity: number; limit_price?: number;
  target?: number; stoploss?: number;
}) => request('/order', {
  method: 'POST',
  body: JSON.stringify({ ...order, portfolio_id: portfolioId }),
});

export const cancelOrder = (id: number) => request(`/order/${id}`, { method: 'DELETE' });
export const closePosition = (portfolioId: number, id: number) =>
  request(`/portfolio/${portfolioId}/positions/${id}`, { method: 'DELETE' });
export const getHistory = (portfolioId: number) => request(`/portfolio/${portfolioId}/history`);
export const getPrices = () => request('/prices');
export const getPrice = (symbol: string) => request(`/symbol/${symbol}`);
