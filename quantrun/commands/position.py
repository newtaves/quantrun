"""Position management commands."""

import click
from decimal import Decimal
from quantrun.db import get_session, init_db
from quantrun.db.models import ExitReason
from quantrun.services.portfolio_manager import PortfolioManager


@click.group()
def position():
    """Manage open positions."""
    pass


@position.command("list")
@click.option("--portfolio", "-p", "portfolio_id", required=True, type=int, help="Portfolio ID")
def list_positions(portfolio_id):
    """List open positions with live PnL."""
    init_db()
    session = get_session()
    try:
        from quantrun.services.execution_engine import order_executor
        positions = PortfolioManager(session).get_positions(portfolio_id)
        if not positions:
            click.echo("No open positions.")
            return
        all_pnl = order_executor.calculate_unrealized_pnl()
        pos_map = {r["position_id"]: r for r in all_pnl}
        for p in positions:
            live = pos_map.get(p.id)
            if live:
                click.echo(f"  #{p.id}  {p.side.value:<4} {p.quantity} {p.symbol:<10} entry={live['entry_price']:<12} current={live['current_price']:<12} pnl={live['unrealized_pnl']}")
            else:
                click.echo(f"  #{p.id}  {p.side.value:<4} {p.quantity} {p.symbol:<10} entry={p.entry_price}  (no live price)")
    finally:
        session.close()


@position.command("close")
@click.argument("position_id", type=int)
@click.option("--reason", "-r", default="MANUAL", type=click.Choice(["MANUAL", "STOPLOSS", "TARGET"], case_sensitive=False), help="Exit reason")
def close_position(position_id, reason):
    """Close an open position at current market price."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        mgr.close_position(position_id, ExitReason(reason.upper()))
        click.echo(f"Position #{position_id} closed ({reason}).")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        session.close()


@position.command("modify")
@click.argument("position_id", type=int)
@click.option("--target", "-t", type=float, default=None, help="New take-profit target")
@click.option("--stoploss", "--sl", type=float, default=None, help="New stop-loss price")
def modify_position(position_id, target, stoploss):
    """Update stop-loss and/or take-profit on an open position."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        t = Decimal(str(target)) if target is not None else None
        sl = Decimal(str(stoploss)) if stoploss is not None else None
        pos = mgr.modify_position(position_id, t, sl)
        click.echo(f"Position #{position_id} updated:")
        if pos.target:
            click.echo(f"  Target:    {pos.target}")
        if pos.stoploss:
            click.echo(f"  Stoploss:  {pos.stoploss}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        session.close()


@position.command("history")
@click.option("--portfolio", "-p", "portfolio_id", required=True, type=int, help="Portfolio ID")
def position_history(portfolio_id):
    """Show closed trade history."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        history = mgr.get_position_history(portfolio_id)
        if not history:
            click.echo("No trade history.")
            return
        for h in history:
            click.echo(
                f"  #{h.id}  {h.side.value:<4} {h.quantity} {h.symbol:<10} "
                f"entry={h.entry_price} exit={h.exit_price} pnl={h.realized_pnl} ({h.exit_reason.value})"
            )
    finally:
        session.close()
