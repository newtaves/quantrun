"""Portfolio management — CRUD, orders, PnL calculations."""

from decimal import Decimal
from typing import List, Optional

from sqlmodel import Session, select

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


class PortfolioManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Portfolio CRUD ──

    def create_portfolio(self, name: str, description: str = "", cash: Decimal = Decimal("10000")) -> Portfolio:
        p = Portfolio(name=name, description=description or None, available_cash=cash, user_id=1)
        self.session.add(p)
        self.session.commit()
        self.session.refresh(p)
        return p

    def get_portfolio(self, pid: int) -> Optional[Portfolio]:
        return self.session.get(Portfolio, pid)

    def list_portfolios(self, user_id: int = 1) -> List[Portfolio]:
        return list(self.session.exec(select(Portfolio).where(Portfolio.user_id == user_id)).all())

    def delete_portfolio(self, pid: int) -> None:
        port = self.session.get(Portfolio, pid)
        if not port:
            raise ValueError(f"Portfolio #{pid} not found")
        positions = list(self.session.exec(select(Position).where(Position.portfolio_id == pid)).all())
        if positions:
            raise ValueError("Cannot delete portfolio with active positions")
        pending = list(self.session.exec(select(Order).where(Order.portfolio_id == pid, Order.status == OrderStatus.PENDING)).all())
        if pending:
            raise ValueError("Cannot delete portfolio with pending orders")
        self.session.delete(port)
        self.session.commit()

    # ── Orders ──

    def place_order(self, order: Order) -> Order:
        port = self.session.get(Portfolio, order.portfolio_id)
        if not port:
            raise ValueError("Portfolio not found")
        order.quantity = Decimal(str(order.quantity))
        if order.limit_price is not None:
            order.limit_price = Decimal(str(order.limit_price))
        if order.target is not None:
            order.target = Decimal(str(order.target))
        if order.stoploss is not None:
            order.stoploss = Decimal(str(order.stoploss))
        if order.quantity <= 0:
            raise ValueError("Quantity must be > 0")

        if order.limit_price is not None:
            est_price = order.limit_price
        else:
            import asyncio
            price = asyncio.run(market_data_streamer.get_market_price(order.symbol))
            if price is None:
                raise ValueError(f"Cannot fetch market price for {order.symbol}")
            est_price = Decimal(str(price))

        est_cost = est_price * order.quantity
        if port.available_cash < est_cost:
            raise ValueError(f"Insufficient funds. Need {est_cost:.4f}, have {port.available_cash:.4f}")

        order.status = OrderStatus.PENDING
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def get_orders(self, portfolio_id: int, status: Optional[str] = None) -> List[Order]:
        if status:
            return list(self.session.exec(select(Order).where(Order.portfolio_id == portfolio_id, Order.status == status).order_by(Order.created_at.desc())).all())
        return list(self.session.exec(select(Order).where(Order.portfolio_id == portfolio_id).order_by(Order.created_at.desc())).all())

    def cancel_order(self, order_id: int) -> None:
        from quantrun.services.execution_engine import order_executor
        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be cancelled")
        order.status = OrderStatus.CANCELLED
        self.session.add(order)
        self.session.commit()
        mem = order_executor._order_registry.pop(order_id, None)
        if mem:
            order_executor.remove_order(mem)

    # ── Positions ──

    def get_positions(self, portfolio_id: int) -> List[Position]:
        return list(self.session.exec(select(Position).where(Position.portfolio_id == portfolio_id)).all())

    def close_position(self, position_id: int, reason: ExitReason = ExitReason.MANUAL) -> None:
        from quantrun.services.execution_engine import order_executor
        pos = self.session.get(Position, position_id)
        if not pos:
            raise ValueError(f"Position #{position_id} not found")
        import asyncio
        price = asyncio.run(market_data_streamer.get_market_price(pos.symbol))
        if price is None:
            raise ValueError(f"Cannot fetch market price for {pos.symbol}")
        mem = order_executor._active_positions.get(position_id, pos)
        asyncio.run(order_executor.close_position(mem, Decimal(str(price)), reason))

    def modify_position(self, position_id: int, target: Optional[Decimal] = None, stoploss: Optional[Decimal] = None) -> Position:
        from quantrun.services.execution_engine import order_executor
        pos = self.session.get(Position, position_id)
        if not pos:
            raise ValueError(f"Position #{position_id} not found")
        if target is not None:
            pos.target = Decimal(str(target))
        if stoploss is not None:
            pos.stoploss = Decimal(str(stoploss))
        self.session.add(pos)
        self.session.commit()
        self.session.refresh(pos)
        order_executor.modify_position_in_memory(position_id, pos.target, pos.stoploss)
        return pos

    def get_position_history(self, portfolio_id: int) -> List[PositionHistory]:
        return list(self.session.exec(select(PositionHistory).where(PositionHistory.portfolio_id == portfolio_id).order_by(PositionHistory.closed_at.desc())).all())

    # ── PnL ──

    def calculate_total_pnl(self, portfolio_id: int) -> dict:
        from quantrun.services.execution_engine import order_executor
        port = self.session.get(Portfolio, portfolio_id)
        positions = self.get_positions(portfolio_id)
        pos_ids = {p.id for p in positions}
        all_pnl = order_executor.calculate_unrealized_pnl()
        port_pnl = [r for r in all_pnl if r["position_id"] in pos_ids]
        unrealized = sum(Decimal(str(r["unrealized_pnl"])) for r in port_pnl)
        realized = port.total_pnl if port else Decimal("0")
        return {
            "total_pnl": round(unrealized + realized, 5),
            "unrealized_pnl": round(unrealized, 5),
            "realized_pnl": round(realized, 5),
            "positions": port_pnl,
        }
