import asyncio
from fastapi import WebSocket
from sqlmodel import Session, select
from paper.db.database import engine
from paper.db.models import Order
from paper.services.execution_engine import order_executor

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}
        self.price_connections: list[WebSocket] = []

    async def connect_prices(self, websocket: WebSocket):
        await websocket.accept()
        self.price_connections.append(websocket)

    def disconnect_prices(self, websocket: WebSocket):
        try:
            self.price_connections.remove(websocket)
        except ValueError:
            pass

    async def connect(self, websocket: WebSocket, portfolio_id: int):
        await websocket.accept()
        if portfolio_id not in self.active_connections:
            self.active_connections[portfolio_id] = []
        self.active_connections[portfolio_id].append(websocket)

    def disconnect(self, websocket: WebSocket, portfolio_id: int):
        if portfolio_id in self.active_connections:
            try:
                self.active_connections[portfolio_id].remove(websocket)
            except ValueError:
                pass

    async def broadcast_pnl(self, portfolio_id: int, pnl_data: dict):
        if portfolio_id in self.active_connections:
            # Create a list of dead connections to remove
            dead_connections = []
            for connection in self.active_connections[portfolio_id]:
                try:
                    await connection.send_json(pnl_data)
                except Exception:
                    dead_connections.append(connection)
            
            for dead in dead_connections:
                self.disconnect(dead, portfolio_id)

    async def broadcast_refresh(self, portfolio_id: int):
        for connection in list(self.active_connections.get(portfolio_id, [])):
            try:
                await connection.send_json({"type": "refresh"})
            except Exception:
                self.disconnect(connection, portfolio_id)

    async def broadcast_prices(self, prices: dict):
        dead_connections = []
        for connection in self.price_connections:
            try:
                await connection.send_json({"type": "prices", "prices": prices})
            except Exception:
                dead_connections.append(connection)
        for dead in dead_connections:
            self.disconnect_prices(dead)

ws_manager = ConnectionManager()

def get_live_portfolio_pnl(portfolio_id: int):
    """Calculate unrealized PnL from in-memory positions for a specific portfolio."""
    positions = [
        p for p in order_executor._active_positions.values()
        if p.portfolio_id == portfolio_id
    ]
    position_ids = {p.id for p in positions}
    all_pnl = order_executor.calculate_unrealized_pnl()
    portfolio_pnl = [r for r in all_pnl if r["position_id"] in position_ids]
    
    total = sum(r["unrealized_pnl"] for r in portfolio_pnl)
    
    # Calculate live capital exposure and available cash in-memory
    invested_cash = sum(p.entry_price * p.quantity for p in positions)
    available_cash = order_executor._portfolio_cash.get(portfolio_id, 0)
    with Session(engine) as session:
        orders = session.exec(select(Order).where(Order.portfolio_id == portfolio_id)).all()

    return {
        "type": "portfolio",
        "unrealized_pnl": round(total, 5),
        "positions": portfolio_pnl,
        "orders": [{
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": float(order.quantity),
            "limit_price": float(order.limit_price) if order.limit_price else None,
            "status": order.status.value,
            "target": float(order.target) if order.target else None,
            "stoploss": float(order.stoploss) if order.stoploss else None,
        } for order in orders],
        "available_cash": float(available_cash),
        "invested_cash": float(invested_cash)
    }

def broadcast_price_update(price_dict: dict):
    """Callback for market_data_streamer to broadcast PnL on price updates."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
        
    loop.create_task(ws_manager.broadcast_prices(price_dict))

    for portfolio_id, conns in list(ws_manager.active_connections.items()):
        if not conns:
            continue
            
        # Check if this portfolio has any active positions affected by the price change
        positions = [
            p for p in order_executor._active_positions.values()
            if p.portfolio_id == portfolio_id and p.symbol in price_dict
        ]
        has_pending_order = False
        with Session(engine) as session:
            pending_orders = session.exec(select(Order).where(Order.portfolio_id == portfolio_id, Order.status == "PENDING")).all()
            has_pending_order = any(order.symbol in price_dict for order in pending_orders)

        # If affected, calculate new PnL and broadcast
        if positions or has_pending_order:
            pnl_data = get_live_portfolio_pnl(portfolio_id)
            loop.create_task(ws_manager.broadcast_pnl(portfolio_id, pnl_data))
