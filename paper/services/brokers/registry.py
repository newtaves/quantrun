from typing import Dict, Type, Optional, List

from .base import BrokerAdapter


class BrokerRegistry:
    """Registry and factory for broker adapters.

    Responsibilities:
    - Register adapter classes under a broker name
    - Lazily instantiate adapters on first use
    - Provide basic fallback chain support
    """

    def __init__(self):
        self._adapter_classes: Dict[str, Type[BrokerAdapter]] = {}
        self._instances: Dict[str, BrokerAdapter] = {}
        self._fallbacks: Dict[str, List[str]] = {}

    def register(self, broker_name: str, adapter_cls: Type[BrokerAdapter], fallback_chain: Optional[List[str]] = None):
        """Register an adapter class for a broker name.

        adapter_cls should be a subclass of `BrokerAdapter`.
        """
        self._adapter_classes[broker_name] = adapter_cls
        if fallback_chain:
            self._fallbacks[broker_name] = fallback_chain

    def get(self, broker_name: str) -> Optional[BrokerAdapter]:
        """Return a lazily-instantiated adapter for `broker_name` or None if unknown."""
        if broker_name in self._instances:
            return self._instances[broker_name]

        cls = self._adapter_classes.get(broker_name)
        if cls is None:
            return None

        inst = cls()
        self._instances[broker_name] = inst
        return inst

    def resolve_with_fallback(self, broker_name: str) -> Optional[BrokerAdapter]:
        """Return the adapter for broker_name or follow fallback chain if unavailable."""
        adapter = self.get(broker_name)
        if adapter:
            return adapter

        chain = self._fallbacks.get(broker_name, [])
        for alt in chain:
            adapter = self.get(alt)
            if adapter:
                return adapter

        return None
