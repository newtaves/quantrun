import asyncio
import itertools
import json
import logging
import threading
import httpx
from typing import Any, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed


class MarketDataStreamer:
    """Manage Binance market-price websocket subscriptions and shared price cache."""

    WS_URL = "wss://stream.binance.com:9443/ws"
    DEFAULT_SYMBOLS = ["BTCUSDT"]#, "ETHUSDT", "BNBUSDT"]

    def __init__(self) -> None:
        self.shutdown = False
        self._market_prices: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._active_streams: Set[str] = set()
        self._ws_connection: Optional[Any] = None
        self._connection_lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()
        self._subscription_lock = asyncio.Lock()
        self._message_id = itertools.count(1)

    def _stream_name(self, symbol: str) -> str:
        """Return the websocket stream name for a symbol."""
        return f"{symbol.lower()}@bookTicker"

    def _is_connection_open(self) -> bool:
        """Return True when the current websocket connection is still open."""
        if self._ws_connection is None:
            return False

        closed_attr = getattr(self._ws_connection, "closed", None)
        if closed_attr is not None:
            return not closed_attr

        return getattr(self._ws_connection, "close_code", None) is None

    async def _send_payload(self, payload: dict) -> None:
        """Send a JSON payload to the active Binance websocket connection."""
        if not self._is_connection_open():
            raise RuntimeError("WebSocket connection is not available")

        ws_conn = self._ws_connection
        if ws_conn is None:
            raise RuntimeError("WebSocket connection is not available")

        async with self._send_lock:
            await ws_conn.send(json.dumps(payload))

    async def _open_connection(self) -> None:
        """Open a new Binance websocket connection if none exists."""
        if self._is_connection_open():
            return

        logging.info(f"Connecting Binance market price websocket: {self.WS_URL}")
        self._ws_connection = await websockets.connect(
            self.WS_URL, ping_interval=20, ping_timeout=10
        )
        asyncio.create_task(self._receive_loop(self._ws_connection))

    async def _ensure_connection(self) -> None:
        """Ensure there is an active websocket connection."""
        async with self._connection_lock:
            if not self._is_connection_open():
                await self._open_connection()

    async def _receive_loop(self, connection: Any) -> None:
        """Receive and process incoming websocket messages."""
        try:
            async for message in connection:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    logging.warning("Received invalid JSON from Binance websocket")
                    continue
                self._process_message(payload)
        except ConnectionClosed as exc:
            logging.warning(f"Binance websocket connection closed: {exc}")
        except Exception as exc:
            logging.error(f"Error in Binance websocket receive loop: {exc}")
        finally:
            if self._ws_connection is connection:
                self._ws_connection = None
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running() and self._active_streams and not self.shutdown:
                    logging.info("Attempting to reconnect...")
                    await asyncio.sleep(5)
                    await self._ensure_connection()
                    await self._resubscribe_active_streams()
            except RuntimeError:
                # This handles the "no running event loop" error during shutdown
                logging.info("Event loop closed; stopping reconnection attempts.")

    def _process_message(self, data: dict) -> None:
        """Process a single websocket payload into a market price update."""
        if not isinstance(data, dict):
            return

        symbol = data.get("s")
        bid_price = data.get("b")
        ask_price = data.get("a")
        if symbol is None or ask_price is None or bid_price is None:
            return

        try:
            price = (float(bid_price)+float(ask_price))/2
        except (ValueError, TypeError):
            logging.warning(f"Unable to parse price for {symbol}: {ask_price}, {bid_price}")
            return

        self.set_market_price(symbol, price)
        logging.info(f"Updated market price: {symbol}={price}")

    async def _resubscribe_active_streams(self) -> None:
        """Resubscribe all currently active streams after reconnect."""
        if not self._active_streams:
            return

        params = [self._stream_name(symbol) for symbol in sorted(self._active_streams)]
        payload = {"method": "SUBSCRIBE", "params": params, "id": next(self._message_id)}
        await self._send_payload(payload)
        logging.info(f"Resubscribed to active streams: {params}")

    async def _subscribe_symbols(self, symbols: List[str]) -> List[str]:
        """Subscribe to one or more symbol mark-price streams."""
        symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if not symbols:
            return sorted(self._active_streams)

        async with self._subscription_lock:
            new_symbols = [symbol for symbol in symbols if symbol not in self._active_streams]
            if not new_symbols:
                return sorted(self._active_streams)

            await self._ensure_connection()
            params = [self._stream_name(symbol) for symbol in new_symbols]
            payload = {"method": "SUBSCRIBE", "params": params, "id": next(self._message_id)}
            await self._send_payload(payload)
            self._active_streams.update(new_symbols)
            logging.info(f"Subscribed to streams: {params}")
            return sorted(self._active_streams)

    async def _unsubscribe_symbols(self, symbols: List[str]) -> List[str]:
        """Unsubscribe from one or more symbol mark-price streams."""
        symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        if not symbols:
            return sorted(self._active_streams)

        async with self._subscription_lock:
            unsubscribe = [symbol for symbol in symbols if symbol in self._active_streams]
            if not unsubscribe:
                return sorted(self._active_streams)

            await self._ensure_connection()
            params = [self._stream_name(symbol) for symbol in unsubscribe]
            payload = {"method": "UNSUBSCRIBE", "params": params, "id": next(self._message_id)}
            await self._send_payload(payload)
            self._active_streams.difference_update(unsubscribe)
            logging.info(f"Unsubscribed from streams: {params}")
            return sorted(self._active_streams)

    async def initialize_price_stream(self, initial_symbols: List[str]) -> None:
        """Initialize the websocket and subscribe to the initial symbol list."""
        if initial_symbols:
            await self._subscribe_symbols(initial_symbols)
        else:
            await self._ensure_connection()

    def get_all_subscriptions(self) -> List[str]:
        """Return the currently subscribed symbol list."""
        return sorted(self._active_streams)

    def set_market_price(self, symbol: str, price: float) -> None:
        """Store the latest market price for a symbol in the shared cache."""
        normalized = symbol.upper()
        with self._lock:
            self._market_prices[normalized] = price

    def _get_cached_price(self, symbol: str) -> Optional[float]:
        """Return a cached price for a symbol, if present."""
        with self._lock:
            return self._market_prices.get(symbol)

    async def get_market_price(self, symbol: str, timeout: float = 5.0) -> Optional[float]:
        """Return the latest market price for a symbol.

        If the symbol is not already cached, subscribe to it and wait
        briefly for the first market price update.

        Parameters:
            symbol: Trading symbol to query.
            timeout: Maximum seconds to wait for the first update.

        Returns:
            Latest price if available; otherwise None.
        """  
        normalized = symbol.strip().upper()
        if not normalized:
            return None
        current_price = self._get_cached_price(normalized)
        if current_price:
            return current_price
        else:
            # Use an AsyncClient for non-blocking I/O
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.binance.com/api/v3/ticker/price?symbol={normalized}")
                
            if resp.status_code == 200:
                data = resp.json()
                price = float(data.get('price'))
                self.set_market_price(normalized, price)
                await self._subscribe_symbols([normalized])
                return price

    def get_all_market_prices(self) -> Dict[str, float]:
        """Return a snapshot of all current market prices."""
        with self._lock:
            return dict(self._market_prices)


market_data_streamer = MarketDataStreamer()
DEFAULT_SYMBOLS = MarketDataStreamer.DEFAULT_SYMBOLS
