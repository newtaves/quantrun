from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class ExitReason(str, Enum):
    STOPLOSS = "STOPLOSS"
    TARGET = "TARGET"
    MANUAL = "MANUAL"


class Order(SQLModel, table=True):
    __tablename__: str = "order"
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, max_length=30)
    side: OrderSide
    quantity: Decimal
    limit_price: Optional[Decimal] = Field(default=None)
    executed_price: Optional[Decimal] = Field(default=None)
    target: Optional[Decimal] = Field(default=None)
    stoploss: Optional[Decimal] = Field(default=None)
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    executed_at: Optional[datetime] = Field(default=None)
    portfolio_id: int = Field(foreign_key="portfolio.id", index=True)


class Portfolio(SQLModel, table=True):
    __tablename__: str = "portfolio"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, default=1)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None)
    available_cash: Decimal = Field(default=Decimal("0"))
    invested_cash: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Position(SQLModel, table=True):
    """Open trade ticket. current_price and unrealized_pnl are calculated on the fly."""

    __tablename__: str = "position"
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolio.id", index=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    symbol: str = Field(index=True)
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    target: Optional[Decimal] = Field(default=None)
    stoploss: Optional[Decimal] = Field(default=None)
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PositionHistory(SQLModel, table=True):
    """Archive of every closed trade for analytics."""

    __tablename__: str = "position_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolio.id", index=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    symbol: str = Field(index=True)
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    realized_pnl: Decimal
    target: Optional[Decimal] = Field(default=None)
    stoploss: Optional[Decimal] = Field(default=None)
    exit_reason: ExitReason
    opened_at: datetime
    closed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
