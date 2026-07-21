"""Market data streamer — subscribes to Binance WebSocket for live prices."""

import asyncio
import itertools
import json
import logging
import threading
from typing import Callable, Dict, List, Optional, Set

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

from quantrun.services.brokers import get_registry

log = logging.getLogger("quantrun.market")


class MarketDataStreamer:
    """Manages Binance WebSocket price subscriptions and an in-memory price cache."""

    DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]

    def __init__(self) -> None:
        self.shutdown = False
        self._market_prices: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._active_streams: Set[str] = set()
        self._ws_connection = None
        self._connection_lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()
        self._subscription_lock = asyncio.Lock()
        self._message_id = itertools.count(1)
        self._price_callbacks: List[Callable[[Dict[str, float]], None]] = []
        registry = get_registry()
        self._broker = registry.get("binance")

    def _stream_name(self, symbol: str) -> str:
        if self._broker:
            return self._broker.stream_name(symbol)
        return f"{symbol.lower()}@bookTicker"

    def _is_connection_open(self) -> bool:
        if self._ws_connection is None:
            return False
        closed = getattr(self._ws_connection, "closed", None)
        if closed is not None:
            return not closed
        return getattr(self._ws_connection, "close_code", None) is None

    async def _send_payload(self, payload: dict) -> None:
        if not self._is_connection_open():
            raise RuntimeError("WebSocket not connected")
        async with self._send_lock:
            await self._ws_connection.send(json.dumps(payload))

    async def _open_connection(self) -> None:
        if self._is_connection_open():
            return
        ws_url = self._broker.websocket_url if self._broker else "wss://stream.binance.com:9443/ws"
        log.info("Connecting to %s", ws_url)
        self._ws_connection = await websockets.connect(ws_url, ping_interval=20, ping_timeout=10)
        asyncio.create_task(self._receive_loop(self._ws_connection))

    async def _ensure_connection(self) -> None:
        async with self._connection_lock:
            if not self._is_connection_open():
                await self._open_connection()

    async def _receive_loop(self, connection) -> None:
        try:
            async for message in connection:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                self._process_message(payload)
        except ConnectionClosed as exc:
            log.warning("Connection closed: %s", exc)
        except Exception as exc:
            log.error("Receive loop error: %s", exc)
        finally:
            if self._ws_connection is connection:
                self._ws_connection = None
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running() and self._active_streams and not self.shutdown:
                    await asyncio.sleep(5)
                    await self._ensure_connection()
                    await self._resubscribe_active()
            except RuntimeError:
                pass

    def _process_message(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        parsed = None
        if self._broker:
            parsed = self._broker.process_message(data)
        else:
            symbol = data.get("s")
            bid = data.get("b")
            ask = data.get("a")
            if symbol and bid and ask:
                try:
                    parsed = (symbol.upper(), (float(bid) + float(ask)) / 2.0)
                except (ValueError, TypeError):
                    return
        if not parsed:
            return
        symbol, price = parsed
        old = self._get_cached_price(symbol)
        if old == price:
            return
        self.set_market_price(symbol, price)
        for cb in self._price_callbacks:
            try:
                cb({symbol: price})
            except Exception as exc:
                log.error("Callback error: %s", exc)

    async def _resubscribe_active(self) -> None:
        if not self._active_streams:
            return
        params = [self._stream_name(s) for s in sorted(self._active_streams)]
        await self._send_payload({"method": "SUBSCRIBE", "params": params, "id": next(self._message_id)})

    async def subscribe(self, symbols: List[str]) -> None:
        symbols = [s.strip().upper() for s in symbols if s.strip()]
        if not symbols:
            return
        async with self._subscription_lock:
            new = [s for s in symbols if s not in self._active_streams]
            if not new:
                return
            await self._ensure_connection()
            params = [self._stream_name(s) for s in new]
            await self._send_payload({"method": "SUBSCRIBE", "params": params, "id": next(self._message_id)})
            self._active_streams.update(new)
            log.info("Subscribed: %s", params)

    async def initialize_price_stream(self, symbols: List[str]) -> None:
        if symbols:
            await self.subscribe(symbols)
        else:
            await self._ensure_connection()

    def register_price_callback(self, cb: Callable[[Dict[str, float]], None]) -> None:
        self._price_callbacks.append(cb)

    def set_market_price(self, symbol: str, price: float) -> None:
        with self._lock:
            self._market_prices[symbol.upper()] = price

    def _get_cached_price(self, symbol: str) -> Optional[float]:
        with self._lock:
            return self._market_prices.get(symbol)

    async def get_market_price(self, symbol: str, timeout: float = 5.0) -> Optional[float]:
        norm = symbol.strip().upper()
        cached = self._get_cached_price(norm)
        if cached is not None:
            return cached
        price = None
        try:
            if self._broker:
                price = await self._broker.fetch_price(norm)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.binance.com/api/v3/ticker/price?symbol={norm}"
                    )
                if resp.status_code == 200:
                    price = float(resp.json().get("price"))
        except Exception as exc:
            log.error("Error fetching price for %s: %s", norm, exc)
        if price is not None:
            self.set_market_price(norm, price)
        return price

    async def shutdown_connections(self) -> None:
        """Gracefully close the websocket connection."""
        self.shutdown = True
        if self._ws_connection is not None:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

    def get_all_market_prices(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._market_prices)


market_data_streamer = MarketDataStreamer()
DEFAULT_SYMBOLS = MarketDataStreamer.DEFAULT_SYMBOLS
