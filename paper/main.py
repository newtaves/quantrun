from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import traceback
from typing import Optional

from paper.db.models import ExitReason, Order, OrderSide, OrderStatus, Portfolio
from paper.db import get_db
from paper.services.market_data import DEFAULT_SYMBOLS, market_data_streamer
from paper.services.portfolio_manager import PortfolioManager
from paper.services.execution_engine import order_executor
from sqlmodel import Session, select
from decimal import Decimal

logging.basicConfig(level=logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    symbols_raw = os.getenv("MARKET_SYMBOLS", ",".join(DEFAULT_SYMBOLS))
    symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
    if not symbols:
        symbols = DEFAULT_SYMBOLS

    # Restore any pending orders / active positions that survived a restart
    await order_executor.sync_from_database()

    # Automatically subscribe to all symbols with active orders or positions
    active_symbols = set(symbols)  # Start with defaults
    pending_orders = order_executor.get_pending_orders()
    for order in pending_orders:
        active_symbols.add(order.symbol.upper())
    
    for pos in order_executor._active_positions.values():
        active_symbols.add(pos.symbol.upper())

    logging.info(f"Starting Binance market price websocket for symbols: {active_symbols}")
    await market_data_streamer.initialize_price_stream(list(active_symbols))

    # Hook execution engine into market data feed.
    # Every price tick now automatically triggers order matching + SL/TP checks.
    market_data_streamer.register_price_callback(order_executor.check_on_price_update)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    market_data_streamer.shutdown = True
    logging.info("Stopping Binance market price websocket")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logging.error(f"Unhandled error on {request.method} {request.url}:\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# ═══════════════════════════ Market Prices ════════════════════════════════════

@app.get("/prices")
def current_prices():
    return market_data_streamer.get_all_market_prices()


@app.get("/symbol/{symbol}")
async def symbol_price(symbol: str):
    price = await market_data_streamer.get_market_price(symbol)
    if price is None:
        raise HTTPException(status_code=404, detail=f"Unable to fetch price for {symbol}")
    return {"symbol": symbol, "price": price}


# ═══════════════════════════ Portfolio CRUD ═══════════════════════════════════

@app.post("/portfolio")
async def create_portfolio(data: Portfolio, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    try:
        portfolio = await manager.create_portfolio(data)
        return {"message": "Portfolio created successfully", "portfolio": portfolio}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/portfolio")
def list_portfolios(user_id: int, session: Session = Depends(get_db)):
    statement = select(Portfolio).where(Portfolio.user_id == user_id)
    portfolios = list(session.exec(statement).all())
    return {"portfolios": portfolios}


@app.get("/portfolio/{portfolio_id}")
def get_portfolio(portfolio_id: int, session: Session = Depends(get_db)):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return {"portfolio": portfolio}


@app.put("/portfolio/{portfolio_id}")
async def update_portfolio(
    portfolio_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Session = Depends(get_db),
):
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if name is not None:
        portfolio.name = name
    if description is not None:
        portfolio.description = description
    session.add(portfolio)
    session.commit()
    session.refresh(portfolio)
    return {"message": "Portfolio updated", "portfolio": portfolio}


@app.delete("/portfolio/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    try:
        await manager.delete_portfolio(portfolio_id)
        return {"message": "Portfolio deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════ Portfolio PnL & Analytics ═══════════════════════

@app.get("/portfolio/{portfolio_id}/pnl")
async def portfolio_pnl(portfolio_id: int, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    return await manager.generate_pnl_report(portfolio_id)


@app.get("/portfolio/{portfolio_id}/unrealized-pnl")
async def portfolio_unrealized_pnl(portfolio_id: int, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    result = await manager.calculate_unrealized_pnl(portfolio_id)
    return {"unrealized_pnl": float(result["total"]), "positions": result["positions"]}


@app.get("/portfolio/{portfolio_id}/summary")
async def portfolio_summary(portfolio_id: int, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    portfolio = session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    pnl = await manager.calculate_total_pnl(portfolio_id)
    positions = await manager.get_positions(portfolio_id)
    return {
        "portfolio_id": portfolio_id,
        "name": portfolio.name,
        "available_cash": float(portfolio.available_cash),
        "invested_cash": float(portfolio.invested_cash),
        "total_pnl": pnl["total_pnl"],
        "unrealized_pnl": pnl["unrealized_pnl"],
        "realized_pnl": pnl["realized_pnl"],
        "position_count": len(positions),
        "positions": pnl["positions"],
    }


# ═══════════════════════════ Positions ═══════════════════════════════════════

@app.get("/portfolio/{portfolio_id}/positions")
async def portfolio_positions(portfolio_id: int, session: Session = Depends(get_db)):
    """
    Returns all open positions with on-the-fly current_price and unrealized_pnl.
    These are NOT stored in the database — calculated fresh on every call.
    """
    manager = PortfolioManager(session)
    result = await manager.calculate_unrealized_pnl(portfolio_id)
    return {"positions": result["positions"]}


@app.delete("/portfolio/{portfolio_id}/positions/{position_id}")
async def close_position(
    portfolio_id: int,
    position_id: int,
    session: Session = Depends(get_db),
):
    """Manually close an open position at the current market price."""
    manager = PortfolioManager(session)
    try:
        await manager.close_position(position_id, ExitReason.MANUAL)
        return {"message": f"Position #{position_id} closed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/portfolio/{portfolio_id}/positions/{position_id}")
async def update_position(
    portfolio_id: int,
    position_id: int,
    target: Optional[Decimal] = None,
    stoploss: Optional[Decimal] = None,
    session: Session = Depends(get_db),
):
    """Update an active position's stoploss and target levels."""
    manager = PortfolioManager(session)
    try:
        position = await manager.modify_position(position_id, target, stoploss)
        return {"message": "Position updated", "position": position}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════ Position History (Analytics) ════════════════════

@app.get("/portfolio/{portfolio_id}/history")
async def position_history(portfolio_id: int, session: Session = Depends(get_db)):
    """
    Returns all closed trade records for analytics.
    Includes entry/exit prices, timestamps, PnL, and exit reason.
    """
    manager = PortfolioManager(session)
    history = await manager.get_position_history(portfolio_id)
    return {
        "history": [
            {
                "id": h.id,
                "order_id": h.order_id,
                "symbol": h.symbol,
                "side": h.side.value,
                "quantity": float(h.quantity),
                "entry_price": float(h.entry_price),
                "exit_price": float(h.exit_price),
                "realized_pnl": float(h.realized_pnl),
                "target": float(h.target) if h.target else None,
                "stoploss": float(h.stoploss) if h.stoploss else None,
                "exit_reason": h.exit_reason.value,
                "opened_at": str(h.opened_at),
                "closed_at": str(h.closed_at),
            }
            for h in history
        ]
    }


# ═══════════════════════════ Orders ══════════════════════════════════════════

@app.post("/order")
async def create_order(order: Order, session: Session = Depends(get_db)):
    """
    Place a new order. After saving as PENDING, adds it to the in-memory
    execution engine. Market orders will be filled on the next price tick.
    """
    manager = PortfolioManager(session)
    try:
        created = await manager.place_order(order)
        # Register with execution engine for matching
        order_executor.add_order(created)
        return {"message": "Order placed successfully", "order": created}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/order/{order_id}")
def read_order(order_id: int, session: Session = Depends(get_db)):
    statement = select(Order).where(Order.id == order_id)
    order = session.exec(statement).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    return {"order": order}


@app.put("/order/{order_id}")
async def update_order(
    order_id: int,
    limit_price: Optional[Decimal] = None,
    target: Optional[Decimal] = None,
    stoploss: Optional[Decimal] = None,
    session: Session = Depends(get_db),
):
    manager = PortfolioManager(session)
    try:
        order = await manager.modify_order(order_id, limit_price, target, stoploss)
        return {"message": "Order updated", "order": order}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/order/{order_id}")
async def cancel_order(order_id: int, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    try:
        await manager.cancel_order(order_id)
        return {"message": "Order cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/portfolio/{portfolio_id}/orders")
async def portfolio_orders(
    portfolio_id: int,
    status: Optional[str] = None,
    session: Session = Depends(get_db),
):
    manager = PortfolioManager(session)
    orders = await manager.get_orders(portfolio_id, status)
    return {"orders": orders}


# ═══════════════════════════ Execution Engine State (debug) ══════════════════

@app.get("/engine/pending")
def engine_pending_orders(symbol: Optional[str] = None):
    """Return current in-memory pending orders (for debugging)."""
    orders = order_executor.get_pending_orders(symbol)
    return {
        "pending_orders": [
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": o.side.value,
                "quantity": float(o.quantity),
                "limit_price": float(o.limit_price) if o.limit_price else None,
                "target": float(o.target) if o.target else None,
                "stoploss": float(o.stoploss) if o.stoploss else None,
            }
            for o in orders
        ]
    }


@app.get("/engine/positions")
def engine_active_positions():
    """Return current in-memory active positions with live PnL (for debugging)."""
    pnl_data = order_executor.calculate_unrealized_pnl()
    return {"active_positions": pnl_data}
