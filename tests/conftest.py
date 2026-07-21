"""Shared fixtures for all tests.

Uses a temporary SQLite database so tests never touch production data.
Mocks the Binance WebSocket daemon so unit/API tests don't need network.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Point DB at a temp file before anything imports quantrun
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["QUANTRUN_DB"] = _tmp_db.name

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


FAKE_PRICES = {
    "BTCUSDT": 85000.0,
    "ETHUSDT": 3200.0,
    "SOLUSDT": 180.0,
    "ADAUSDT": 0.45,
    "DOGEUSDT": 0.12,
    "XRPUSDT": 2.10,
}


# ── Async helpers for mocks ─────────────────────────────────────────────────

async def _fake_get_market_price(self, symbol):
    return FAKE_PRICES.get(symbol.upper())


async def _fake_init_stream(self, symbols=None):
    pass


def _fake_get_cached(self, symbol):
    return FAKE_PRICES.get(symbol.upper())


def _fake_get_all(self):
    return dict(FAKE_PRICES)


# ── Mock the market data streamer so we never hit Binance ────────────────────

@pytest.fixture(autouse=True, scope="session")
def mock_market_data():
    """Patch the Binance price streamer with fake prices for the entire session."""
    p1 = patch(
        "quantrun.services.market_data.MarketDataStreamer.get_market_price",
        _fake_get_market_price,
    )
    p2 = patch(
        "quantrun.services.market_data.MarketDataStreamer.get_all_market_prices",
        _fake_get_all,
    )
    p3 = patch(
        "quantrun.services.market_data.MarketDataStreamer._get_cached_price",
        _fake_get_cached,
    )
    p4 = patch(
        "quantrun.services.market_data.MarketDataStreamer.initialize_price_stream",
        _fake_init_stream,
    )

    p1.start()
    p2.start()
    p3.start()
    p4.start()

    yield FAKE_PRICES

    p1.stop()
    p2.stop()
    p3.stop()
    p4.stop()


@pytest.fixture(autouse=True, scope="session")
def prevent_daemon_start():
    """Prevent the SDK background daemon from starting during tests."""
    with patch("quantrun.client._ensure_daemon"):
        yield


@pytest.fixture()
def fresh_db():
    """Create a clean database for each test function."""
    from quantrun.db.database import init_db, engine
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


@pytest.fixture()
def sdk(fresh_db):
    """Return a QuantRun SDK instance (no daemon)."""
    from quantrun.client import QuantRun
    qr = QuantRun()
    qr._initialized = True  # skip init which would start daemon
    return qr
