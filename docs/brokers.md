# Broker Adapter Guide

This document explains how to add and register broker adapters for the
unified multi-broker market data service implemented in `paper/services/`.

Overview
--------

Adapters encapsulate broker-specific logic (symbol formats, websocket
topics, message formats, REST endpoints) behind a common `BrokerAdapter`
interface. The system uses a central `BrokerRegistry` to register adapters
and lazily instantiate them for use by `MarketDataStreamer`.

Key files
---------

- `paper/services/brokers/base.py` — `BrokerAdapter` abstract base class.
- `paper/services/brokers/registry.py` — `BrokerRegistry` for registration
  and lazy instantiation.
- `paper/services/brokers/__init__.py` — central registry instance and
  built-in adapter registration (e.g. `binance`).
- `paper/services/market_data.py` — streamer delegates parsing and
  REST fetches to adapters.
- `paper/services/symbols/config.py` — symbol → (normalized, broker)
  mappings used by the `SymbolMapper`.

Adding a new adapter (step-by-step)
-----------------------------------

1. Create the adapter file

   - Place a new file under `paper/services/brokers/<category>/`, for example
     `crypto/kraken.py` or `stocks_us/nasdaq.py`.
   - Implement a class that inherits `BrokerAdapter` and fully implements
     the abstract methods:
     - `broker_name`, `asset_class`, `websocket_url`
     - `normalize_symbol`, `denormalize_symbol`, `stream_name`
     - `process_message(data)` → `(symbol, price) | None`
     - `async fetch_price(symbol)` → `float | None`
     - `async fetch_historical_data(symbol, interval)` → `list`

2. Add symbol mappings (optional)

   - If the broker should be preferred for particular user symbols, add or
     adjust entries in `paper/services/symbols/config.py` mapping user-facing
     strings to `(normalized_symbol, broker_name)`.

3. Register the adapter centrally

   - Import and register the adapter in `paper/services/brokers/__init__.py`:

     from .crypto.kraken import KrakenAdapter
     _registry.register("kraken", KrakenAdapter)

   - The shared registry instance is available via
     `paper.services.brokers.get_registry()` and is used by the streamer.

4. Verify behavior

   - Ensure `stream_name()` matches the broker websocket topic naming.
   - Ensure `process_message()` returns a canonical symbol and numeric price.
   - Implement `fetch_price()` for REST fallback when the websocket may not
     provide an immediate update.

5. Tests and documentation

   - Add unit tests that mock websocket messages and REST responses.
   - Document any broker-specific caveats in this file and in
     `paper/services/symbols/config.py` if needed.

Example adapter skeleton
------------------------

```py
from paper.services.brokers.base import BrokerAdapter

class ExampleAdapter(BrokerAdapter):
    @property
    def broker_name(self) -> str:
        return "example"

    @property
    def asset_class(self) -> str:
        return "crypto"

    @property
    def websocket_url(self) -> str:
        return "wss://example/ws"

    def normalize_symbol(self, symbol: str) -> str:
        return symbol.strip().upper()

    def denormalize_symbol(self, symbol: str) -> str:
        return symbol

    def stream_name(self, symbol: str) -> str:
        return f"{self.normalize_symbol(symbol).lower()}@ticker"

    def process_message(self, data: dict):
        # parse and return (symbol, price)
        return None

    async def fetch_price(self, symbol: str):
        return None

    async def fetch_historical_data(self, symbol: str, interval: str):
        return []

```

Dependencies
------------

- Common: `httpx`, `websockets`.
- Stocks: `yfinance` is recommended for US/India stocks adapters.

Notes
-----

The current implementation registers `binance` by default. To enable
multi-broker routing in `MarketDataStreamer`, the streamer must be
refactored to consult the `SymbolMapper` and route per-broker subscriptions
and connections. This is planned as a follow-up refactor.
