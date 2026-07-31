"""Portfolio management commands."""

import click
from decimal import Decimal
from quantrun.db import get_session, init_db
from quantrun.services.portfolio_manager import PortfolioManager


@click.group()
def portfolio():
    """Manage trading portfolios."""
    pass


@portfolio.command("create")
@click.option("--name", "-n", required=True, help="Portfolio name")
@click.option("--description", "-d", default="", help="Description")
@click.option("--cash", "-c", default=10000.0, type=float, help="Starting cash balance")
def create_portfolio(name, description, cash):
    """Create a new portfolio with an initial cash balance."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        p = mgr.create_portfolio(name, description, Decimal(str(cash)))
        click.echo(f"Created portfolio #{p.id}: {p.name} with {p.available_cash} cash")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        session.close()


@portfolio.command("list")
def list_portfolios():
    """List all portfolios."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        portfolios = mgr.list_portfolios()
        if not portfolios:
            click.echo("No portfolios found.")
            return
        for p in portfolios:
            click.echo(f"  #{p.id}  {p.name:<20}  cash={p.available_cash}  invested={p.invested_cash}  pnl={p.total_pnl}")
    finally:
        session.close()


@portfolio.command("get")
@click.argument("portfolio_id", type=int)
def get_portfolio(portfolio_id):
    """Show details of a specific portfolio."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        p = mgr.get_portfolio(portfolio_id)
        if not p:
            click.echo(f"Portfolio #{portfolio_id} not found.")
            return
        click.echo(f"  ID:          {p.id}")
        click.echo(f"  Name:        {p.name}")
        click.echo(f"  Description: {p.description or '-'}")
        click.echo(f"  Cash:        {p.available_cash}")
        click.echo(f"  Invested:    {p.invested_cash}")
        click.echo(f"  Total PnL:   {p.total_pnl}")
        click.echo(f"  Created:     {p.created_at}")
    finally:
        session.close()


@portfolio.command("delete")
@click.argument("portfolio_id", type=int)
def delete_portfolio(portfolio_id):
    """Delete a portfolio (must have no open positions or pending orders)."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        mgr.delete_portfolio(portfolio_id)
        click.echo(f"Deleted portfolio #{portfolio_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        session.close()
