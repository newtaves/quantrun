from typing import List, Optional, Tuple

import httpx

from quantrun.services.brokers.base import BrokerAdapter


class BinanceAdapter(BrokerAdapter):
    """Binance REST/WebSocket adapter for crypto market data."""

    WS_URL = "wss://stream.binance.com:9443/ws"
    REST_BASE = "https://api.binance.com"

    @property
    def broker_name(self) -> str:
        return "binance"

    @property
    def asset_class(self) -> str:
        return "crypto"

    @property
    def websocket_url(self) -> str:
        return self.WS_URL

    def normalize_symbol(self, symbol: str) -> str:
        s = symbol.strip().upper()
        s = s.replace(":", "").replace("/", "").replace("-", "")
        if s.isalpha() and len(s) <= 6 and not any(q in s for q in ("USDT", "BTC", "USD")):
            s = f"{s}USDT"
        return s

    def denormalize_symbol(self, symbol: str) -> str:
        s = symbol.strip().upper()
        if s.endswith("USDT"):
            return s[:-4]
        return s

    def stream_name(self, symbol: str) -> str:
        sym = self.normalize_symbol(symbol)
        return f"{sym.lower()}@bookTicker"

    def process_message(self, data: dict) -> Optional[Tuple[str, float]]:
        if not isinstance(data, dict):
            return None
        symbol = data.get("s")
        bid_price = data.get("b")
        ask_price = data.get("a")
        if symbol is None or bid_price is None or ask_price is None:
            return None
        try:
            price = (float(bid_price) + float(ask_price)) / 2.0
        except (ValueError, TypeError):
            return None
        return symbol.upper(), price

    async def fetch_price(self, symbol: str) -> Optional[float]:
        symbol = self.normalize_symbol(symbol)
        url = f"{self.REST_BASE}/api/v3/ticker/price?symbol={symbol}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200:
            return None
        data = resp.json()
        try:
            return float(data.get("price"))
        except (TypeError, ValueError):
            return None

    async def fetch_historical_data(self, symbol: str, interval: str = "1m") -> List[dict]:
        symbol = self.normalize_symbol(symbol)
        url = f"{self.REST_BASE}/api/v3/klines?symbol={symbol}&interval={interval}&limit=500"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=20.0)
        if resp.status_code != 200:
            return []
        raw = resp.json()
        return [
            {
                "open_time": item[0],
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "close_time": item[6],
            }
            for item in raw
        ]
