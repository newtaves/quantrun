from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import yfinance as yf
from sqlmodel import Session, select

from paper.db.database import engine
from paper.db.models import (
    Agent,
    AgentActivity,
    AgentNote,
    AgentRun,
    AgentEquitySnapshot,
    ExitReason,
    Order,
    OrderSide,
    Portfolio,
)
from paper.services.execution_engine import order_executor
from paper.services.market_data import market_data_streamer
from paper.services.portfolio_manager import PortfolioManager


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


def _crypto_ticker(symbol: str) -> str:
    normalized = symbol.upper().replace("/", "")
    if normalized.endswith("USDT"):
        return f"{normalized[:-4]}-USD"
    if normalized.endswith("USD"):
        return f"{normalized[:-3]}-USD"
    return normalized


def get_crypto_candles(symbol: str, interval: str = "1h", period: str = "7d") -> list[dict[str, Any]]:
    """Return OHLCV candles for any crypto ticker through yfinance.

    Symbols such as BTCUSDT, BTC/USD, BTCUSD, and BTC-USD are accepted.
    """
    ticker = _crypto_ticker(symbol)
    frame = yf.download(ticker, interval=interval, period=period, auto_adjust=False, progress=False)
    if frame.empty:
        return []
    if hasattr(frame.columns, "levels"):
        frame.columns = [column[0] if isinstance(column, tuple) else column for column in frame.columns]
    candles: list[dict[str, Any]] = []
    for timestamp, row in frame.tail(500).iterrows():
        candles.append({
            "timestamp": timestamp.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
        })
    return candles


async def search_crypto_news(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search current crypto news using Google Custom Search, with RSS fallback."""
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")
    if api_key and cx:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": api_key, "cx": cx, "q": f"crypto {query}", "num": min(limit, 10)},
            )
            response.raise_for_status()
            return [
                {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
                for item in response.json().get("items", [])
            ]

    # Google News RSS requires no API key and keeps the hourly job usable by default.
    import xml.etree.ElementTree as ET
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(
            "https://news.google.com/rss/search",
            params={"q": f"crypto {query}", "hl": "en-US", "gl": "US", "ceid": "US:en"},
        )
        response.raise_for_status()
    root = ET.fromstring(response.text)
    items = []
    for item in root.findall("./channel/item")[:limit]:
        items.append({
            "title": item.findtext("title", ""),
            "url": item.findtext("link", ""),
            "snippet": item.findtext("description", ""),
        })
    return items


class AgentTools:
    """Portfolio-scoped tools exposed to one agent and fully activity-logged."""

    def __init__(self, agent: Agent, run: AgentRun, session: Session):
        self.agent = agent
        self.run = run
        self.session = session
        self.manager = PortfolioManager(session)

    def _record(self, kind: str, name: str, inputs: Any, output: Any, success: bool = True) -> None:
        self.session.add(AgentActivity(
            agent_id=self.agent.id,
            run_id=self.run.id,
            kind=kind,
            name=name,
            input_json=_json(inputs),
            output_json=_json(output),
            success=success,
        ))
        self.session.commit()

    async def portfolio_state(self) -> dict[str, Any]:
        report = await self.manager.generate_pnl_report(self.agent.portfolio_id)
        positions = await self.manager.get_positions(self.agent.portfolio_id)
        orders = await self.manager.get_orders(self.agent.portfolio_id)
        notes = self.session.exec(
            select(AgentNote).where(AgentNote.agent_id == self.agent.id).order_by(AgentNote.created_at.desc()).limit(20)
        ).all()
        state = {
            **report,
            "positions": report.get("positions", []),
            "position_limits": [
                {"id": p.id, "symbol": p.symbol, "side": p.side.value, "target": p.target, "stoploss": p.stoploss}
                for p in positions
            ],
            "orders": [
                {"id": o.id, "symbol": o.symbol, "side": o.side.value, "quantity": o.quantity,
                 "limit_price": o.limit_price, "status": o.status.value, "target": o.target, "stoploss": o.stoploss}
                for o in orders
            ],
            "notes": [{"symbol": n.symbol, "category": n.category, "content": n.content, "created_at": n.created_at} for n in notes],
        }
        self._record("observation", "portfolio_state", {}, state)
        return state

    async def place_order(self, symbol: str, side: str, quantity: float, limit_price: float | None = None,
                          target: float | None = None, stoploss: float | None = None) -> dict[str, Any]:
        order = Order(
            portfolio_id=self.agent.portfolio_id,
            symbol=symbol.upper(), side=OrderSide(side.upper()), quantity=Decimal(str(quantity)),
            limit_price=Decimal(str(limit_price)) if limit_price is not None else None,
            target=Decimal(str(target)) if target is not None else None,
            stoploss=Decimal(str(stoploss)) if stoploss is not None else None,
        )
        try:
            created = await self.manager.place_order(order)
            order_executor.add_order(created)
            price = await market_data_streamer.get_market_price(created.symbol)
            if created.limit_price is None and price is not None:
                await order_executor.process_market_tick(created.symbol, Decimal(str(price)))
            result = {"order_id": created.id, "status": created.status.value, "symbol": created.symbol}
            self._record("tool", "place_order", locals(), result)
            return result
        except Exception as exc:
            self._record("tool", "place_order", locals(), {"error": str(exc)}, False)
            raise

    async def modify_order(self, order_id: int, limit_price: float | None = None,
                           target: float | None = None, stoploss: float | None = None) -> dict[str, Any]:
        try:
            existing = await self.manager.get_order(order_id)
            if not existing or existing.portfolio_id != self.agent.portfolio_id:
                raise ValueError("Order is not owned by this agent")
            order = await self.manager.modify_order(order_id, limit_price, target, stoploss)
            result = {"order_id": order.id, "status": order.status.value, "target": order.target, "stoploss": order.stoploss}
            self._record("tool", "modify_order", locals(), result)
            return result
        except Exception as exc:
            self._record("tool", "modify_order", locals(), {"error": str(exc)}, False)
            raise

    async def cancel_order(self, order_id: int) -> dict[str, Any]:
        order = await self.manager.get_order(order_id)
        if not order or order.portfolio_id != self.agent.portfolio_id:
            raise ValueError("Order is not owned by this agent")
        await self.manager.cancel_order(order_id)
        result = {"order_id": order_id, "status": "CANCELLED"}
        self._record("tool", "cancel_order", locals(), result)
        return result

    async def close_position(self, position_id: int) -> dict[str, Any]:
        position = await self.manager.get_position(position_id)
        if not position or position.portfolio_id != self.agent.portfolio_id:
            raise ValueError("Position is not owned by this agent")
        await self.manager.close_position(position_id, ExitReason.MANUAL)
        result = {"position_id": position_id, "status": "CLOSED"}
        self._record("tool", "close_position", locals(), result)
        return result

    async def write_note(self, content: str, symbol: str | None = None, category: str = "lesson") -> dict[str, Any]:
        note = AgentNote(agent_id=self.agent.id, portfolio_id=self.agent.portfolio_id, symbol=symbol, category=category, content=content)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        result = {"note_id": note.id, "content": note.content}
        self._record("tool", "write_note", locals(), result)
        return result

    async def candles(self, symbol: str, interval: str = "1h", period: str = "7d") -> dict[str, Any]:
        candles = await asyncio.to_thread(get_crypto_candles, symbol, interval, period)
        result = {"symbol": symbol.upper(), "interval": interval, "period": period, "candles": candles}
        self._record("tool", "get_candles", {"symbol": symbol, "interval": interval, "period": period}, {"count": len(candles)})
        return result

    async def news(self, query: str, limit: int = 5) -> dict[str, Any]:
        results = await search_crypto_news(query, limit)
        result = {"query": query, "results": results}
        self._record("tool", "google_search", {"query": query, "limit": limit}, result)
        return result

    async def snapshot(self) -> AgentEquitySnapshot:
        report = await self.manager.generate_pnl_report(self.agent.portfolio_id)
        portfolio = self.session.get(Portfolio, self.agent.portfolio_id)
        snapshot = AgentEquitySnapshot(
            agent_id=self.agent.id,
            equity=Decimal(str(report["available_cash"])) + Decimal(str(report["invested_cash"])) + Decimal(str(report["unrealized_pnl"])),
            available_cash=Decimal(str(report["available_cash"])),
            invested_cash=Decimal(str(report["invested_cash"])),
            realized_pnl=Decimal(str(report["realized_pnl"])),
            unrealized_pnl=Decimal(str(report["unrealized_pnl"])),
        )
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot
