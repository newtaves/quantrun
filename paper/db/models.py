from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import Column, Text

from sqlmodel import SQLModel, Field


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    executed_at: Optional[datetime] = Field(default=None)
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", index=True)


class Portfolio(SQLModel, table=True):
    __tablename__: str = "dashboard_portfolio"
    id: Optional[int] = Field(default=None, primary_key=True)
    # Kept only for compatibility with existing SQLite files. Authentication
    # has been removed; every local portfolio belongs to the single workspace.
    user_id: int = Field(default=1, index=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None)
    available_cash: Decimal = Field(default=Decimal("0"))
    invested_cash: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Position(SQLModel, table=True):
    """
    Represents a single open trade ticket.
    current_price and unrealized_pnl are NOT stored — calculated on the fly.
    Each executed order creates one distinct Position (no averaging).
    """
    __tablename__: str = "dashboard_position"
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", index=True)
    order_id: int = Field(foreign_key="dashboard_order.id", index=True)
    symbol: str = Field(index=True)
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    target: Optional[Decimal] = Field(default=None)
    stoploss: Optional[Decimal] = Field(default=None)
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PositionHistory(SQLModel, table=True):
    """
    Permanent archive of every closed trade for analytics.
    Stores entry/exit prices, timestamps, PnL, and the reason for closure.
    """
    __tablename__: str = "dashboard_positionhistory"
    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", index=True)
    order_id: int = Field(foreign_key="dashboard_order.id", index=True)
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


class Agent(SQLModel, table=True):
    __tablename__: str = "agent"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    strategy: str = Field(default="balanced", max_length=100)
    system_prompt: Optional[str] = None
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", unique=True, index=True)
    initial_capital: Decimal = Field(default=Decimal("0"))
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentRun(SQLModel, table=True):
    __tablename__: str = "agent_run"
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    completed_at: Optional[datetime] = None
    status: str = Field(default="RUNNING", max_length=20)
    summary: Optional[str] = None
    error: Optional[str] = None


class AgentActivity(SQLModel, table=True):
    __tablename__: str = "agent_activity"
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    run_id: Optional[int] = Field(default=None, foreign_key="agent_run.id", index=True)
    kind: str = Field(max_length=30, index=True)
    name: str = Field(max_length=100, index=True)
    input_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    output_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    success: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class AgentNote(SQLModel, table=True):
    __tablename__: str = "agent_note"
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    portfolio_id: int = Field(foreign_key="dashboard_portfolio.id", index=True)
    symbol: Optional[str] = Field(default=None, max_length=30, index=True)
    category: str = Field(default="lesson", max_length=30)
    content: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class AgentEquitySnapshot(SQLModel, table=True):
    __tablename__: str = "agent_equity_snapshot"
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    equity: Decimal
    available_cash: Decimal
    invested_cash: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
