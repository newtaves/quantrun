#!/usr/bin/env python3
"""QuantRun CLI — Paper trading bot for crypto markets."""

import click

from quantrun.db import init_db


@click.group()
@click.version_option(package_name="quantrun-cli")
def cli():
    """QuantRun CLI — Paper trading bot for crypto markets.

    Start by running 'quantrun init' to create the database,
    then 'quantrun portfolio create' to set up a portfolio.
    """
    pass


@cli.command()
def init():
    """Initialize the database (create tables if they don't exist)."""
    init_db()
    click.echo("Database initialized.")


# Register subcommand groups
from quantrun.commands.portfolio import portfolio  # noqa: E402
from quantrun.commands.order import order  # noqa: E402
from quantrun.commands.position import position  # noqa: E402
from quantrun.commands.market import prices  # noqa: E402
from quantrun.commands.pnl import pnl  # noqa: E402
from quantrun.commands.stream import stream  # noqa: E402
from quantrun.commands.serve import serve  # noqa: E402

cli.add_command(portfolio)
cli.add_command(order)
cli.add_command(position)
cli.add_command(prices)
cli.add_command(pnl)
cli.add_command(stream)
cli.add_command(serve)


if __name__ == "__main__":
    cli()
