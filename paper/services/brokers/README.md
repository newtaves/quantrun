Adding a new broker adapter
===========================

This file documents the recommended minimal steps and examples for adding a
new broker adapter to the codebase.

1) Create the adapter
---------------------

Create a new Python file under `paper/services/brokers/<category>/` (for
example `crypto/kraken.py` or `stocks_us/nasdaq.py`) and implement a class
subclassing `BrokerAdapter`.

Minimum methods to implement:
- `broker_name(self) -> str`
- `asset_class(self) -> str`
- `websocket_url(self) -> str`
- `normalize_symbol(self, symbol: str) -> str`
- `denormalize_symbol(self, symbol: str) -> str`
- `stream_name(self, symbol: str) -> str`
- `process_message(self, data: dict) -> tuple[str, float] | None`
- `async fetch_price(self, symbol: str) -> float | None`
- `async fetch_historical_data(self, symbol: str, interval: str) -> list`

2) Add symbol mappings
----------------------

If the broker is primary for certain user symbols, add entries to
`paper/services/symbols/config.py` mapping user strings to `(normalized, broker)`.

3) Register the adapter
------------------------

Import and register the adapter in `paper/services/brokers/__init__.py`:

from .crypto.kraken import KrakenAdapter
_registry.register("kraken", KrakenAdapter)

The shared registry is returned by `paper.services.brokers.get_registry()` and
is used by `MarketDataStreamer` to obtain adapters.

4) Verify parsing and subscribe behavior
---------------------------------------

- Ensure `stream_name()` returns the correct websocket topic string.
- Ensure `process_message()` extracts a canonical symbol and a numeric price.
- Implement `fetch_price()` for REST fallbacks used by the streamer.

5) Tests and docs
-----------------

Create unit tests that mock websocket messages and REST responses to validate
the adapter. Update `paper/services/symbols/config.py` and this README with any
broker-specific notes.

6) Optional: fallback chains
---------------------------

Use the `fallback_chain` parameter of `_registry.register()` to provide
alternate brokers to try when the primary is unavailable.

Example quick adapter skeleton
------------------------------

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
