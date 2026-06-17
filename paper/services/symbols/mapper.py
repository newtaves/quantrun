from typing import Tuple, Optional
from ..exceptions import SymbolNotFoundError
from .config import MAPPINGS


class SymbolMapper:
    """Maps user symbols to (normalized_symbol, broker) tuples.

    The mapper first consults the config mappings, then tries a few
    simple normalization heuristics (remove separators, uppercase).
    """

    def __init__(self, mappings: Optional[dict] = None):
        self._mappings = mappings or MAPPINGS

    def map(self, symbol: str) -> Tuple[str, str]:
        """Return (normalized_symbol, broker) for a given user symbol.

        Raises SymbolNotFoundError when no mapping can be determined.
        """
        if not symbol or not isinstance(symbol, str):
            raise SymbolNotFoundError(f"Invalid symbol: {symbol}")

        key = symbol.strip().upper()

        # direct match
        if key in self._mappings:
            return self._mappings[key]

        # try common separators
        compact = key.replace(":", "").replace("/", "").replace("-", "")
        if compact in self._mappings:
            return self._mappings[compact]

        # try simple suffix patterns (e.g. BTC -> BTCUSDT on binance)
        if key.isalpha() and key in self._mappings:
            return self._mappings[key]

        # wildcard patterns in mappings (keys ending with '*')
        for k, v in self._mappings.items():
            if k.endswith("*"):
                prefix = k[:-1]
                if key.startswith(prefix):
                    return v

        raise SymbolNotFoundError(f"No mapping found for symbol '{symbol}'")
