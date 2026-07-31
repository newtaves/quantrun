"""QuantRun REST API server.

Start with:
    uvicorn server:app --reload --port 8000

Or:
    python server.py
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from quantrun.client import QuantRun

log = logging.getLogger("quantrun.server")

qr = QuantRun()


@asynccontextmanager
async def lifespan(app: FastAPI):
    qr.init()
    yield
    qr.stop()


app = FastAPI(title="QuantRun API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ───────────────────────────────────────────────────────────

class CreatePortfolio(BaseModel):
    name: str
    cash: float = 10000
    description: str = ""


class PlaceOrder(BaseModel):
    symbol: str
    side: str
    usd: Optional[float] = None
    qty: Optional[float] = None
    limit: Optional[float] = None
    target: Optional[float] = None
    stoploss: Optional[float] = None


# ── Portfolios ───────────────────────────────────────────────────────────────

@app.get("/api/portfolios")
def list_portfolios():
    return {"portfolios": [asdict(p) for p in qr.list_portfolios()]}


@app.post("/api/portfolios")
def create_portfolio(data: CreatePortfolio):
    p = qr.create_portfolio(data.name, data.cash, data.description)
    return {"portfolio": asdict(p)}


@app.get("/api/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: int):
    p = qr.get_portfolio(portfolio_id)
    if not p:
        raise HTTPException(404, "Portfolio not found")
    return {"portfolio": asdict(p)}


@app.delete("/api/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: int):
    try:
        qr.delete_portfolio(portfolio_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "Deleted"}


# ── Orders ───────────────────────────────────────────────────────────────────

@app.post("/api/portfolios/{portfolio_id}/orders")
def place_order(portfolio_id: int, data: PlaceOrder):
    if data.side.upper() == "BUY":
        result = qr.buy(
            portfolio_id, data.symbol,
            usd=data.usd, qty=data.qty,
            limit=data.limit, target=data.target, stoploss=data.stoploss,
        )
    else:
        result = qr.sell(
            portfolio_id, data.symbol,
            usd=data.usd, qty=data.qty,
            limit=data.limit, target=data.target, stoploss=data.stoploss,
        )
    if result.error:
        raise HTTPException(400, result.error)
    return {"order": asdict(result)}


@app.get("/api/portfolios/{portfolio_id}/orders")
def list_orders(portfolio_id: int):
    session = qr._session()
    try:
        from quantrun.db.models import Order
        from sqlmodel import select
        orders = list(session.exec(select(Order).where(Order.portfolio_id == portfolio_id).order_by(Order.created_at.desc())).all())
        return {"orders": [
            {
                "order_id": o.id, "symbol": o.symbol, "side": o.side.value,
                "quantity": float(o.quantity),
                "limit_price": float(o.limit_price) if o.limit_price else None,
                "executed_price": float(o.executed_price) if o.executed_price else None,
                "target": float(o.target) if o.target else None,
                "stoploss": float(o.stoploss) if o.stoploss else None,
                "status": o.status.value,
                "created_at": str(o.created_at),
            }
            for o in orders
        ]}
    finally:
        session.close()


@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: int):
    try:
        qr.cancel_order(order_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "Cancelled"}


# ── Positions ────────────────────────────────────────────────────────────────

@app.get("/api/portfolios/{portfolio_id}/positions")
def list_positions(portfolio_id: int):
    return {"positions": [asdict(p) for p in qr.get_positions(portfolio_id)]}


@app.delete("/api/positions/{position_id}")
def close_position(position_id: int):
    try:
        qr.close_position(position_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"message": "Closed"}


# ── PnL ──────────────────────────────────────────────────────────────────────

@app.get("/api/portfolios/{portfolio_id}/pnl")
def get_pnl(portfolio_id: int):
    return {"pnl": asdict(qr.get_pnl(portfolio_id))}


@app.get("/api/portfolios/{portfolio_id}/history")
def get_history(portfolio_id: int):
    return {"history": qr.get_history(portfolio_id)}


# ── Prices ───────────────────────────────────────────────────────────────────

@app.get("/api/prices")
def get_prices(symbols: Optional[str] = Query(None)):
    sym_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    return {"prices": qr.get_prices(sym_list)}


@app.get("/api/prices/{symbol}")
def get_price(symbol: str):
    price = qr.get_price(symbol)
    if price is None:
        raise HTTPException(404, f"Price not found for {symbol}")
    return {"symbol": symbol.upper(), "price": price}


# ── WebSocket: live prices ──────────────────────────────────────────────────

@app.websocket("/ws/prices")
async def ws_prices(ws: WebSocket):
    await ws.accept()
    from quantrun.services.market_data import market_data_streamer

    last_prices: dict = {}

    def on_price_update(prices: dict):
        last_prices.update(prices)

    market_data_streamer.register_price_callback(on_price_update)

    try:
        while True:
            current = market_data_streamer.get_all_market_prices()
            if current:
                await ws.send_json({"prices": current})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── WebSocket: live portfolio data ──────────────────────────────────────────

@app.websocket("/ws/portfolio/{portfolio_id}")
async def ws_portfolio(ws: WebSocket, portfolio_id: int):
    await ws.accept()

    from quantrun.db.models import Order
    from sqlmodel import select

    try:
        while True:
            try:
                if not qr.get_portfolio(portfolio_id):
                    await ws.send_json({"error": "Portfolio not found"})
                    break

                pnl = asdict(qr.get_pnl(portfolio_id))
                positions = [asdict(p) for p in qr.get_positions(portfolio_id)]
                portfolio = asdict(qr.get_portfolio(portfolio_id))

                session = qr._session()
                try:
                    orders = list(session.exec(
                        select(Order).where(Order.portfolio_id == portfolio_id).order_by(Order.created_at.desc())
                    ).all())
                    orders_data = [
                        {
                            "order_id": o.id, "symbol": o.symbol, "side": o.side.value,
                            "quantity": float(o.quantity),
                            "limit_price": float(o.limit_price) if o.limit_price else None,
                            "executed_price": float(o.executed_price) if o.executed_price else None,
                            "target": float(o.target) if o.target else None,
                            "stoploss": float(o.stoploss) if o.stoploss else None,
                            "status": o.status.value,
                            "created_at": str(o.created_at),
                        }
                        for o in orders
                    ]
                finally:
                    session.close()

                await ws.send_json({
                    "pnl": pnl,
                    "positions": positions,
                    "orders": orders_data,
                    "portfolio": portfolio,
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                log.error("WS portfolio error: %s", e)
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
