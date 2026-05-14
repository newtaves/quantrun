from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from paper.db.models import Order, OrderSide, OrderStatus, Portfolio, Position
from paper.services.market_data import market_data_streamer


class PortfolioManager:
    def __init__(self, session: Session) -> None:
        self.session = session

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

    async def get_positions(self, portfolio_id: int) -> List[Position]:
        statement = select(Position).where(Position.portfolio_id == portfolio_id)
        return list(self.session.exec(statement).all())

    async def get_position(self, position_id: int) -> Optional[Position]:
        return self.session.get(Position, position_id)

    async def get_position_summary(self, portfolio_id: int) -> dict:
        positions = await self.get_positions(portfolio_id)
        total_invested = sum(
            p.average_price * p.quantity for p in positions
        )
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        return {
            "total_positions": len(positions),
            "invested_capital": float(total_invested),
            "unrealized_pnl": float(total_unrealized_pnl),
            "exposure": float(total_invested),
        }

    async def get_available_cash(self, portfolio_id: int) -> Decimal:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return Decimal("0")
        return portfolio.available_cash

    async def get_invested_cash(self, portfolio_id: int) -> Decimal:
        positions = await self.get_positions(portfolio_id)
        return sum(p.average_price * p.quantity for p in positions)

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
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return {"total": Decimal("0"), "positions": []}

        prices = market_data_streamer.get_all_market_prices()
        positions = await self.get_positions(portfolio_id)

        total = Decimal("0")
        position_pnls = []
        for pos in positions:
            raw_price = prices.get(pos.symbol)
            if raw_price is not None:
                current_price = Decimal(str(raw_price))
                if pos.side == OrderSide.BUY:
                    pnl = (current_price - pos.average_price) * pos.quantity
                else:
                    pnl = (pos.average_price - current_price) * pos.quantity
                total += pnl
                position_pnls.append({
                    "position_id": pos.id,
                    "symbol": pos.symbol,
                    "side": pos.side.value,
                    "quantity": float(pos.quantity),
                    "average_price": float(pos.average_price),
                    "current_price": float(current_price),
                    "unrealized_pnl": round(float(pnl), 5),
                })
                pos.current_price = current_price
                pos.unrealized_pnl = pnl

        self.session.commit()
        return {"total": round(total, 5), "positions": position_pnls}

    async def calculate_realized_pnl(self, portfolio_id: int) -> Decimal:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return Decimal("0")
        return portfolio.total_pnl

    async def generate_pnl_report(self, portfolio_id: int) -> dict:
        total = await self.calculate_total_pnl(portfolio_id)
        unrealized_details = await self.calculate_unrealized_pnl(portfolio_id)
        portfolio = self.session.get(Portfolio, portfolio_id)

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name if portfolio else "Unknown",
            "total_pnl": total["total_pnl"],
            "unrealized_pnl": total["unrealized_pnl"],
            "realized_pnl": total["realized_pnl"],
            "available_cash": float(portfolio.available_cash) if portfolio else 0.0,
            "invested_cash": float(portfolio.invested_cash) if portfolio else 0.0,
            "positions": unrealized_details["positions"],
        }

    async def place_order(self, order: Order) -> Order:
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

        if order.limit_price is not None:
            estimated_price = order.limit_price
        else:
            price = await market_data_streamer.get_market_price(order.symbol)
            if price is None:
                raise ValueError(f"Unable to fetch market price for {order.symbol}")
            estimated_price = Decimal(str(price))

        estimated_cost = estimated_price * order.quantity

        if order.side == OrderSide.BUY and portfolio.available_cash < estimated_cost:
            raise ValueError(
                f"Insufficient funds. Required: {estimated_cost}, "
                f"Available: {portfolio.available_cash}"
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
        return order

    async def cancel_order(self, order_id: int) -> None:
        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be cancelled")

        order.status = OrderStatus.CANCELLED
        self.session.add(order)
        self.session.commit()

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

    async def update_portfolio_metrics(self, portfolio_id: int) -> None:
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            return

        invested = await self.get_invested_cash(portfolio_id)
        portfolio.invested_cash = invested

        pnl_data = await self.calculate_unrealized_pnl(portfolio_id)

        self.session.add(portfolio)
        self.session.commit()
