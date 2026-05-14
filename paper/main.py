from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
import logging
import os
from paper.db.models import Order, OrderSide, OrderStatus, Portfolio
from paper.db import get_db
from sqlmodel import Session, select
from paper.services.market_data import DEFAULT_SYMBOLS, market_data_streamer
from decimal import Decimal

logging.basicConfig(level=logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    #All this code will run at the startup of the app

    #Later replace it with the symbols in the order and open positions in all portfolios
    symbols_raw = os.getenv("MARKET_SYMBOLS", ",".join(DEFAULT_SYMBOLS))
    
    symbols = [symbol.strip().upper() for symbol in symbols_raw.split(",") if symbol.strip()]
    if not symbols:
        symbols = DEFAULT_SYMBOLS

    logging.info(f"Starting Binance market price websocket for symbols: {symbols}")
    await market_data_streamer.initialize_price_stream(symbols)


    #all this code will run when the app shuts down
    yield
    market_data_streamer.shutdown = True # i.e. The server is closing so do not attempt to reconnect with websocket
    logging.info("Stopping Binance market price websocket")


app = FastAPI(lifespan=lifespan)

#===============Testing===========================
@app.get("/prices")
def current_prices():
    return market_data_streamer.get_all_market_prices()

@app.get("/symbol/{symbol}")
async def symbol_price(symbol:str):
    price = await market_data_streamer.get_market_price(symbol)
    return {'symbol':symbol, 'price':price}
#================Testing==========================


@app.post("/order")
async def create_order(order: Order, session: Session = Depends(get_db)):

    # check portfolio exists
    portfolio = session.get(Portfolio, order.portfolio_id)

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # validate quantity
    if order.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    # validate limit price
    if order.limit_price is not None and order.limit_price <= 0:
        raise HTTPException(status_code=400, detail="Limit price must be greater than 0")

    # determine estimated execution price
    if order.limit_price is not None:
        estimated_price = order.limit_price
    else:
        estimated_price = await market_data_streamer.get_market_price(order.symbol) #fetch the market price

        if estimated_price is None:
            raise HTTPException(status_code=400, detail=f"Unable to fetch market price for {order.symbol}")

    # estimated total order value
    estimated_cost = Decimal(str(estimated_price)) * Decimal(str(order.quantity))

    # only validate buying power
    if order.side == OrderSide.BUY:

        if portfolio.available_cash < estimated_cost:
            raise HTTPException(status_code=400, detail=(
                    f"Insufficient funds. "
                    f"Required: {estimated_cost}, "
                    f"Available: {portfolio.available_cash}"
                )
            )

    # order is only placed, not executed
    order.status = OrderStatus.PENDING

    session.add(order)
    session.commit()
    session.refresh(order)

    return {
        "message": "Order placed successfully",
        "order": order,
        "estimated_cost": estimated_cost
    }


@app.get("/order/{order_id}")
def read_order(order_id: str, session: Session = Depends(get_db)):
    statement = select(Order).where(Order.id == order_id)
    order = session.exec(statement).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with ID {order_id} not found")
    
    return {
        "order": order
    }


@app.put("/order/{order_id}")
def update_order(order_id: str, order: dict):
    return {"message": "Order updated", "order_id": order_id, "order": order}

@app.delete("/order/{order_id}")
def cancel_order(order_id: str):
    return {"message": "Order deleted", "order_id": order_id}