from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI
from sqlmodel import Session, select

from paper.agents.tools import AgentTools
from paper.db.database import engine
from paper.db.models import Agent, AgentRun
from paper.services.execution_engine import order_executor

logger = logging.getLogger(__name__)


TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "get_portfolio_state", "description": "Inspect this agent's cash, PnL, active positions, orders, targets, stop losses, and notes.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "place_order", "description": "Place a paper order in your own portfolio. Use conservative sizing.", "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}, "side": {"type": "string", "enum": ["BUY", "SELL"]}, "quantity": {"type": "number"}, "limit_price": {"type": ["number", "null"]}, "target": {"type": ["number", "null"]}, "stoploss": {"type": ["number", "null"]}}, "required": ["symbol", "side", "quantity"]}}},
    {"type": "function", "function": {"name": "modify_order", "description": "Modify a pending order owned by this agent.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}, "limit_price": {"type": ["number", "null"]}, "target": {"type": ["number", "null"]}, "stoploss": {"type": ["number", "null"]}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "cancel_order", "description": "Cancel a pending order owned by this agent.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "close_position", "description": "Close an active position owned by this agent at the current market price.", "parameters": {"type": "object", "properties": {"position_id": {"type": "integer"}}, "required": ["position_id"]}}},
    {"type": "function", "function": {"name": "write_note", "description": "Write a durable trade observation or lesson for future runs.", "parameters": {"type": "object", "properties": {"content": {"type": "string"}, "symbol": {"type": ["string", "null"]}, "category": {"type": "string"}}, "required": ["content"]}}},
    {"type": "function", "function": {"name": "get_candles", "description": "Fetch OHLCV candles for any cryptocurrency through yfinance.", "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}, "interval": {"type": "string", "enum": ["15m", "1h", "4h", "1d"]}, "period": {"type": "string", "enum": ["1d", "7d", "30d", "90d"]}}, "required": ["symbol"]}}},
    {"type": "function", "function": {"name": "google_search", "description": "Search current crypto news and market information.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}}},
]


async def run_agent(agent: Agent, client: AsyncOpenAI) -> None:
    with Session(engine) as session:
        db_agent = session.get(Agent, agent.id)
        if not db_agent or not db_agent.active:
            return
        run = AgentRun(agent_id=db_agent.id)
        session.add(run)
        session.commit()
        session.refresh(run)
        tools = AgentTools(db_agent, run, session)
        try:
            state = await tools.portfolio_state()
            symbols = sorted({position["symbol"] for position in state.get("positions", [])})
            candles = {symbol: (await tools.candles(symbol, "1h", "7d"))["candles"][-48:] for symbol in symbols}
            news = {symbol: (await tools.news(symbol, 3))["results"] for symbol in symbols}
            system_prompt = db_agent.system_prompt or (
                "You are a disciplined crypto paper-trading portfolio manager. "
                "Protect capital, never revenge trade, use stop losses, and explain every action. "
                "You may only act in the portfolio provided. Do not claim a tool succeeded unless its result says so."
            )
            user_prompt = {
                "agent": {"name": db_agent.name, "strategy": db_agent.strategy},
                "portfolio": state,
                "open_position_candles": candles,
                "latest_news": news,
                "instruction": "Review the portfolio for this hourly cycle. Take action only when justified. Write a lesson when a decision is important. Finish with a concise summary.",
            }
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, default=str)},
            ]
            handlers = {
                "get_portfolio_state": lambda args: tools.portfolio_state(),
                "place_order": lambda args: tools.place_order(**args),
                "modify_order": lambda args: tools.modify_order(**args),
                "cancel_order": lambda args: tools.cancel_order(**args),
                "close_position": lambda args: tools.close_position(**args),
                "write_note": lambda args: tools.write_note(**args),
                "get_candles": lambda args: tools.candles(**args),
                "google_search": lambda args: tools.news(**args),
            }
            for _ in range(8):
                response = await client.chat.completions.create(
                    model=os.getenv("FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-70b-instruct"),
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                    temperature=0.1,
                )
                message = response.choices[0].message
                messages.append(message.model_dump(exclude_none=True))
                if not message.tool_calls:
                    run.summary = message.content or "Cycle completed without a summary."
                    break
                for call in message.tool_calls:
                    name = call.function.name
                    args = json.loads(call.function.arguments or "{}")
                    try:
                        result = await handlers[name](args)
                    except Exception as exc:
                        result = {"error": str(exc)}
                    tools._record("model", name, args, result, "error" not in result)
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
            await tools.snapshot()
            run.status = "COMPLETED"
            run.completed_at = datetime.now(UTC)
        except Exception as exc:
            logger.exception("Agent %s failed", db_agent.name)
            run.status = "FAILED"
            run.error = str(exc)
            run.completed_at = datetime.now(UTC)
        session.add(run)
        session.commit()


async def run_all_agents() -> None:
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        raise RuntimeError("FIREWORKS_API_KEY is required")
    client = AsyncOpenAI(api_key=api_key, base_url=os.getenv("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"))
    with Session(engine) as session:
        agents = session.exec(select(Agent).where(Agent.active == True)).all()
    await order_executor.sync_from_database()
    for agent in agents:
        await run_agent(agent, client)
