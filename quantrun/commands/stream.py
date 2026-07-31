"""Stream command — start background price feed and order matching."""

import asyncio
import signal
import click
from quantrun.db import init_db
from quantrun.services.execution_engine import order_executor
from quantrun.services.market_data import market_data_streamer


@click.command()
@click.option("--symbols", "-s", default=None, help="Comma-separated symbols to stream")
def stream(symbols):
    """Start the live price streamer and order execution engine.

    Runs in the foreground, processing market ticks and matching
    pending orders / checking SL-TP until interrupted (Ctrl+C).
    """
    init_db()

    sym_list = (
        [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if symbols
        else ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"]
    )

    async def _run():
        await order_executor.sync_from_database()

        active = set(sym_list)
        for o in order_executor.get_pending_orders():
            active.add(o.symbol.upper())
        for pos in order_executor._active_positions.values():
            active.add(pos.symbol.upper())

        click.echo(f"Starting price stream for: {', '.join(sorted(active))}")
        await market_data_streamer.initialize_price_stream(list(active))
        market_data_streamer.register_price_callback(order_executor.check_on_price_update)

        click.echo("Stream active — press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            market_data_streamer.shutdown = True
            click.echo("\nStream stopped.")

    loop = asyncio.new_event_loop()

    def _shutdown(sig, frame):
        for task in asyncio.all_tasks(loop):
            task.cancel()
        click.echo("\nShutting down...")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(_run())
    except (KeyboardInterrupt, SystemExit):
        market_data_streamer.shutdown = True
        click.echo("Stream stopped.")
    finally:
        loop.close()
