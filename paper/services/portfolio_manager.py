from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

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


class PortfolioManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ─────────────────────────── Portfolio CRUD ──────────────────────────────

    async def create_portfolio(self, data: Portfolio) -> Portfolio:
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)
        return data

    async def get_portfolios(self, user_id: int) -> List[Portfolio]:
        statement = select(Portfolio).where(Portfolio.user_id == user_id)
        return list(self.session.exec(statement).all())

    async def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        return self.session.get(Portfolio, portfolio_id)

    async def delete_portfolio(self, portfolio_id: int) -> None:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return

        positions = self.session.exec(
            select(Position).where(Position.portfolio_id == portfolio_id)
        ).all()
        if positions:
            raise ValueError("Cannot delete portfolio with active positions")

        pending_orders = self.session.exec(
            select(Order).where(
                Order.portfolio_id == portfolio_id,
                Order.status == OrderStatus.PENDING,
            )
        ).all()
        if pending_orders:
            raise ValueError("Cannot delete portfolio with pending orders")

        self.session.delete(portfolio)
        self.session.commit()

    # ─────────────────────────── Positions ───────────────────────────────────

    async def get_positions(self, portfolio_id: int) -> List[Position]:
        statement = select(Position).where(Position.portfolio_id == portfolio_id)
        return list(self.session.exec(statement).all())

    async def get_position(self, position_id: int) -> Optional[Position]:
        return self.session.get(Position, position_id)

    async def get_position_summary(self, portfolio_id: int) -> dict:
        """Return a lightweight summary using in-memory executor state."""
        # Import here to avoid circular import at module level
        from paper.services.execution_engine import order_executor

        positions = await self.get_positions(portfolio_id)
        total_invested = sum(p.entry_price * p.quantity for p in positions)

        pnl_data = order_executor.calculate_unrealized_pnl()
        portfolio_pnl = [r for r in pnl_data if any(p.id == r["position_id"] for p in positions)]
        total_unrealized = sum(Decimal(str(r["unrealized_pnl"])) for r in portfolio_pnl)

        return {
            "total_positions": len(positions),
            "invested_capital": float(total_invested),
            "unrealized_pnl": float(total_unrealized),
            "exposure": float(total_invested),
        }

    async def get_available_cash(self, portfolio_id: int) -> Decimal:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return Decimal("0")
        return portfolio.available_cash

    async def get_invested_cash(self, portfolio_id: int) -> Decimal:
        positions = await self.get_positions(portfolio_id)
        return sum(p.entry_price * p.quantity for p in positions)

    # ─────────────────────────── PnL calculations ────────────────────────────

    async def calculate_total_pnl(self, portfolio_id: int) -> dict:
        unrealized = await self.calculate_unrealized_pnl(portfolio_id)
        realized = await self.calculate_realized_pnl(portfolio_id)
        return {
            "total_pnl": round(unrealized["total"] + realized, 5),
            "unrealized_pnl": round(unrealized["total"], 5),
            "realized_pnl": round(realized, 5),
            "positions": unrealized["positions"],
        }

    async def calculate_unrealized_pnl(self, portfolio_id: int) -> dict:
        """
        Calculate unrealized PnL from live prices.
        Nothing is persisted — current_price and unrealized_pnl are on-the-fly only.
        """
        from paper.services.execution_engine import order_executor

        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"total": Decimal("0"), "positions": []}

        positions = await self.get_positions(portfolio_id)
        position_ids = {p.id for p in positions}

        all_pnl = order_executor.calculate_unrealized_pnl()
        portfolio_pnl = [r for r in all_pnl if r["position_id"] in position_ids]

        total = sum(Decimal(str(r["unrealized_pnl"])) for r in portfolio_pnl)
        return {"total": round(total, 5), "positions": portfolio_pnl}

    async def calculate_realized_pnl(self, portfolio_id: int) -> Decimal:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return Decimal("0")
        return portfolio.total_pnl

    async def generate_pnl_report(self, portfolio_id: int) -> dict:
        total = await self.calculate_total_pnl(portfolio_id)
        portfolio = self.session.get(Portfolio, portfolio_id)

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name if portfolio else "Unknown",
            "total_pnl": total["total_pnl"],
            "unrealized_pnl": total["unrealized_pnl"],
            "realized_pnl": total["realized_pnl"],
            "available_cash": float(portfolio.available_cash) if portfolio else 0.0,
            "invested_cash": float(portfolio.invested_cash) if portfolio else 0.0,
            "positions": total["positions"],
        }

    # ─────────────────────────── Orders ──────────────────────────────────────

    async def place_order(self, order: Order) -> Order:
        """
        Validate and persist a new order as PENDING.

        Cash availability is checked here to give fast feedback to the caller.
        Actual cash deduction happens at execution time in OrderExecutor.
        """
        portfolio = self.session.get(Portfolio, order.portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")

        order.quantity = Decimal(str(order.quantity))
        if order.limit_price is not None:
            order.limit_price = Decimal(str(order.limit_price))
        if order.target is not None:
            order.target = Decimal(str(order.target))
        if order.stoploss is not None:
            order.stoploss = Decimal(str(order.stoploss))

        if order.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        if order.limit_price is not None and order.limit_price <= 0:
            raise ValueError("Limit price must be greater than 0")

        # Estimate execution cost for cash pre-check
        if order.limit_price is not None:
            estimated_price = order.limit_price
        else:
            price = await market_data_streamer.get_market_price(order.symbol)
            if price is None:
                raise ValueError(f"Unable to fetch market price for {order.symbol}")
            estimated_price = Decimal(str(price))

        estimated_cost = estimated_price * order.quantity

        # Both BUY and short SELL reserve collateral equal to estimated cost
        if portfolio.available_cash < estimated_cost:
            raise ValueError(
                f"Insufficient funds. Required: {estimated_cost:.4f}, "
                f"Available: {portfolio.available_cash:.4f}"
            )

        order.status = OrderStatus.PENDING
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    async def modify_order(
        self,
        order_id: int,
        limit_price: Optional[Decimal] = None,
        target: Optional[Decimal] = None,
        stoploss: Optional[Decimal] = None,
    ) -> Order:
        """
        Modify a pending order's price levels.
        Also updates the in-memory orderbook entry if present.
        """
        from paper.services.execution_engine import order_executor

        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be modified")

        if limit_price is not None:
            order.limit_price = limit_price
        if target is not None:
            order.target = target
        if stoploss is not None:
            order.stoploss = stoploss

        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)

        # Re-sort the in-memory orderbook entry with updated price
        mem_order = order_executor._order_registry.get(order_id)
        if mem_order:
            mem_order.limit_price = order.limit_price
            mem_order.target = order.target
            mem_order.stoploss = order.stoploss
            # Re-sort the bucket
            symbol = order.symbol.upper()
            if order.side.value == "BUY":
                bucket = order_executor._buy_orders.get(symbol, [])
                bucket.sort(key=order_executor._sort_key_buy)
            else:
                bucket = order_executor._sell_orders.get(symbol, [])
                bucket.sort(key=order_executor._sort_key_sell)

        return order

    async def cancel_order(self, order_id: int) -> None:
        """Cancel a pending order in both DB and in-memory orderbook."""
        from paper.services.execution_engine import order_executor

        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be cancelled")

        order.status = OrderStatus.CANCELLED
        self.session.add(order)
        self.session.commit()

        # Also remove from in-memory orderbook if present
        mem_order = order_executor._order_registry.pop(order_id, None)
        if mem_order:
            order_executor.remove_order(mem_order)

    async def close_position(
        self,
        position_id: int,
        exit_reason: ExitReason = ExitReason.MANUAL,
    ) -> None:
        """
        Manually close an open position at the current market price.

        Parameters:
        - position_id: ID of the position to close.
        - exit_reason: Defaults to MANUAL.
        """
        from paper.services.execution_engine import order_executor

        position = self.session.get(Position, position_id)
        if not position:
            raise ValueError(f"Position #{position_id} not found")

        price = await market_data_streamer.get_market_price(position.symbol)
        if price is None:
            raise ValueError(f"Unable to fetch market price for {position.symbol}")

        # Use in-memory cache if available (fresher), fallback to DB object
        mem_position = order_executor._active_positions.get(position_id, position)
        await order_executor.close_position(
            mem_position, Decimal(str(price)), exit_reason
        )

    async def modify_position(
        self,
        position_id: int,
        target: Optional[Decimal] = None,
        stoploss: Optional[Decimal] = None,
    ) -> Position:
        """
        Update an active position's stoploss and target in both DB and in-memory.
        """
        from paper.services.execution_engine import order_executor

        position = self.session.get(Position, position_id)
        if not position:
            raise ValueError(f"Position #{position_id} not found")

        if target is not None:
            position.target = Decimal(str(target))
        if stoploss is not None:
            position.stoploss = Decimal(str(stoploss))

        self.session.add(position)
        self.session.commit()
        self.session.refresh(position)

        # Update in-memory registry
        order_executor.modify_position(
            position_id, position.target, position.stoploss
        )

        return position

    # ─────────────────────────── Query helpers ───────────────────────────────

    async def get_orders(
        self, portfolio_id: int, status: Optional[str] = None
    ) -> List[Order]:
        if status:
            statement = (
                select(Order)
                .where(Order.portfolio_id == portfolio_id, Order.status == status)
                .order_by(Order.created_at.desc())
            )
        else:
            statement = (
                select(Order)
                .where(Order.portfolio_id == portfolio_id)
                .order_by(Order.created_at.desc())
            )
        return list(self.session.exec(statement).all())

    async def get_order(self, order_id: int) -> Optional[Order]:
        return self.session.get(Order, order_id)

    async def get_pending_orders(self, portfolio_id: int) -> List[Order]:
        return await self.get_orders(portfolio_id, status=OrderStatus.PENDING.value)

    async def get_executed_orders(self, portfolio_id: int) -> List[Order]:
        return await self.get_orders(portfolio_id, status=OrderStatus.EXECUTED.value)

    async def get_position_history(self, portfolio_id: int) -> List[PositionHistory]:
        """Return all closed trade records for a portfolio (analytics)."""
        statement = (
            select(PositionHistory)
            .where(PositionHistory.portfolio_id == portfolio_id)
            .order_by(PositionHistory.closed_at.desc())
        )
        return list(self.session.exec(statement).all())

    async def update_portfolio_metrics(self, portfolio_id: int) -> None:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return

        invested = await self.get_invested_cash(portfolio_id)
        portfolio.invested_cash = invested
        self.session.add(portfolio)
        self.session.commit()
