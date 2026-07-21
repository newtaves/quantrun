class BrokerError(Exception):
    pass


class SymbolNotFoundError(BrokerError):
    pass


class BrokerConnectionError(BrokerError):
    pass
