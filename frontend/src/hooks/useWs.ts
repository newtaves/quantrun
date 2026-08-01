import { useCallback, useEffect, useState } from 'react';
import { API_BASE, WS_BASE } from '../config';

export function usePricesWs() {
  const [prices, setPrices] = useState<Record<string, number>>({});
  useEffect(() => {
    let active = true;
    let retry: number | undefined;
    const connect = () => {
      if (!active) return;
      const socket = new WebSocket(`${WS_BASE}/ws/prices`);
      socket.onmessage = event => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'prices' && data.prices) setPrices(previous => ({ ...previous, ...data.prices }));
        } catch { /* Ignore malformed ticks. */ }
      };
      socket.onclose = () => { if (active) retry = window.setTimeout(connect, 2000); };
      socket.onerror = () => socket.close();
    };
    connect();
    return () => { active = false; if (retry) window.clearTimeout(retry); };
  }, []);
  return prices;
}

export function usePortfolioWs(portfolioId: number | null) {
  const [data, setData] = useState<any>({ pnl: null, positions: [], orders: [], portfolio: null });

  const refresh = useCallback(async () => {
    if (!portfolioId) return;
    try {
      const [summaryResponse, positionsResponse, ordersResponse] = await Promise.all([
        fetch(`${API_BASE}/portfolio/${portfolioId}/summary`),
        fetch(`${API_BASE}/portfolio/${portfolioId}/positions`),
        fetch(`${API_BASE}/portfolio/${portfolioId}/orders`),
      ]);
      const [summary, positions, orders] = await Promise.all([
        summaryResponse.json(), positionsResponse.json(), ordersResponse.json(),
      ]);
      setData({
        pnl: { realized_pnl: summary.realized_pnl || 0, unrealized_pnl: summary.unrealized_pnl || 0, total_pnl: summary.total_pnl || 0 },
        positions: positions.positions || [],
        orders: orders.orders || [],
        portfolio: summary,
      });
    } catch { /* The websocket will retry and the next refresh will recover. */ }
  }, [portfolioId]);

  useEffect(() => {
    if (!portfolioId) return;
    let active = true;
    let retry: number | undefined;
    const connect = () => {
      if (!active) return;
      const socket = new WebSocket(`${WS_BASE}/ws/portfolio/${portfolioId}/pnl`);
      socket.onopen = () => { void refresh(); };
      socket.onmessage = event => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'refresh') { void refresh(); return; }
          setData(previous => ({
            ...previous,
            positions: message.positions || previous.positions,
            orders: message.orders || previous.orders,
            pnl: { ...(previous.pnl || {}), unrealized_pnl: message.unrealized_pnl ?? (previous.pnl?.unrealized_pnl || 0) },
            portfolio: { ...(previous.portfolio || {}), available_cash: message.available_cash, invested_cash: message.invested_cash },
          }));
        } catch { /* Ignore malformed messages. */ }
      };
      socket.onclose = () => { if (active) retry = window.setTimeout(connect, 2000); };
      socket.onerror = () => socket.close();
    };
    void refresh();
    connect();
    return () => { active = false; if (retry) window.clearTimeout(retry); };
  }, [portfolioId, refresh]);

  return { ...data, refresh };
}
