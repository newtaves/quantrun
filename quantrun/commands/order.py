"""Order management commands."""

import click
from decimal import Decimal
from quantrun.db import get_session, init_db
from quantrun.db.models import Order, OrderSide
from quantrun.services.portfolio_manager import PortfolioManager
from quantrun.services.execution_engine import order_executor
from quantrun.services.market_data import market_data_streamer


@click.group()
def order():
    """Manage trading orders."""
    pass


@order.command("place")
@click.option("--portfolio", "-p", "portfolio_id", required=True, type=int, help="Portfolio ID")
@click.option("--symbol", "-s", required=True, help="Trading symbol (e.g. BTCUSDT)")
@click.option("--side", "-x", required=True, type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="Order side")
@click.option("--quantity", "-q", required=True, type=float, help="Quantity to trade")
@click.option("--limit", "-l", "limit_price", type=float, default=None, help="Limit price (market if omitted)")
@click.option("--target", "-t", type=float, default=None, help="Take-profit target price")
@click.option("--stoploss", "--sl", type=float, default=None, help="Stop-loss price")
def place_order(portfolio_id, symbol, side, quantity, limit_price, target, stoploss):
    """Place a new order. Market order if --limit is omitted."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        o = Order(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            side=OrderSide(side.upper()),
            quantity=Decimal(str(quantity)),
            limit_price=Decimal(str(limit_price)) if limit_price is not None else None,
            target=Decimal(str(target)) if target is not None else None,
            stoploss=Decimal(str(stoploss)) if stoploss is not None else None,
        )
        created = mgr.place_order(o)
        order_executor.add_order(created)

        # Market orders: execute immediately at the fetched price
        if created.limit_price is None:
            import asyncio
            price = asyncio.run(market_data_streamer.get_market_price(created.symbol))
            if price is not None:
                asyncio.run(order_executor.execute_order(created, Decimal(str(price))))

        # Re-read from DB to get the post-execution status
        session.refresh(created)
        click.echo(f"Order #{created.id} placed: {created.side.value} {created.quantity} {created.symbol} (status={created.status.value})")
        if created.executed_price:
            click.echo(f"  Executed @ {created.executed_price}")
        if created.limit_price:
            click.echo(f"  Limit: {created.limit_price}")
        if created.target:
            click.echo(f"  Target: {created.target}")
        if created.stoploss:
            click.echo(f"  Stoploss: {created.stoploss}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        session.close()


@order.command("list")
@click.option("--portfolio", "-p", "portfolio_id", required=True, type=int, help="Portfolio ID")
@click.option("--status", "-s", default=None, help="Filter by status (PENDING, EXECUTED, CANCELLED)")
def list_orders(portfolio_id, status):
    """List orders for a portfolio."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        orders = mgr.get_orders(portfolio_id, status)
        if not orders:
            click.echo("No orders found.")
            return
        for o in orders:
            limit_str = f"limit={o.limit_price}" if o.limit_price else "market"
            exec_str = f" @ {o.executed_price}" if o.executed_price else ""
            click.echo(f"  #{o.id}  {o.side.value:<4} {o.quantity} {o.symbol:<10} {limit_str:<16} {o.status.value}{exec_str}")
    finally:
        session.close()


@order.command("cancel")
@click.argument("order_id", type=int)
def cancel_order(order_id):
    """Cancel a pending order."""
    init_db()
    session = get_session()
    try:
        mgr = PortfolioManager(session)
        mgr.cancel_order(order_id)
        click.echo(f"Order #{order_id} cancelled.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        session.close()
