from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from paper.db.models import Agent, AgentEquitySnapshot, PositionHistory


def agent_metrics(session: Session, agent: Agent) -> dict[str, Any]:
    trades = session.exec(
        select(PositionHistory).where(PositionHistory.portfolio_id == agent.portfolio_id).order_by(PositionHistory.closed_at)
    ).all()
    snapshots = session.exec(
        select(AgentEquitySnapshot).where(AgentEquitySnapshot.agent_id == agent.id).order_by(AgentEquitySnapshot.timestamp)
    ).all()
    values = [float(snapshot.equity) for snapshot in snapshots]
    returns = [(values[index] / values[index - 1]) - 1 for index in range(1, len(values)) if values[index - 1]]
    mean = sum(returns) / len(returns) if returns else 0.0
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1) if len(returns) > 1 else 0.0
    sharpe = (mean / math.sqrt(variance)) * math.sqrt(24 * 365) if variance > 0 else 0.0

    peak = None
    max_drawdown = 0.0
    for value in values:
        peak = value if peak is None else max(peak, value)
        if peak:
            max_drawdown = max(max_drawdown, (peak - value) / peak)

    realized = sum(float(trade.realized_pnl) for trade in trades)
    unrealized = float(snapshots[-1].unrealized_pnl) if snapshots else 0.0
    equity = values[-1] if values else float(agent.initial_capital)
    profits = [float(trade.realized_pnl) for trade in trades]
    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "strategy": agent.strategy,
        "portfolio_id": agent.portfolio_id,
        "active": agent.active,
        "equity": round(equity, 4),
        "realized_pnl": round(realized, 4),
        "unrealized_pnl": round(unrealized, 4),
        "total_pnl": round(realized + unrealized, 4),
        "trade_count": len(trades),
        "winning_trades": sum(1 for profit in profits if profit > 0),
        "win_rate": round((sum(1 for profit in profits if profit > 0) / len(profits)) * 100, 2) if profits else 0.0,
        "max_profit": round(max(profits), 4) if profits else 0.0,
        "max_loss": round(min(profits), 4) if profits else 0.0,
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_drawdown * 100, 4),
        "snapshot_count": len(snapshots),
    }


def equity_series(session: Session, agent_id: int) -> list[dict[str, Any]]:
    snapshots = session.exec(
        select(AgentEquitySnapshot).where(AgentEquitySnapshot.agent_id == agent_id).order_by(AgentEquitySnapshot.timestamp)
    ).all()
    return [{
        "timestamp": snapshot.timestamp.isoformat(),
        "equity": float(snapshot.equity),
        "pnl": float(snapshot.realized_pnl + snapshot.unrealized_pnl),
        "realized_pnl": float(snapshot.realized_pnl),
        "unrealized_pnl": float(snapshot.unrealized_pnl),
    } for snapshot in snapshots]
