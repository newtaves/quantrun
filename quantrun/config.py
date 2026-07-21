"""Application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("QUANTRUN_DB", str(BASE_DIR / "quantrun.db"))
DB_URL = f"sqlite:///{DB_PATH}"

# Binance
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
BINANCE_REST_URL = "https://api.binance.com"

# Defaults
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
DEFAULT_USER_ID = 1
