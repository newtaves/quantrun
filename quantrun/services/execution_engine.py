"""In-memory execution engine for paper trading."""

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from quantrun.db.database import engine
from quantrun.db.models import (
    ExitReason,
    Order,
    OrderSide,
    OrderStatus,
    Portfolio,
    Position,
    PositionHistory,
)
from quantrun.services.market_data import market_data_streamer

log = logging.getLogger("quantrun.engine")


class OrderExecutor:
    """In-memory execution engine that matches orders and manages positions.

    Maintains per-symbol orderbooks, executes market/limit orders,
    tracks SL/TP for open positions, and archives closed trades.
    """

    def __init__(self) -> None:
        self._buy_orders: Dict[str, List[Order]] = {}
        self._sell_orders: Dict[str, List[Order]] = {}
        self._active_positions: Dict[int, Position] = {}
        self._order_registry: Dict[int, Order] = {}
        self._portfolio_cash: Dict[int, Decimal] = {}
        self._lock = asyncio.Lock()

    def _get_session(self) -> Session:
        return Session(engine)

    # ── Orderbook helpers ──

    @staticmethod
    def _sort_key_buy(order: Order):
        if order.limit_price is None:
            return (0, Decimal("0"))
        return (1, order.limit_price)

    @staticmethod
    def _sort_key_sell(order: Order):
        if order.limit_price is None:
            return (0, Decimal("0"))
        return (1, -order.limit_price)

    def add_order(self, order: Order) -> None:
        sym = order.symbol.upper()
        if order.side == OrderSide.BUY:
            bucket = self._buy_orders.setdefault(sym, [])
            bucket.append(order)
            bucket.sort(key=self._sort_key_buy)
        else:
            bucket = self._sell_orders.setdefault(sym, [])
            bucket.append(order)
            bucket.sort(key=self._sort_key_sell)
        if order.id is not None:
            self._order_registry[order.id] = order

    def remove_order(self, order: Order) -> None:
        bucket = (
            self._buy_orders.get(order.symbol.upper(), [])
            if order.side == OrderSide.BUY
            else self._sell_orders.get(order.symbol.upper(), [])
        )
        try:
            bucket.remove(order)
        except ValueError:
            pass
        if order.id is not None:
            self._order_registry.pop(order.id, None)

    def get_pending_orders(self, symbol: Optional[str] = None) -> List[Order]:
        if symbol:
            return self._buy_orders.get(symbol.upper(), []) + self._sell_orders.get(symbol.upper(), [])
        out: List[Order] = []
        for b in self._buy_orders.values():
            out.extend(b)
        for b in self._sell_orders.values():
            out.extend(b)
        return out

    # ── Market tick ──

    async def process_market_tick(self, symbol: str, price: Decimal) -> None:
        async with self._lock:
            await self._execute_limit_orders(symbol, price)
            await self._check_stoploss(symbol, price)
            await self._check_targets(symbol, price)

    async def _execute_limit_orders(self, symbol: str, price: Decimal) -> None:
        sym = symbol.upper()
        for order in list(self._buy_orders.get(sym, [])):
            if order.limit_price is None or price <= order.limit_price:
                await self.execute_order(order, price)
        for order in list(self._sell_orders.get(sym, [])):
            if order.limit_price is None or price >= order.limit_price:
                await self.execute_order(order, price)

    # ── Order execution ──

    async def execute_order(self, order: Order, exec_price: Decimal) -> Optional[Position]:
        pid = order.portfolio_id
        cost = exec_price * order.quantity

        available = self._portfolio_cash.get(pid)
        if available is None:
            def _fetch():
                with self._get_session() as s:
                    p = s.get(Portfolio, pid)
                    return p.available_cash if p else None
            available = await asyncio.to_thread(_fetch)
            if available is None:
                return None
            self._portfolio_cash[pid] = available

        if available < cost:
            log.warning("Insufficient cash for order #%s — cancelling", order.id)
            self.remove_order(order)
            def _cancel():
                with self._get_session() as s:
                    o = s.get(Order, order.id)
                    if o and o.status == OrderStatus.PENDING:
                        o.status = OrderStatus.CANCELLED
                        s.add(o)
                        s.commit()
            await asyncio.to_thread(_cancel)
            return None

        self._portfolio_cash[pid] = available - cost
        return await self._create_position(order, exec_price)

    async def _create_position(self, order: Order, exec_price: Decimal) -> Position:
        now = datetime.now(UTC)
        cost = exec_price * order.quantity
        position = Position(
            portfolio_id=order.portfolio_id,
            order_id=order.id,
            symbol=order.symbol.upper(),
            side=order.side,
            quantity=order.quantity,
            entry_price=exec_price,
            target=order.target,
            stoploss=order.stoploss,
            opened_at=now,
        )

        def _save():
            with self._get_session() as s:
                o = s.get(Order, order.id)
                if o:
                    o.status = OrderStatus.EXECUTED
                    o.executed_price = exec_price
                    o.executed_at = now
                    s.add(o)
                p = s.get(Portfolio, order.portfolio_id)
                if p:
                    p.available_cash -= cost
                    p.invested_cash += cost
                    s.add(p)
                s.add(position)
                s.commit()
                s.refresh(position)

        await asyncio.to_thread(_save)
        self.remove_order(order)
        self._active_positions[position.id] = position
        log.info("Order #%s EXECUTED -> Position #%s %s %s @ %s", order.id, position.id, position.side.value, position.quantity, exec_price)
        return position

    # ── Position closure ──

    async def close_position(self, position: Position, exit_price: Decimal, reason: ExitReason = ExitReason.MANUAL) -> None:
        if position.side == OrderSide.BUY:
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity

        entry_cost = position.entry_price * position.quantity
        cash_returned = entry_cost + pnl
        pid = position.portfolio_id

        self._portfolio_cash[pid] = self._portfolio_cash.get(pid, Decimal("0")) + cash_returned

        def _save():
            with self._get_session() as s:
                port = s.get(Portfolio, pid)
                if port:
                    port.available_cash += cash_returned
                    port.invested_cash = max(Decimal("0"), port.invested_cash - entry_cost)
                    port.total_pnl += pnl
                    s.add(port)
                history = PositionHistory(
                    portfolio_id=pid,
                    order_id=position.order_id,
                    symbol=position.symbol,
                    side=position.side,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    realized_pnl=pnl,
                    target=position.target,
                    stoploss=position.stoploss,
                    exit_reason=reason,
                    opened_at=position.opened_at,
                    closed_at=datetime.now(UTC),
                )
                s.add(history)
                db_pos = s.get(Position, position.id)
                if db_pos:
                    s.delete(db_pos)
                s.commit()

        await asyncio.to_thread(_save)
        self._active_positions.pop(position.id, None)
        log.info("Position #%s closed | %s %s | Exit: %s | PnL: %s | Reason: %s", position.id, position.symbol, position.side.value, exit_price, pnl, reason.value)

    # ── SL / TP ──

    async def _check_stoploss(self, symbol: str, price: Decimal) -> None:
        sym = symbol.upper()
        for pos in [p for p in self._active_positions.values() if p.symbol == sym and p.stoploss is not None]:
            hit = (pos.side == OrderSide.BUY and price <= pos.stoploss) or (pos.side == OrderSide.SELL and price >= pos.stoploss)
            if hit:
                log.info("SL hit for position #%s @ %s", pos.id, price)
                await self.close_position(pos, price, ExitReason.STOPLOSS)

    async def _check_targets(self, symbol: str, price: Decimal) -> None:
        sym = symbol.upper()
        for pos in [p for p in self._active_positions.values() if p.symbol == sym and p.target is not None]:
            hit = (pos.side == OrderSide.BUY and price >= pos.target) or (pos.side == OrderSide.SELL and price <= pos.target)
            if hit:
                log.info("Target hit for position #%s @ %s", pos.id, price)
                await self.close_position(pos, price, ExitReason.TARGET)

    # ── Unrealized PnL ──

    def calculate_unrealized_pnl(self, symbol: Optional[str] = None) -> List[Dict]:
        prices = market_data_streamer.get_all_market_prices()
        results = []
        for pos in self._active_positions.values():
            if symbol and pos.symbol != symbol.upper():
                continue
            raw = prices.get(pos.symbol)
            if raw is None:
                continue
            cur = Decimal(str(raw))
            if pos.side == OrderSide.BUY:
                pnl = (cur - pos.entry_price) * pos.quantity
            else:
                pnl = (pos.entry_price - cur) * pos.quantity
            results.append({
                "position_id": pos.id,
                "order_id": pos.order_id,
                "symbol": pos.symbol,
                "side": pos.side.value,
                "quantity": float(pos.quantity),
                "entry_price": float(pos.entry_price),
                "current_price": float(cur),
                "unrealized_pnl": round(float(pnl), 5),
                "target": float(pos.target) if pos.target else None,
                "stoploss": float(pos.stoploss) if pos.stoploss else None,
                "opened_at": str(pos.opened_at),
            })
        return results

    # ── Price update hook ──

    def check_on_price_update(self, price_dict: Dict[str, float]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        for sym, price in price_dict.items():
            loop.create_task(self.process_market_tick(sym.upper(), Decimal(str(price))))

    # ── Startup sync ──

    async def sync_from_database(self) -> None:
        with self._get_session() as s:
            for order in s.exec(select(Order).where(Order.status == OrderStatus.PENDING)).all():
                self.add_order(order)
            for pos in s.exec(select(Position)).all():
                self._active_positions[pos.id] = pos
            for port in s.exec(select(Portfolio)).all():
                self._portfolio_cash[port.id] = port.available_cash
        log.info("Synced from DB — %d pending orders, %d active positions", len(self.get_pending_orders()), len(self._active_positions))

    # ── Modify ──

    def modify_position_in_memory(self, position_id: int, target: Optional[Decimal] = None, stoploss: Optional[Decimal] = None) -> Position:
        pos = self._active_positions.get(position_id)
        if not pos:
            raise ValueError(f"Position #{position_id} not found in memory")
        if target is not None:
            pos.target = target
        if stoploss is not None:
            pos.stoploss = stoploss
        return pos


order_executor = OrderExecutor()
