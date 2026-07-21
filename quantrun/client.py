"""QuantRun SDK — clean public interface for strategies and scripts.

This is the only module external code should import. It hides all
internal details (database, execution engine, websocket, brokers).

A background daemon automatically starts on first use to keep the
WebSocket price feed and execution engine alive for limit orders,
stop-loss, and target checks.

Usage:
    from quantrun.client import QuantRun

    qr = QuantRun()
    qr.init()
    order = qr.buy(1, "BTCUSDT", usd=10)
    print(order)
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import threading
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from quantrun.db import get_session, init_db
from quantrun.db.models import Order, OrderSide
from quantrun.services.execution_engine import order_executor
from quantrun.services.market_data import market_data_streamer

log = logging.getLogger("quantrun.sdk")


# ── Background daemon ────────────────────────────────────────────────────────

class _Daemon:
    """Runs the WebSocket price feed and execution engine in a background thread.

    The daemon syncs state from the DB, opens a Binance WebSocket connection,
    and processes every price tick through the execution engine so that limit
    orders, stop-loss, and target checks work without a separate `quantrun stream`.
    """

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._started = threading.Event()
        self._shutdown = False

    def start(self, symbols: Optional[list[str]] = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._shutdown = False
        self._thread = threading.Thread(target=self._run, args=(symbols,), daemon=True)
        self._thread.start()
        self._started.wait(timeout=10)

    def stop(self) -> None:
        self._shutdown = True
        market_data_streamer.shutdown = True
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self, symbols: Optional[list[str]]) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_main(symbols))

    async def _async_main(self, symbols: Optional[list[str]]) -> None:
        await order_executor.sync_from_database()

        active = set(symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"])
        for o in order_executor.get_pending_orders():
            active.add(o.symbol.upper())
        for pos in order_executor._active_positions.values():
            active.add(pos.symbol.upper())

        log.info("Daemon starting price stream for: %s", sorted(active))
        await market_data_streamer.initialize_price_stream(list(active))
        market_data_streamer.register_price_callback(order_executor.check_on_price_update)

        self._started.set()

        try:
            while not self._shutdown:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        finally:
            market_data_streamer.shutdown = True
            log.info("Daemon stopped.")


_daemon = _Daemon()


def _ensure_daemon(symbols: Optional[list[str]] = None) -> None:
    if not _daemon._started.is_set():
        _daemon.start(symbols)


atexit.register(_daemon.stop)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class OrderResult:
    order_id: int
    status: str
    symbol: str
    side: str
    quantity: float
    price: Optional[float] = None
    cost: Optional[float] = None
    target: Optional[float] = None
    stoploss: Optional[float] = None
    error: Optional[str] = None


@dataclass
class PositionResult:
    position_id: int
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    target: Optional[float] = None
    stoploss: Optional[float] = None


@dataclass
class PortfolioResult:
    portfolio_id: int
    name: str
    available_cash: float
    invested_cash: float
    total_pnl: float
    description: Optional[str] = None


@dataclass
class PnLResult:
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    positions: list[PositionResult] = field(default_factory=list)


# ── SDK client ───────────────────────────────────────────────────────────────

class QuantRun:
    """SDK client for the QuantRun paper trading engine.

    A background daemon starts automatically on first use to keep the
    WebSocket price feed and execution engine alive. This ensures limit
    orders, stop-loss, and target checks work without a separate process.
    """

    def __init__(self) -> None:
        self._initialized = False

    def init(self, symbols: Optional[list[str]] = None) -> None:
        """Initialize the database and start the background daemon."""
        init_db()
        self._initialized = True
        _ensure_daemon(symbols)

    def _ensure_init(self) -> None:
        if not self._initialized:
            self.init()

    def _session(self):
        return get_session()

    def stop(self) -> None:
        """Stop the background daemon."""
        _daemon.stop()

    # ── Portfolio ──

    def create_portfolio(self, name: str, cash: float = 10000, description: str = "") -> PortfolioResult:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            p = mgr.create_portfolio(name, description, Decimal(str(cash)))
            return PortfolioResult(
                portfolio_id=p.id, name=p.name, description=p.description,
                available_cash=float(p.available_cash), invested_cash=float(p.invested_cash),
                total_pnl=float(p.total_pnl),
            )
        finally:
            session.close()

    def list_portfolios(self) -> list[PortfolioResult]:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            return [
                PortfolioResult(
                    portfolio_id=p.id, name=p.name, description=p.description,
                    available_cash=float(p.available_cash), invested_cash=float(p.invested_cash),
                    total_pnl=float(p.total_pnl),
                )
                for p in mgr.list_portfolios()
            ]
        finally:
            session.close()

    def get_portfolio(self, portfolio_id: int) -> Optional[PortfolioResult]:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            p = mgr.get_portfolio(portfolio_id)
            if not p:
                return None
            return PortfolioResult(
                portfolio_id=p.id, name=p.name, description=p.description,
                available_cash=float(p.available_cash), invested_cash=float(p.invested_cash),
                total_pnl=float(p.total_pnl),
            )
        finally:
            session.close()

    def delete_portfolio(self, portfolio_id: int) -> None:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            PortfolioManager(session).delete_portfolio(portfolio_id)
        finally:
            session.close()

    # ── Price ──

    def get_price(self, symbol: str) -> Optional[float]:
        """Fetch current market price. Uses cached value if daemon is running."""
        self._ensure_init()
        cached = market_data_streamer._get_cached_price(symbol.upper())
        if cached is not None:
            return cached
        import asyncio
        return asyncio.run(market_data_streamer.get_market_price(symbol))

    def get_prices(self, symbols: Optional[list[str]] = None) -> dict[str, float]:
        """Return all cached market prices. Fetches via REST if daemon not running."""
        self._ensure_init()
        cached = market_data_streamer.get_all_market_prices()
        if cached:
            return cached

        import asyncio

        async def _fetch():
            syms = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
            for s in syms:
                await market_data_streamer.get_market_price(s)
            return market_data_streamer.get_all_market_prices()

        return asyncio.run(_fetch())

    # ── Orders ──

    def buy(
        self,
        portfolio_id: int,
        symbol: str,
        *,
        usd: Optional[float] = None,
        qty: Optional[float] = None,
        limit: Optional[float] = None,
        target: Optional[float] = None,
        stoploss: Optional[float] = None,
    ) -> OrderResult:
        """Place a BUY order. Specify either `usd` or `qty`."""
        return self._place_order(portfolio_id, symbol, "BUY", usd=usd, qty=qty,
                                 limit=limit, target=target, stoploss=stoploss)

    def sell(
        self,
        portfolio_id: int,
        symbol: str,
        *,
        usd: Optional[float] = None,
        qty: Optional[float] = None,
        limit: Optional[float] = None,
        target: Optional[float] = None,
        stoploss: Optional[float] = None,
    ) -> OrderResult:
        """Place a SELL order. Specify either `usd` or `qty`."""
        return self._place_order(portfolio_id, symbol, "SELL", usd=usd, qty=qty,
                                 limit=limit, target=target, stoploss=stoploss)

    def _place_order(
        self,
        portfolio_id: int,
        symbol: str,
        side: str,
        *,
        usd: Optional[float] = None,
        qty: Optional[float] = None,
        limit: Optional[float] = None,
        target: Optional[float] = None,
        stoploss: Optional[float] = None,
    ) -> OrderResult:
        self._ensure_init()

        if usd is None and qty is None:
            return OrderResult(0, "ERROR", symbol, side, 0, error="Specify usd or qty")
        if usd is not None and qty is not None:
            return OrderResult(0, "ERROR", symbol, side, 0, error="Specify only one of usd or qty")

        if usd is not None:
            price = self.get_price(symbol)
            if price is None:
                return OrderResult(0, "ERROR", symbol, side, 0, error=f"Cannot fetch price for {symbol}")
            qty = round(usd / price, 6)

        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            o = Order(
                portfolio_id=portfolio_id,
                symbol=symbol.upper(),
                side=OrderSide(side.upper()),
                quantity=Decimal(str(qty)),
                limit_price=Decimal(str(limit)) if limit is not None else None,
                target=Decimal(str(target)) if target is not None else None,
                stoploss=Decimal(str(stoploss)) if stoploss is not None else None,
            )
            created = mgr.place_order(o)
            order_executor.add_order(created)

            # Market orders: execute immediately
            if created.limit_price is None:
                price = self.get_price(symbol)
                if price is not None:
                    loop = _daemon._loop
                    if loop and loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            order_executor.execute_order(created, Decimal(str(price))), loop
                        )
                        future.result(timeout=10)
                    else:
                        asyncio.run(order_executor.execute_order(created, Decimal(str(price))))

            session.refresh(created)

            return OrderResult(
                order_id=created.id,
                status=created.status.value,
                symbol=created.symbol,
                side=created.side.value,
                quantity=float(created.quantity),
                price=float(created.executed_price) if created.executed_price else None,
                cost=float(created.executed_price * created.quantity) if created.executed_price else None,
                target=float(created.target) if created.target else None,
                stoploss=float(created.stoploss) if created.stoploss else None,
            )
        except Exception as e:
            return OrderResult(0, "ERROR", symbol, side, qty or 0, error=str(e))
        finally:
            session.close()

    def cancel_order(self, order_id: int) -> None:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            PortfolioManager(session).cancel_order(order_id)
        finally:
            session.close()

    # ── Positions ──

    def get_positions(self, portfolio_id: int) -> list[PositionResult]:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            positions = mgr.get_positions(portfolio_id)
            all_pnl = order_executor.calculate_unrealized_pnl()
            pnl_map = {r["position_id"]: r for r in all_pnl}
            results = []
            for p in positions:
                live = pnl_map.get(p.id)
                results.append(PositionResult(
                    position_id=p.id, symbol=p.symbol, side=p.side.value,
                    quantity=float(p.quantity), entry_price=float(p.entry_price),
                    current_price=live["current_price"] if live else None,
                    unrealized_pnl=live["unrealized_pnl"] if live else None,
                    target=float(p.target) if p.target else None,
                    stoploss=float(p.stoploss) if p.stoploss else None,
                ))
            return results
        finally:
            session.close()

    def close_position(self, position_id: int) -> None:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            from quantrun.db.models import ExitReason
            PortfolioManager(session).close_position(position_id, ExitReason.MANUAL)
        finally:
            session.close()

    # ── PnL ──

    def get_pnl(self, portfolio_id: int) -> PnLResult:
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            total = mgr.calculate_total_pnl(portfolio_id)
            positions = [
                PositionResult(
                    position_id=r["position_id"], symbol=r["symbol"], side=r["side"],
                    quantity=r["quantity"], entry_price=r["entry_price"],
                    current_price=r["current_price"], unrealized_pnl=r["unrealized_pnl"],
                    target=r.get("target"), stoploss=r.get("stoploss"),
                )
                for r in total["positions"]
            ]
            return PnLResult(
                total_pnl=float(total["total_pnl"]),
                unrealized_pnl=float(total["unrealized_pnl"]),
                realized_pnl=float(total["realized_pnl"]),
                positions=positions,
            )
        finally:
            session.close()

    # ── History ──

    def get_history(self, portfolio_id: int) -> list[dict]:
        """Return closed trade history for a portfolio."""
        self._ensure_init()
        session = self._session()
        try:
            from quantrun.services.portfolio_manager import PortfolioManager
            mgr = PortfolioManager(session)
            return [
                {
                    "id": h.id,
                    "symbol": h.symbol,
                    "side": h.side.value,
                    "quantity": float(h.quantity),
                    "entry_price": float(h.entry_price),
                    "exit_price": float(h.exit_price),
                    "realized_pnl": float(h.realized_pnl),
                    "exit_reason": h.exit_reason.value,
                    "opened_at": str(h.opened_at),
                    "closed_at": str(h.closed_at),
                }
                for h in mgr.get_position_history(portfolio_id)
            ]
        finally:
            session.close()
