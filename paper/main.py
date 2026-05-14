from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import os
from typing import List

from paper.services.market_data import DEFAULT_SYMBOLS, market_data_streamer

logging.basicConfig(level=logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    #Later replace it with the symbols in the order and open positions in all portfolios
    symbols_raw = os.getenv("MARKET_SYMBOLS", ",".join(DEFAULT_SYMBOLS))
    
    symbols = [symbol.strip().upper() for symbol in symbols_raw.split(",") if symbol.strip()]
    if not symbols:
        symbols = DEFAULT_SYMBOLS

    logging.info(f"Starting Binance market price websocket for symbols: {symbols}")
    await market_data_streamer.initialize_price_stream(symbols)

    yield

    logging.info("Stopping Binance market price websocket")


app = FastAPI(lifespan=lifespan)

@app.get("/prices")
def current_prices():
    return market_data_streamer.get_all_market_prices()

@app.get("/symbol/{symbol}")
async def symbol_price(symbol:str):
    price = await market_data_streamer.get_market_price(symbol)
    return {'symbol':symbol, 'price':price}

# just boilerplate

@app.post("/order")
def create_order(order: dict):
    return {"message": "Order created", "order": order}

@app.get("/order/{order_id}")
def read_order(order_id: str):
    return {"order": f"This is your order with ID: {order_id}"}

@app.put("/order/{order_id}")
def update_order(order_id: str, order: dict):
    return {"message": "Order updated", "order_id": order_id, "order": order}

@app.delete("/order/{order_id}")
def cancel_order(order_id: str):
    return {"message": "Order deleted", "order_id": order_id}