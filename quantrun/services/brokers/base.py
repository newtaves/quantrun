from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class BrokerAdapter(ABC):
    """Abstract base for all broker adapters."""

    @property
    @abstractmethod
    def broker_name(self) -> str:
        ...

    @property
    @abstractmethod
    def asset_class(self) -> str:
        ...

    @property
    @abstractmethod
    def websocket_url(self) -> str:
        ...

    @abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        ...

    @abstractmethod
    def denormalize_symbol(self, symbol: str) -> str:
        ...

    @abstractmethod
    def stream_name(self, symbol: str) -> str:
        ...

    @abstractmethod
    def process_message(self, data: dict) -> Optional[Tuple[str, float]]:
        ...

    @abstractmethod
    async def fetch_price(self, symbol: str) -> Optional[float]:
        ...

    @abstractmethod
    async def fetch_historical_data(self, symbol: str, interval: str) -> List[dict]:
        ...
