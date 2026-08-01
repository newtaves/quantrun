import { useEffect, useState } from 'react';
import { WS_BASE } from '../config';
import { getPrices } from '../api/api';

export function usePricesWs() {
  const [prices, setPrices] = useState<Record<string, number>>({});
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try { const data = await getPrices(); if (active) setPrices(data); } catch { /* Retry on the next tick. */ }
    };
    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return prices;
}

export function usePortfolioWs(portfolioId: number | null) {
  const [data, setData] = useState<any>({});
  useEffect(() => {
    if (!portfolioId) return;
    const socket = new WebSocket(`${WS_BASE}/ws/portfolio/${portfolioId}/pnl`);
    socket.onmessage = event => { try { setData(JSON.parse(event.data)); } catch { /* ignore */ } };
    return () => socket.close();
  }, [portfolioId]);
  return data;
}
