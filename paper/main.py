from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
import traceback
from typing import Optional

from paper.db.models import Order, OrderSide, OrderStatus, Portfolio
from paper.db import get_db
from paper.services.market_data import DEFAULT_SYMBOLS, market_data_streamer
from paper.services.portfolio_manager import PortfolioManager
from sqlmodel import Session, select
from decimal import Decimal

logging.basicConfig(level=logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    symbols_raw = os.getenv("MARKET_SYMBOLS", ",".join(DEFAULT_SYMBOLS))
    symbols = [symbol.strip().upper() for symbol in symbols_raw.split(",") if symbol.strip()]
    if not symbols:
        symbols = DEFAULT_SYMBOLS

    logging.info(f"Starting Binance market price websocket for symbols: {symbols}")
    await market_data_streamer.initialize_price_stream(symbols)

    yield

    # Shutdown
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


# =============== Market Prices ===============
@app.get("/prices")
def current_prices():
    return market_data_streamer.get_all_market_prices()


@app.get("/symbol/{symbol}")
async def symbol_price(symbol: str):
    price = await market_data_streamer.get_market_price(symbol)
    if price is None:
        raise HTTPException(status_code=404, detail=f"Unable to fetch price for {symbol}")
    return {"symbol": symbol, "price": price}


# =============== Portfolio CRUD ===============
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


# =============== Portfolio PnL & Analytics ===============
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
    }


# =============== Positions ===============
@app.get("/portfolio/{portfolio_id}/positions")
async def portfolio_positions(portfolio_id: int, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    positions = await manager.get_positions(portfolio_id)
    prices = market_data_streamer.get_all_market_prices()
    result = []
    for pos in positions:
        current_price = prices.get(pos.symbol, float(pos.current_price))
        if pos.side == OrderSide.BUY:
            pnl = (Decimal(str(current_price)) - pos.average_price) * pos.quantity
        else:
            pnl = (pos.average_price - Decimal(str(current_price))) * pos.quantity
        result.append({
            "id": pos.id,
            "symbol": pos.symbol,
            "side": pos.side.value,
            "quantity": float(pos.quantity),
            "average_price": float(pos.average_price),
            "current_price": float(current_price),
            "unrealized_pnl": round(float(pnl), 5),
            "target": float(pos.target) if pos.target else None,
            "stoploss": float(pos.stoploss) if pos.stoploss else None,
            "opened_at": str(pos.opened_at),
        })
    return {"positions": result}


# =============== Orders ===============
@app.post("/order")
async def create_order(order: Order, session: Session = Depends(get_db)):
    manager = PortfolioManager(session)
    try:
        created = await manager.place_order(order)
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
