"""Central broker registration module.

Importing this module registers built-in adapters into a shared
BrokerRegistry instance accessible via `get_registry()`.
"""
from .registry import BrokerRegistry

# Import known adapters so they can be registered below
from .crypto.binance import BinanceAdapter  # noqa: F401


_registry = BrokerRegistry()

# Register builtin adapters here
try:
    _registry.register("binance", BinanceAdapter)
except Exception:
    # best-effort registration; ignore (yet) if something unexpected occurs
    pass


def get_registry() -> BrokerRegistry:
    """Return the shared BrokerRegistry instance."""
    return _registry


__all__ = ["get_registry", "BrokerRegistry"]
