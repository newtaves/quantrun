import { useEffect, useRef, useState } from 'react';

const WS_BASE = import.meta.env.VITE_WS_BASE || "ws://localhost:8000";

export function usePricesWs() {
  const [prices, setPrices] = useState<Record<string, number>>({});
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let alive = true;
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/ws/prices`);
      wsRef.current = ws;
      ws.onmessage = (event) => {
        if (!alive) return;
        try {
          const data = JSON.parse(event.data);
          if (data.prices) setPrices(prev => ({ ...prev, ...data.prices }));
        } catch {}
      };
      ws.onclose = () => {
        if (alive) setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { alive = false; wsRef.current?.close(); };
  }, []);

  return prices;
}

export function usePortfolioWs(portfolioId: number | null) {
  const [data, setData] = useState<{
    pnl: any;
    positions: any[];
    orders: any[];
    portfolio: any;
  }>({ pnl: null, positions: [], orders: [], portfolio: null });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!portfolioId) return;
    let alive = true;
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/ws/portfolio/${portfolioId}`);
      wsRef.current = ws;
      ws.onmessage = (event) => {
        if (!alive) return;
        try {
          const d = JSON.parse(event.data);
          setData(d);
        } catch {}
      };
      ws.onclose = () => {
        if (alive) setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { alive = false; wsRef.current?.close(); };
  }, [portfolioId]);

  return data;
}
