from .base import BrokerAdapter
from .registry import BrokerRegistry
from .crypto.binance import BinanceAdapter

_registry = BrokerRegistry()
_registry.register("binance", BinanceAdapter)


def get_registry() -> BrokerRegistry:
    return _registry
