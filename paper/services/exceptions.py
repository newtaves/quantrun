class BrokerError(Exception):
    """Base exception for broker-related errors."""
    pass


class SymbolNotFoundError(BrokerError):
    """Raised when a symbol cannot be mapped to any broker."""
    pass


class BrokerConnectionError(BrokerError):
    """Raised when connection to a broker fails or is unavailable."""
    pass


class InvalidSymbolError(BrokerError):
    """Raised when a symbol is syntactically invalid for a broker."""
    pass
