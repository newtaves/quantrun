from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class Order(SQLModel, table=True):
    __tablename__: str = "dashboard_order"
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, max_length=30)
    side: OrderSide
    quantity: Decimal
    limit_price: Optional[Decimal] = Field(default=None)
    executed_price: Optional[Decimal] = Field(default=None)
    target: Optional[Decimal] = Field(default=None)
    stoploss: Optional[Decimal] = Field(default=None)
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=datetime.now(UTC))
    executed_at: Optional[datetime] = Field(default=None)
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", index=True)


class Portfolio(SQLModel, table=True):
    __tablename__: str = "dashboard_portfolio"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="auth_user.id")
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None)
    available_cash: Decimal = Field(default=Decimal("0"))
    invested_cash: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))
    created_at: datetime = Field(default_factory=datetime.now(UTC))


class Position(SQLModel, table=True):
    __tablename__: str = "dashboard_position"
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", index=True)
    symbol: str = Field(index=True)
    side: OrderSide
    quantity: Decimal
    average_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal = Field(default=Decimal("0"))
    target: Optional[Decimal] = Field(default=None)
    stoploss: Optional[Decimal] = Field(default=None)
    opened_at: datetime = Field(default_factory=datetime.now(UTC))