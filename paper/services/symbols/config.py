"""Symbol mapping configuration.

This module contains a simple dict mapping user-provided symbol strings
to a tuple of (normalized_symbol, broker_name). It is intentionally
small and easy to extend; production installations can load this from
YAML/JSON or an external service.
"""

# Exact mappings. Keys should be uppercase.
MAPPINGS = {
    # Crypto
    "BTC": ("BTCUSDT", "binance"),
    "BTC:USDT": ("BTCUSDT", "binance"),
    "ETH": ("ETHUSDT", "binance"),

}
