"""PnL and analytics commands."""

import click
from quantrun.db import get_session, init_db
from quantrun.services.portfolio_manager import PortfolioManager


@click.command()
@click.argument("portfolio_id", type=int)
def pnl(portfolio_id):
    """Show PnL report for a portfolio."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        port = mgr.get_portfolio(portfolio_id)
        if not port:
            click.echo(f"Portfolio #{portfolio_id} not found.")
            return
        total = mgr.calculate_total_pnl(portfolio_id)
        click.echo(f"Portfolio: {port.name} (#{port.id})")
        click.echo(f"  Available Cash:  {port.available_cash}")
        click.echo(f"  Invested Cash:   {port.invested_cash}")
        click.echo(f"  Realized PnL:    {total['realized_pnl']}")
        click.echo(f"  Unrealized PnL:  {total['unrealized_pnl']}")
        click.echo(f"  Total PnL:       {total['total_pnl']}")
        if total["positions"]:
            click.echo(f"\n  Open Positions ({len(total['positions'])}):")
            for pos in total["positions"]:
                click.echo(f"    #{pos['position_id']}  {pos['side']:<4} {pos['quantity']} {pos['symbol']:<10} entry={pos['entry_price']:<12} current={pos['current_price']:<12} pnl={pos['unrealized_pnl']}")
    finally:
        session.close()
