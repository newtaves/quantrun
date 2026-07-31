"""Stress tests for the QuantRun application.

Tests throughput, concurrency, and stability under load.
Requires the server to be running:
    quantrun serve

Run with:
    pytest tests/test_stress.py -v -s
"""
import asyncio
import httpx
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import pytest
import websockets

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT"]


def _server_running() -> bool:
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


def _timed_request(method: str, url: str, **kwargs):
    """Execute an HTTP request and return (status_code, latency_ms)."""
    start = time.perf_counter()
    with httpx.Client(timeout=30) as client:
        r = getattr(client, method)(url, **kwargs)
    latency = (time.perf_counter() - start) * 1000
    return r.status_code, latency


def _create_portfolio(name: str, cash: float = 100_000) -> int:
    r = httpx.post(f"{BASE}/api/portfolios", json={"name": name, "cash": cash})
    return r.json()["portfolio"]["portfolio_id"]


def _print_stats(label: str, latencies: list, errors: int, total_count: int, elapsed: float):
    if not latencies:
        print(f"\n[{label}] No successful requests")
        return
    sorted_l = sorted(latencies)
    p99_idx = min(int(len(sorted_l) * 0.99), len(sorted_l) - 1)
    print(f"\n[{label}] {total_count} requests in {elapsed:.2f}s")
    print(f"  Throughput: {total_count / elapsed:.1f} req/s")
    print(f"  Latency:    avg={statistics.mean(latencies):.0f}ms  "
          f"p50={statistics.median(latencies):.0f}ms  "
          f"p99={sorted_l[p99_idx]:.0f}ms  "
          f"max={max(latencies):.0f}ms")
    print(f"  Errors:     {errors}/{total_count}")


# ── REST Throughput Tests ───────────────────────────────────────────────────

@requires_server
class TestRestThroughput:
    def test_create_portfolios_bulk(self):
        """Create 10 portfolios and measure throughput."""
        count = 10
        latencies = []
        errors = 0
        start = time.perf_counter()

        for i in range(count):
            status, lat = _timed_request("post", f"{BASE}/api/portfolios", json={
                "name": f"BULK_{int(time.time())}_{i}",
                "cash": 100000,
            })
            latencies.append(lat)
            if status != 200:
                errors += 1

        total = time.perf_counter() - start
        _print_stats("BULK CREATE", latencies, errors, count, total)
        assert errors == 0

    def test_place_orders_rapid_fire(self):
        """Place 10 market buy orders on a single portfolio as fast as possible."""
        pid = _create_portfolio(f"RAPID_{int(time.time())}", cash=10_000_000)

        count = 10
        latencies = []
        errors = 0
        start = time.perf_counter()

        for i in range(count):
            status, lat = _timed_request("post", f"{BASE}/api/portfolios/{pid}/orders", json={
                "symbol": SYMBOLS[i % len(SYMBOLS)],
                "side": "BUY",
                "usd": 100,
            })
            latencies.append(lat)
            if status != 200:
                errors += 1

        total = time.perf_counter() - start
        _print_stats("RAPID FIRE", latencies, errors, count, total)
        assert errors == 0

    def test_read_endpoints_benchmark(self):
        """Benchmark all read-only endpoints."""
        pid = _create_portfolio(f"READ_{int(time.time())}")

        endpoints = [
            ("GET", f"{BASE}/api/portfolios"),
            ("GET", f"{BASE}/api/portfolios/{pid}"),
            ("GET", f"{BASE}/api/portfolios/{pid}/orders"),
            ("GET", f"{BASE}/api/portfolios/{pid}/positions"),
            ("GET", f"{BASE}/api/portfolios/{pid}/pnl"),
            ("GET", f"{BASE}/api/portfolios/{pid}/history"),
            ("GET", f"{BASE}/api/prices"),
            ("GET", f"{BASE}/api/prices/BTCUSDT"),
        ]

        rounds = 5
        labels = [f"{m} {u.split('/api/')[-1]}" for m, u in endpoints]
        results = {label: [] for label in labels}

        for _ in range(rounds):
            for method, url in endpoints:
                status, lat = _timed_request(method.lower(), url)
                label = f"{method} {url.split('/api/')[-1]}"
                results[label].append(lat)

        print(f"\n[READ BENCHMARK] {rounds} rounds x {len(endpoints)} endpoints")
        for label, lats in results.items():
            print(f"  {label:40s} avg={statistics.mean(lats):6.0f}ms  "
                  f"max={max(lats):6.0f}ms")

    def test_mixed_read_write_load(self):
        """Interleave reads and writes concurrently."""
        pid = _create_portfolio(f"MIXED_{int(time.time())}", cash=10_000_000)

        results = {"reads": [], "writes": [], "errors": 0}

        def do_read():
            status, lat = _timed_request("get", f"{BASE}/api/portfolios/{pid}/positions")
            return "reads", status, lat

        def do_write():
            status, lat = _timed_request("post", f"{BASE}/api/portfolios/{pid}/orders", json={
                "symbol": "BTCUSDT", "side": "BUY", "usd": 50,
            })
            return "writes", status, lat

        tasks = []
        for i in range(10):
            tasks.append(do_read)
            if i % 2 == 0:
                tasks.append(do_write)

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(t) for t in tasks]
            for f in as_completed(futures):
                kind, status, lat = f.result()
                results[kind].append(lat)
                if status != 200:
                    results["errors"] += 1

        print(f"\n[MIXED LOAD] {len(results['reads'])} reads + {len(results['writes'])} writes")
        if results["reads"]:
            print(f"  Read  latency: avg={statistics.mean(results['reads']):.0f}ms  max={max(results['reads']):.0f}ms")
        if results["writes"]:
            print(f"  Write latency: avg={statistics.mean(results['writes']):.0f}ms  max={max(results['writes']):.0f}ms")
        print(f"  Errors: {results['errors']}")
        assert results["errors"] == 0


# ── WebSocket Stress Tests ──────────────────────────────────────────────────

@requires_server
class TestWebSocketStress:
    def test_many_price_connections(self):
        """Open 10 concurrent price WS connections."""
        count = 10

        async def read_one():
            async with websockets.connect(f"{WS_BASE}/ws/prices") as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                return json.loads(msg)

        async def run_all():
            return await asyncio.gather(*[read_one() for _ in range(count)])

        start = time.perf_counter()
        results = asyncio.run(run_all())
        elapsed = time.perf_counter() - start

        assert len(results) == count
        for r in results:
            assert "prices" in r
        print(f"\n[WS PRICE CONNS] {count} connections in {elapsed:.2f}s — all received data")

    def test_many_portfolio_connections(self):
        """Open 5 concurrent portfolio WS connections."""
        pids = []
        for i in range(5):
            pids.append(_create_portfolio(f"WS_STRESS_{int(time.time())}_{i}"))

        async def read_portfolio(pid):
            async with websockets.connect(f"{WS_BASE}/ws/portfolio/{pid}") as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                return json.loads(msg)

        async def run_all():
            return await asyncio.gather(*[read_portfolio(pid) for pid in pids])

        start = time.perf_counter()
        results = asyncio.run(run_all())
        elapsed = time.perf_counter() - start

        assert len(results) == len(pids)
        for r in results:
            assert "pnl" in r
            assert "positions" in r
        print(f"\n[WS PORTFOLIO CONNS] {len(pids)} connections in {elapsed:.2f}s")

    def test_sustained_price_stream(self):
        """Keep a price WS open for 5 seconds and count messages."""
        async def stream():
            messages = []
            async with websockets.connect(f"{WS_BASE}/ws/prices") as ws:
                deadline = time.time() + 5
                while time.time() < deadline:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=2)
                        messages.append(json.loads(msg))
                    except asyncio.TimeoutError:
                        break
            return messages

        start = time.perf_counter()
        messages = asyncio.run(stream())
        elapsed = time.perf_counter() - start

        print(f"\n[SUSTAINED STREAM] {len(messages)} messages in {elapsed:.1f}s "
              f"({len(messages) / elapsed:.1f} msg/s)")
        assert len(messages) >= 1

    def test_rapid_connect_disconnect(self):
        """Rapidly connect and disconnect price WS 5 times."""
        async def connect_disconnect():
            ws = await websockets.connect(f"{WS_BASE}/ws/prices")
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                return json.loads(msg)
            finally:
                await ws.close()

        async def run_all():
            return await asyncio.gather(*[connect_disconnect() for _ in range(5)])

        start = time.perf_counter()
        results = asyncio.run(run_all())
        elapsed = time.perf_counter() - start

        assert len(results) == 5
        for r in results:
            assert "prices" in r
        print(f"\n[RAPID CONNECT/DISCONNECT] 5 cycles in {elapsed:.2f}s")


# ── Portfolio Lifecycle Stress ──────────────────────────────────────────────

@requires_server
class TestLifecycleStress:
    def test_full_lifecycle(self):
        """Create portfolio -> place orders -> close positions -> delete."""
        pid = _create_portfolio(f"LIFECYCLE_{int(time.time())}", cash=500_000)

        # Place 5 market buys
        for sym in SYMBOLS[:5]:
            r = httpx.post(f"{BASE}/api/portfolios/{pid}/orders", json={
                "symbol": sym, "side": "BUY", "usd": 1000,
            })
            assert r.status_code == 200, f"Order failed: {r.text}"

        # Verify positions
        positions = httpx.get(f"{BASE}/api/portfolios/{pid}/positions").json()["positions"]
        assert len(positions) == 5

        # Close all positions
        for pos in positions:
            r = httpx.delete(f"{BASE}/api/positions/{pos['position_id']}")
            assert r.status_code == 200

        # Verify empty
        positions2 = httpx.get(f"{BASE}/api/portfolios/{pid}/positions").json()["positions"]
        assert len(positions2) == 0

        # Verify history
        history = httpx.get(f"{BASE}/api/portfolios/{pid}/history").json()["history"]
        assert len(history) == 5

        # Delete portfolio
        r = httpx.delete(f"{BASE}/api/portfolios/{pid}")
        assert r.status_code == 200
        print(f"\n[FULL LIFECYCLE] 5 orders -> 5 positions -> close all -> delete — OK")

    def test_concurrent_portfolio_operations(self):
        """Multiple threads creating and reading portfolios simultaneously."""
        results = {"creates": 0, "reads": 0, "errors": 0}

        def create_portfolio(i):
            try:
                status, _ = _timed_request("post", f"{BASE}/api/portfolios", json={
                    "name": f"CONCURRENT_{int(time.time())}_{i}", "cash": 50000,
                })
                if status == 200:
                    results["creates"] += 1
                else:
                    results["errors"] += 1
            except Exception:
                results["errors"] += 1

        def read_portfolios():
            try:
                status, _ = _timed_request("get", f"{BASE}/api/portfolios")
                if status == 200:
                    results["reads"] += 1
                else:
                    results["errors"] += 1
            except Exception:
                results["errors"] += 1

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = []
            for i in range(10):
                futures.append(pool.submit(create_portfolio, i))
            for _ in range(5):
                futures.append(pool.submit(read_portfolios))
            for f in as_completed(futures):
                f.result()

        print(f"\n[CONCURRENT OPS] creates={results['creates']}  reads={results['reads']}  "
              f"errors={results['errors']}")
        assert results["errors"] == 0
