"""Tests for WebSocket endpoints.

These tests require the server to be running:
    quantrun serve

Run with:
    pytest tests/test_websocket.py -v
"""
import asyncio
import json
import time
import pytest

import websockets

WS_BASE = "ws://localhost:8000"


def _server_running() -> bool:
    """Check if the API server is reachable."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(("localhost", 8000))
        sock.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


requires_server = pytest.mark.skipif(
    not _server_running(),
    reason="Server not running on :8000 — start with `quantrun serve`"
)


# ── Price WebSocket ─────────────────────────────────────────────────────────

@requires_server
class TestPricesWebSocket:
    @pytest.mark.asyncio
    async def test_connect_and_receive(self):
        async with websockets.connect(f"{WS_BASE}/ws/prices") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            assert "prices" in data
            assert "BTCUSDT" in data["prices"]

    @pytest.mark.asyncio
    async def test_multiple_messages(self):
        async with websockets.connect(f"{WS_BASE}/ws/prices") as ws:
            messages = []
            deadline = time.time() + 4
            while time.time() < deadline and len(messages) < 3:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                messages.append(json.loads(msg))
            assert len(messages) >= 2
            for m in messages:
                assert "prices" in m
                assert isinstance(m["prices"], dict)

    @pytest.mark.asyncio
    async def test_price_values_are_numeric(self):
        async with websockets.connect(f"{WS_BASE}/ws/prices") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            for sym, price in data["prices"].items():
                assert isinstance(price, (int, float)), f"{sym} price is not numeric"

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Multiple WS connections should all receive data."""
        async def read_one():
            async with websockets.connect(f"{WS_BASE}/ws/prices") as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                return json.loads(msg)

        results = await asyncio.gather(*[read_one() for _ in range(5)])
        assert len(results) == 5
        for r in results:
            assert "prices" in r


# ── Portfolio WebSocket ─────────────────────────────────────────────────────

@requires_server
class TestPortfolioWebSocket:
    @pytest.fixture()
    def portfolio_id(self):
        """Create a temporary portfolio via REST and return its ID."""
        import httpx
        r = httpx.post(f"http://localhost:8000/api/portfolios", json={
            "name": "WS_TEST_PORT",
            "cash": 100000,
        })
        return r.json()["portfolio"]["portfolio_id"]

    @pytest.mark.asyncio
    async def test_connect_and_receive(self, portfolio_id):
        async with websockets.connect(f"{WS_BASE}/ws/portfolio/{portfolio_id}") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            assert "pnl" in data
            assert "positions" in data
            assert "orders" in data
            assert "portfolio" in data

    @pytest.mark.asyncio
    async def test_portfolio_data_matches(self, portfolio_id):
        async with websockets.connect(f"{WS_BASE}/ws/portfolio/{portfolio_id}") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            assert data["portfolio"]["name"] == "WS_TEST_PORT"
            assert data["portfolio"]["available_cash"] == 100000.0

    @pytest.mark.asyncio
    async def test_reflects_new_order(self, portfolio_id):
        """Place an order via REST, then verify it shows up in WS data."""
        import httpx
        httpx.post(f"http://localhost:8000/api/portfolios/{portfolio_id}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01,
        })
        async with websockets.connect(f"{WS_BASE}/ws/portfolio/{portfolio_id}") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            # Position should exist after market buy
            assert len(data["positions"]) >= 1

    @pytest.mark.asyncio
    async def test_nonexistent_portfolio(self):
        async with websockets.connect(f"{WS_BASE}/ws/portfolio/99999") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_multiple_portfolio_connections(self, portfolio_id):
        """Multiple WS connections to the same portfolio should all work."""
        async def read_one():
            async with websockets.connect(f"{WS_BASE}/ws/portfolio/{portfolio_id}") as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                return json.loads(msg)

        results = await asyncio.gather(*[read_one() for _ in range(3)])
        assert len(results) == 3
        for r in results:
            assert "pnl" in r
