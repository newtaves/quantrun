from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Optional, Any


class BrokerAdapter(ABC):
	"""Abstract base for all broker adapters.

	Concrete adapters should implement websocket connection details,
	symbol normalization and conversion helpers, message processing,
	and simple REST helpers for fetching current price / historical data.
	"""

	@property
	@abstractmethod
	def broker_name(self) -> str:
		"""A short identifier for the broker (e.g. 'binance', 'nasdaq')."""

	@property
	@abstractmethod
	def asset_class(self) -> str:
		"""Asset class handled by this adapter, e.g. 'crypto', 'stocks_us', 'stocks_in'."""

	@property
	@abstractmethod
	def websocket_url(self) -> str:
		"""WebSocket endpoint URL for realtime streams (if supported)."""

	@abstractmethod
	def normalize_symbol(self, symbol: str) -> str:
		"""Convert a user-facing symbol to the broker's canonical symbol.

		Example: 'BTC' -> 'BTCUSDT' for Binance.
		"""

	@abstractmethod
	def denormalize_symbol(self, symbol: str) -> str:
		"""Convert a broker symbol back to a user-friendly representation."""

	@abstractmethod
	def stream_name(self, symbol: str) -> str:
		"""Return the stream/topic name to subscribe to for realtime messages."""

	@abstractmethod
	def process_message(self, data: dict) -> Tuple[str, float] | None:
		"""Process an incoming websocket message and return (symbol, price).

		Return None when the message doesn't contain a price update.
		"""

	@abstractmethod
	async def fetch_price(self, symbol: str) -> float | None:
		"""Fetch current ticker/market price via REST API. Return None if unavailable."""

	@abstractmethod
	async def fetch_historical_data(self, symbol: str, interval: str) -> List[dict]:
		"""Fetch historical OHLCV or similar data for the symbol.

		Interval string is implementation-defined (e.g. '1m', '1d').
		"""
