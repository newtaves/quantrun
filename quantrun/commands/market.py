"""Market data commands."""

import asyncio
import click
from quantrun.db import init_db
from quantrun.services.market_data import market_data_streamer


@click.command()
@click.option("--symbols", "-s", default=None, help="Comma-separated symbols (default: BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT)")
def prices(symbols):
    """Fetch and display current market prices."""
    init_db()
    sym_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None

    async def _fetch():
        if sym_list:
            for s in sym_list:
                await market_data_streamer.get_market_price(s)
        else:
            for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT", "LTCUSDT", "DOGEUSDT", "XRPUSDT"]:
                await market_data_streamer.get_market_price(s)
        data = market_data_streamer.get_all_market_prices()
        await market_data_streamer.shutdown_connections()
        return data

    data = asyncio.run(_fetch())
    if not data:
        click.echo("Unable to fetch prices.")
        return
    click.echo(f"{'Symbol':<12} {'Price':>14}")
    click.echo("-" * 28)
    for sym in sorted(data.keys()):
        click.echo(f"{sym:<12} {data[sym]:>14,.2f}")
