import asyncio
import logging
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from paper.db.database import engine
from paper.db.models import (
    ExitReason,
    Order,
    OrderSide,
    OrderStatus,
    Portfolio,
    Position,
    PositionHistory,
)
from paper.services.market_data import market_data_streamer


class OrderExecutor:
    """
    Core in-memory execution engine for paper trading.

    Responsibilities:
    - Maintain per-symbol orderbooks (buy / sell) in memory, sorted for fast matching.
    - Execute market orders immediately and limit orders when price conditions are met.
    - Support BUY (long), SELL (short sell), and position closure.
    - Track stoploss and target for every open position and auto-close on hit.
    - Keep an in-memory portfolio cash mirror to avoid DB reads on every tick.
    - Archive every closed trade to PositionHistory for analytics.
    - Minimise DB writes: only write on order execution, position open/close.

    Order execution rules:
    - BUY  limit: execute when market_price <= limit_price  (buying cheaper or at limit)
    - SELL limit: execute when market_price >= limit_price  (selling at or above target entry)
    - Market order (limit_price is None): execute at current market price immediately.

    Position closure rules:
    - LONG  stoploss: close when market_price <= stoploss
    - LONG  target  : close when market_price >= target
    - SHORT stoploss: close when market_price >= stoploss
    - SHORT target  : close when market_price <= target

    Cash accounting:
    - On execution  : deduct (entry_price * quantity) from available_cash
    - On closure    : return  entry_price * quantity + realized_pnl  to available_cash
    - Short sells use the same collateral model (entry value is reserved).
    """

    def __init__(self) -> None:
        """
        Initialise all in-memory registries.

        _buy_orders  : symbol -> List[Order] sorted ascending  by limit_price
                       (market orders — limit_price is None — come first)
        _sell_orders : symbol -> List[Order] sorted descending by limit_price
                       (market orders come first)
        _active_positions : position_id -> Position
        _order_registry   : order_id    -> Order  (for O(1) cancel / lookup)
        _portfolio_cash   : portfolio_id -> Decimal  (mirrors DB available_cash)
        _lock             : asyncio.Lock protecting shared state during tick processing
        """
        self._buy_orders: Dict[str, List[Order]] = {}
        self._sell_orders: Dict[str, List[Order]] = {}
        self._active_positions: Dict[int, Position] = {}
        self._order_registry: Dict[int, Order] = {}
        self._portfolio_cash: Dict[int, Decimal] = {}
        self._lock = asyncio.Lock()

    # ─────────────────────────── DB session helper ───────────────────────────

    def _get_session(self) -> Session:
        """Return a new SQLModel Session bound to the shared engine."""
        return Session(engine)

    # ──────────────────────────── Orderbook management ───────────────────────

    def _sort_key_buy(self, order: Order):
        """Sort buy orders: market (None) first, then ascending limit_price."""
        if order.limit_price is None:
            return (0, Decimal("0"))
        return (1, order.limit_price)

    def _sort_key_sell(self, order: Order):
        """Sort sell orders: market (None) first, then descending limit_price."""
        if order.limit_price is None:
            return (0, Decimal("0"))
        return (1, -order.limit_price)

    def add_order(self, order: Order) -> None:
        """
        Add a new order into the in-memory orderbook.

        Buy  orders are sorted ascending  by limit_price (execute at lowest).
        Sell orders are sorted descending by limit_price (execute at highest).
        Market orders (limit_price=None) are placed first in both lists.

        Parameters:
        - order: An Order with status=PENDING that has already been saved to DB.
        """
        symbol = order.symbol.upper()

        if order.side == OrderSide.BUY:
            bucket = self._buy_orders.setdefault(symbol, [])
            bucket.append(order)
            bucket.sort(key=self._sort_key_buy)
        else:
            bucket = self._sell_orders.setdefault(symbol, [])
            bucket.append(order)
            bucket.sort(key=self._sort_key_sell)

        if order.id is not None:
            self._order_registry[order.id] = order

        logging.info(
            f"[OrderBook] Added {order.side.value} order #{order.id} "
            f"{order.symbol} qty={order.quantity} limit={order.limit_price}"
        )

    def remove_order(self, order: Order) -> None:
        """
        Remove an order from the in-memory orderbook.

        Called internally after execution, cancellation, or rejection.

        Parameters:
        - order: The Order object to remove.
        """
        symbol = order.symbol.upper()

        if order.side == OrderSide.BUY:
            bucket = self._buy_orders.get(symbol, [])
        else:
            bucket = self._sell_orders.get(symbol, [])

        try:
            bucket.remove(order)
        except ValueError:
            pass  # Already removed — safe to ignore

        if order.id is not None:
            self._order_registry.pop(order.id, None)

    def cancel_order(self, order_id: int) -> None:
        """
        Cancel a pending order: remove from orderbook and mark CANCELLED in DB.

        Parameters:
        - order_id: ID of the order to cancel.

        Raises:
        - ValueError: if the order is not found in the in-memory registry.
        """
        order = self._order_registry.get(order_id)
        if not order:
            raise ValueError(f"Order #{order_id} not found in orderbook")

        self.remove_order(order)

        with self._get_session() as session:
            db_order = session.get(Order, order_id)
            if db_order and db_order.status == OrderStatus.PENDING:
                db_order.status = OrderStatus.CANCELLED
                session.add(db_order)
                session.commit()

        logging.info(f"[OrderBook] Cancelled order #{order_id}")

    def get_buy_orders(self, symbol: str) -> List[Order]:
        """
        Return all pending BUY orders for a symbol (copy of internal list).

        Parameters:
        - symbol: Trading symbol (case-insensitive).
        """
        return list(self._buy_orders.get(symbol.upper(), []))

    def get_sell_orders(self, symbol: str) -> List[Order]:
        """
        Return all pending SELL orders for a symbol (copy of internal list).

        Parameters:
        - symbol: Trading symbol (case-insensitive).
        """
        return list(self._sell_orders.get(symbol.upper(), []))

    def get_pending_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Return all pending orders, optionally filtered by symbol.

        Parameters:
        - symbol: Optional trading symbol filter.
        """
        if symbol:
            return self.get_buy_orders(symbol) + self.get_sell_orders(symbol)

        all_orders: List[Order] = []
        for bucket in self._buy_orders.values():
            all_orders.extend(bucket)
        for bucket in self._sell_orders.values():
            all_orders.extend(bucket)
        return all_orders

    # ───────────────────────── Market tick processing ────────────────────────

    async def process_market_tick(self, symbol: str, current_price: Decimal) -> None:
        """
        Main event handler triggered whenever a new market price arrives.

        Acquires the internal lock, then:
        1. Attempts to execute pending limit / market orders for the symbol.
        2. Checks stoploss levels for all open positions on this symbol.
        3. Checks target levels for all open positions on this symbol.

        Parameters:
        - symbol: Trading symbol (e.g. "BTCUSDT").
        - current_price: Latest mid-price from market data feed.
        """
        async with self._lock:
            await self.execute_limit_orders(symbol, current_price)
            await self.check_stoploss(symbol, current_price)
            await self.check_targets(symbol, current_price)

    async def execute_limit_orders(self, symbol: str, current_price: Decimal) -> None:
        """
        Check and execute all pending orders whose price condition is satisfied.

        BUY  : execute when current_price <= limit_price  (or market order)
        SELL : execute when current_price >= limit_price  (or market order)

        Parameters:
        - symbol: Trading symbol.
        - current_price: Latest market price.
        """
        symbol = symbol.upper()

        # Snapshot both lists before iterating (execute_order mutates them)
        buy_orders = list(self._buy_orders.get(symbol, []))
        for order in buy_orders:
            if order.limit_price is None or current_price <= order.limit_price:
                await self.execute_order(order, current_price)

        sell_orders = list(self._sell_orders.get(symbol, []))
        for order in sell_orders:
            if order.limit_price is None or current_price >= order.limit_price:
                await self.execute_order(order, current_price)

    # ────────────────────────── Order execution ──────────────────────────────

    async def execute_order(self, order: Order, execution_price: Decimal) -> Optional[Position]:
        """
        Execute a single order at the given price.

        Responsibilities:
        - Verify sufficient available cash (both BUY and short SELL require collateral).
        - Deduct cost from in-memory cash mirror.
        - Create a new Position in the DB (ticket-based: never averaged).
        - Mark the Order as EXECUTED in the DB.
        - Deduct cash and update invested_cash in the Portfolio DB row.
        - Remove the order from the orderbook.

        Parameters:
        - order: The pending Order to fill.
        - execution_price: Price at which the order is filled.

        Returns:
        - The newly created Position, or None if execution was rejected.
        """
        portfolio_id = order.portfolio_id
        cost = execution_price * order.quantity

        # ── Cash check ──────────────────────────────────────────────────────
        available = self._portfolio_cash.get(portfolio_id)
        if available is None:
            # First execution for this portfolio — prime the cache from DB
            with self._get_session() as session:
                portfolio = session.get(Portfolio, portfolio_id)
                if not portfolio:
                    logging.error(
                        f"[Execution] Portfolio #{portfolio_id} not found "
                        f"for order #{order.id}. Rejecting."
                    )
                    return None
                available = portfolio.available_cash
                self._portfolio_cash[portfolio_id] = available

        if available < cost:
            logging.warning(
                f"[Execution] Insufficient cash for order #{order.id} "
                f"({order.side.value} {order.quantity} {order.symbol} @ {execution_price}). "
                f"Required: {cost:.4f}, Available: {available:.4f}. Skipping."
            )
            return None

        # ── Deduct cash in-memory immediately ───────────────────────────────
        self._portfolio_cash[portfolio_id] = available - cost

        # ── Create position + persist ────────────────────────────────────────
        position = await self.create_position(order, execution_price)
        return position

    async def create_position(self, order: Order, execution_price: Decimal) -> Position:
        """
        Persist a new Position and mark the Order as EXECUTED in a single DB write.

        Also deducts cash from the Portfolio row and increments invested_cash.
        The position is then cached in _active_positions.

        Parameters:
        - order: The executed Order.
        - execution_price: Fill price.

        Returns:
        - The newly created and persisted Position.
        """
        now = datetime.now(UTC)
        cost = execution_price * order.quantity

        position = Position(
            portfolio_id=order.portfolio_id,
            order_id=order.id,
            symbol=order.symbol.upper(),
            side=order.side,
            quantity=order.quantity,
            entry_price=execution_price,
            target=order.target,
            stoploss=order.stoploss,
            opened_at=now,
        )

        with self._get_session() as session:
            # 1. Mark order executed
            db_order = session.get(Order, order.id)
            if db_order:
                db_order.status = OrderStatus.EXECUTED
                db_order.executed_price = execution_price
                db_order.executed_at = now
                session.add(db_order)

            # 2. Update portfolio cash
            portfolio = session.get(Portfolio, order.portfolio_id)
            if portfolio:
                portfolio.available_cash -= cost
                portfolio.invested_cash += cost
                session.add(portfolio)

            # 3. Save position
            session.add(position)
            session.commit()
            session.refresh(position)

        # Remove from orderbook AFTER successful DB write
        self.remove_order(order)

        # Cache active position
        self._active_positions[position.id] = position

        logging.info(
            f"[Execution] ✅ Order #{order.id} EXECUTED → "
            f"Position #{position.id} | {position.side.value} "
            f"{position.quantity} {position.symbol} @ {execution_price}"
        )
        return position

    def modify_position(
        self,
        position_id: int,
        target: Optional[Decimal] = None,
        stoploss: Optional[Decimal] = None,
    ) -> Position:
        """
        Update the target and/or stoploss of an active in-memory position.

        Parameters:
        - position_id: ID of the active position.
        - target: New target price (optional).
        - stoploss: New stoploss price (optional).
        """
        position = self._active_positions.get(position_id)
        if not position:
            raise ValueError(f"Active position #{position_id} not found in memory")

        if target is not None:
            position.target = target
        if stoploss is not None:
            position.stoploss = stoploss

        logging.info(
            f"[Execution] Updated Position #{position_id} | "
            f"TGT={position.target} | SL={position.stoploss}"
        )
        return position

    async def update_position(
        self, position: Position, quantity: Decimal, execution_price: Decimal
    ) -> Position:
        """
        Not used in the ticket-based system (each order = its own position).
        Kept for API compatibility. Returns the unchanged position.
        """
        logging.warning(
            "[OrderExecutor] update_position called but ticket-based mode is active. "
            "Each order creates its own position — no averaging applied."
        )
        return position

    # ────────────────────────── Position closure ─────────────────────────────

    async def close_position(
        self,
        position: Position,
        exit_price: Decimal,
        exit_reason: ExitReason = ExitReason.MANUAL,
    ) -> None:
        """
        Close an active position: calculate PnL, return cash, archive to history.

        Cash accounting:
        - Entry cost = average_price * quantity  (was deducted on open)
        - Realized PnL = (exit - entry) * qty  for LONG
                       = (entry - exit) * qty  for SHORT
        - Cash returned = entry_cost + realized_pnl

        Parameters:
        - position: The active Position to close.
        - exit_price: Market price at which the position is closed.
        - exit_reason: STOPLOSS | TARGET | MANUAL.
        """
        if position.side == OrderSide.BUY:
            realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:  # SHORT SELL
            realized_pnl = (position.entry_price - exit_price) * position.quantity

        entry_cost = position.entry_price * position.quantity
        cash_returned = entry_cost + realized_pnl

        portfolio_id = position.portfolio_id

        # ── Update in-memory cash mirror ─────────────────────────────────────
        self._portfolio_cash[portfolio_id] = (
            self._portfolio_cash.get(portfolio_id, Decimal("0")) + cash_returned
        )

        with self._get_session() as session:
            # 1. Update portfolio
            portfolio = session.get(Portfolio, portfolio_id)
            if portfolio:
                portfolio.available_cash += cash_returned
                portfolio.invested_cash = max(
                    Decimal("0"), portfolio.invested_cash - entry_cost
                )
                portfolio.total_pnl += realized_pnl
                session.add(portfolio)

            # 2. Archive to PositionHistory
            history = PositionHistory(
                portfolio_id=position.portfolio_id,
                order_id=position.order_id,
                symbol=position.symbol,
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=exit_price,
                realized_pnl=realized_pnl,
                target=position.target,
                stoploss=position.stoploss,
                exit_reason=exit_reason,
                opened_at=position.opened_at,
                closed_at=datetime.now(UTC),
            )
            session.add(history)

            # 3. Delete the active position row
            db_position = session.get(Position, position.id)
            if db_position:
                session.delete(db_position)

            session.commit()

        # Remove from in-memory cache
        self._active_positions.pop(position.id, None)

        logging.info(
            f"[Execution] 🔒 Position #{position.id} closed | "
            f"{position.symbol} {position.side.value} | "
            f"Exit: {exit_price} | PnL: {realized_pnl:.4f} | Reason: {exit_reason.value}"
        )

    # ───────────────────────── Stoploss / Target checks ─────────────────────

    async def check_stoploss(self, symbol: str, current_price: Decimal) -> None:
        """
        Close any open positions whose stoploss level has been breached.

        LONG  stoploss: triggered when current_price <= stoploss
        SHORT stoploss: triggered when current_price >= stoploss

        Parameters:
        - symbol: Trading symbol to check.
        - current_price: Latest market price.
        """
        symbol = symbol.upper()
        positions = [
            p for p in self._active_positions.values()
            if p.symbol == symbol and p.stoploss is not None
        ]

        for position in positions:
            hit = False
            if position.side == OrderSide.BUY and current_price <= position.stoploss:
                hit = True
            elif position.side == OrderSide.SELL and current_price >= position.stoploss:
                hit = True

            if hit:
                logging.info(
                    f"[SL] 🛑 Stoploss hit for position #{position.id} "
                    f"{position.symbol} @ {current_price} (SL={position.stoploss})"
                )
                await self.close_position(position, current_price, ExitReason.STOPLOSS)

    async def check_targets(self, symbol: str, current_price: Decimal) -> None:
        """
        Close any open positions whose target level has been reached.

        LONG  target: triggered when current_price >= target
        SHORT target: triggered when current_price <= target

        Parameters:
        - symbol: Trading symbol to check.
        - current_price: Latest market price.
        """
        symbol = symbol.upper()
        positions = [
            p for p in self._active_positions.values()
            if p.symbol == symbol and p.target is not None
        ]

        for position in positions:
            hit = False
            if position.side == OrderSide.BUY and current_price >= position.target:
                hit = True
            elif position.side == OrderSide.SELL and current_price <= position.target:
                hit = True

            if hit:
                logging.info(
                    f"[TGT] 🎯 Target hit for position #{position.id} "
                    f"{position.symbol} @ {current_price} (TGT={position.target})"
                )
                await self.close_position(position, current_price, ExitReason.TARGET)

    # ────────────────────────── Unrealized PnL ───────────────────────────────

    def calculate_unrealized_pnl(
        self, symbol: Optional[str] = None
    ) -> List[Dict]:
        """
        Calculate unrealized PnL on the fly from in-memory positions.
        Nothing is written to the database.

        Parameters:
        - symbol: Optional filter. If None, calculates for all positions.

        Returns:
        - List of dicts with position_id, symbol, side, qty, entry, current, pnl.
        """
        prices = market_data_streamer.get_all_market_prices()
        results = []

        for pos in self._active_positions.values():
            if symbol and pos.symbol != symbol.upper():
                continue

            raw = prices.get(pos.symbol)
            if raw is None:
                continue

            current_price = Decimal(str(raw))
            if pos.side == OrderSide.BUY:
                pnl = (current_price - pos.entry_price) * pos.quantity
            else:
                pnl = (pos.entry_price - current_price) * pos.quantity

            results.append({
                "position_id": pos.id,
                "order_id": pos.order_id,
                "symbol": pos.symbol,
                "side": pos.side.value,
                "quantity": float(pos.quantity),
                "entry_price": float(pos.entry_price),
                "current_price": float(current_price),
                "unrealized_pnl": round(float(pnl), 5),
                "target": float(pos.target) if pos.target else None,
                "stoploss": float(pos.stoploss) if pos.stoploss else None,
                "opened_at": str(pos.opened_at),
            })

        return results

    # ────────────────────── Price update hook (called by streamer) ───────────

    def check_on_price_update(self, price_dict: Dict[str, float]) -> None:
        """
        Entry point called by market_data_streamer whenever prices update.

        For each symbol in the update, schedules an async process_market_tick
        on the running event loop. This keeps the price-handler (sync) decoupled
        from the async execution logic.

        Usage in market_data_streamer._process_message:
            from paper.services.execution_engine import order_executor
            order_executor.check_on_price_update({symbol: price})

        Parameters:
        - price_dict: Dict mapping symbol -> latest float price.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # No event loop running (e.g. during tests/startup)

        for symbol, price in price_dict.items():
            decimal_price = Decimal(str(price))
            loop.create_task(
                self.process_market_tick(symbol.upper(), decimal_price)
            )

    # ─────────────────────────── DB Sync (startup) ───────────────────────────

    async def sync_from_database(self) -> None:
        """
        Load pending orders and active positions from the database into memory.

        Called once at application startup so that the engine picks up any
        state that persisted across restarts.
        """
        with self._get_session() as session:
            # Pending orders → orderbook
            pending_orders = session.exec(
                select(Order).where(Order.status == OrderStatus.PENDING)
            ).all()
            for order in pending_orders:
                self.add_order(order)

            # Active positions → position cache
            positions = session.exec(select(Position)).all()
            for position in positions:
                self._active_positions[position.id] = position

            # Portfolio cash → cash cache
            portfolios = session.exec(select(Portfolio)).all()
            for portfolio in portfolios:
                self._portfolio_cash[portfolio.id] = portfolio.available_cash

        logging.info(
            f"[OrderExecutor] Synced from DB — "
            f"{len(self.get_pending_orders())} pending orders | "
            f"{len(self._active_positions)} active positions"
        )


# ── Module-level singleton ────────────────────────────────────────────────────
order_executor = OrderExecutor()