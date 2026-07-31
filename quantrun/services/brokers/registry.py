from typing import Dict, List, Optional, Type

from quantrun.services.brokers.base import BrokerAdapter


class BrokerRegistry:
    """Registry and factory for broker adapters."""

    def __init__(self) -> None:
        self._adapter_classes: Dict[str, Type[BrokerAdapter]] = {}
        self._instances: Dict[str, BrokerAdapter] = {}

    def register(self, name: str, cls: Type[BrokerAdapter]) -> None:
        self._adapter_classes[name] = cls

    def get(self, name: str) -> Optional[BrokerAdapter]:
        if name in self._instances:
            return self._instances[name]
        cls = self._adapter_classes.get(name)
        if cls is None:
            return None
        inst = cls()
        self._instances[name] = inst
        return inst

    def list_brokers(self) -> List[str]:
        return list(self._adapter_classes.keys())
