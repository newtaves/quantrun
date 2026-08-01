# QuantRun CLI

Paper trading bot for crypto markets. Simulates orders against live Binance prices with an in-memory execution engine, stop-loss / take-profit management, position analytics, and a terminal-style React dashboard with live WebSocket updates.

## Setup

```bash
# Clone and enter the project
cd quantrun-cli

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install Python package (creates the `quantrun` CLI command)
pip install -e .

# Initialize database
quantrun init

# Install frontend dependencies
cd frontend && npm install && cd ..
```

The FastAPI service stores its local SQLite database at `data/paper_trading.db`.
Set `QUANTRUN_DB_PATH` to use a different location.

## Autonomous agents

Create an agent through the API; this creates a dedicated paper portfolio:

```bash
curl -X POST http://localhost:8001/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"Momentum","strategy":"momentum","capital":100000}'
```

Run one agent cycle locally:

```bash
FIREWORKS_API_KEY=your-key uv run python -m paper.agents.run_agents
```

The runner records model calls, tool calls, notes, runs, and hourly equity snapshots in the same SQLite database. Tools include portfolio inspection, order placement/modification/cancellation, position closing, durable notes, yfinance candles, and current crypto news. Configure `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_CX` for Google Custom Search; otherwise the news tool uses Google News RSS.

The leaderboard is available at `GET /agents/leaderboard`, with equity series at `GET /agents/{id}/equity`. The React dashboard exposes it under **AGENT RANKINGS**.

The GitHub Actions workflow in `.github/workflows/run-agents.yml` runs hourly. GitHub-hosted runners are ephemeral, so production use requires a persistent database strategy (for example a self-hosted runner with the SQLite file, or a future PostgreSQL adapter); the workflow should not be expected to preserve a local SQLite file between hosted runs.

## Quick Start

```bash
# Start everything (API server + React frontend)
quantrun serve

# Open http://localhost:5173
```

## Architecture

```
React UI (port 5173)
    |  HTTP + WebSocket
FastAPI server (port 8000)
    |  imports
SDK client (quantrun.client)
    |  background thread
Binance WebSocket + Execution Engine
    |
SQLite database
```

The SDK starts a **background daemon** on first use that keeps the WebSocket price feed and execution engine alive. Limit orders, stop-loss, and target checks work automatically without a separate process.

Two WebSocket streams feed the frontend:
- `/ws/prices` — live market prices pushed every second
- `/ws/portfolio/{id}` — live positions, orders, and PnL for a portfolio

## CLI Commands

### Serve

| Command | Description |
|---------|-------------|
| `quantrun serve` | Start API server + React frontend |
| `quantrun serve --no-frontend` | Start API server only |
| `quantrun serve -p 9000` | Custom API port |

### Database

| Command | Description |
|---------|-------------|
| `quantrun init` | Create tables if they don't exist |

### Portfolio

| Command | Description |
|---------|-------------|
| `quantrun portfolio create --name NAME [--cash AMOUNT]` | Create a new portfolio |
| `quantrun portfolio list` | List all portfolios |
| `quantrun portfolio get ID` | Show portfolio details |
| `quantrun portfolio delete ID` | Delete (must have no open positions or pending orders) |

### Orders

| Command | Description |
|---------|-------------|
| `quantrun order place -p PORT -s SYMBOL -x BUY\|SELL -q QTY [--limit PRICE] [--target PRICE] [--stoploss PRICE]` | Place an order |
| `quantrun order list -p PORT [--status STATUS]` | List orders |
| `quantrun order cancel ORDER_ID` | Cancel a pending order |

Market orders (no `--limit`) execute immediately. Limit orders wait for the price to hit the level via the background WebSocket stream.

### Positions

| Command | Description |
|---------|-------------|
| `quantrun position list -p PORT` | List open positions with live PnL |
| `quantrun position close POS_ID [--reason MANUAL\|STOPLOSS\|TARGET]` | Close at market price |
| `quantrun position modify POS_ID [--target PRICE] [--stoploss PRICE]` | Update SL/TP levels |
| `quantrun position history -p PORT` | View closed trade history |

### Market Data

| Command | Description |
|---------|-------------|
| `quantrun prices [--symbols BTCUSDT,ETHUSDT]` | Fetch current prices via REST |

### Analytics

| Command | Description |
|---------|-------------|
| `quantrun pnl PORTFOLIO_ID` | Full PnL report (realized + unrealized) |

### Live Stream

| Command | Description |
|---------|-------------|
| `quantrun stream [--symbols BTCUSDT,ETHUSDT]` | Start WebSocket price feed + order matching engine |

Only needed if you want a standalone stream process. The SDK background daemon handles this automatically.

## Python SDK

Use the SDK as a library in your own scripts and strategies.

```python
from quantrun.client import QuantRun

qr = QuantRun()
qr.init()  # Creates DB + starts background WebSocket daemon

# Portfolios
qr.create_portfolio("My Fund", cash=50000)
qr.list_portfolios()
qr.get_portfolio(1)

# Prices
qr.get_price("BTCUSDT")
qr.get_prices(["BTCUSDT", "ETHUSDT", "SOLUSDT"])

# Orders — market
qr.buy(1, "BTCUSDT", usd=100)
qr.sell(1, "ETHUSDT", qty=0.5)

# Orders — limit with SL/TP
qr.buy(1, "BTCUSDT", qty=0.01, limit=60000, target=70000, stoploss=55000)

# Positions
qr.get_positions(1)
qr.close_position(1)

# PnL
qr.get_pnl(1)
qr.get_history(1)

# Cleanup
qr.stop()
```

### SDK Reference

| Method | Description |
|--------|-------------|
| `qr.init(symbols=None)` | Initialize DB and start background daemon |
| `qr.stop()` | Stop the background daemon |
| `qr.get_price(symbol)` | Current market price |
| `qr.get_prices(symbols=None)` | Multiple prices |
| `qr.create_portfolio(name, cash=10000, description="")` | Create portfolio |
| `qr.list_portfolios()` | List all portfolios |
| `qr.get_portfolio(id)` | Get one portfolio |
| `qr.delete_portfolio(id)` | Delete portfolio |
| `qr.buy(pid, symbol, usd=N)` | Market buy by dollar amount |
| `qr.buy(pid, symbol, qty=N)` | Market buy by quantity |
| `qr.buy(pid, symbol, usd=N, limit=X, target=Y, stoploss=Z)` | Limit buy with SL/TP |
| `qr.sell(...)` | Same options as buy |
| `qr.cancel_order(order_id)` | Cancel pending order |
| `qr.get_positions(pid)` | Open positions with live PnL |
| `qr.close_position(pos_id)` | Close position at market |
| `qr.get_pnl(pid)` | Full PnL report |
| `qr.get_history(pid)` | Closed trade history |

## REST API

Start with `quantrun serve` or `uvicorn server:app --port 8000`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolios` | List portfolios |
| POST | `/api/portfolios` | Create portfolio |
| GET | `/api/portfolios/:id` | Get portfolio |
| DELETE | `/api/portfolios/:id` | Delete portfolio |
| POST | `/api/portfolios/:id/orders` | Place order |
| GET | `/api/portfolios/:id/orders` | List orders |
| DELETE | `/api/orders/:id` | Cancel order |
| GET | `/api/portfolios/:id/positions` | List positions |
| DELETE | `/api/positions/:id` | Close position |
| GET | `/api/portfolios/:id/pnl` | PnL report |
| GET | `/api/portfolios/:id/history` | Trade history |
| GET | `/api/prices` | All prices |
| GET | `/api/prices/:symbol` | Single price |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `ws://host:8000/ws/prices` | Live market prices (JSON: `{ prices: { SYMBOL: price, ... } }`) |
| `ws://host:8000/ws/portfolio/:id` | Live portfolio data (JSON: `{ pnl, positions, orders, portfolio }`) |

The frontend connects to both automatically. Prices update every ~1s. Portfolio data updates every ~2s.

## Error Handling

All API errors return structured JSON with the server's error message. The frontend displays toast notifications for every operation:

- **Success** — green toast (e.g. "ORDER FILLED: BUY 0.1 BTCUSDT @ $67432.50")
- **Error** — red toast with the exact server message (e.g. "Cannot delete portfolio with active positions", "Insufficient funds. Need 5000.00, have 1234.56")
- **Info** — yellow toast for warnings

Toasts auto-dismiss after 5 seconds or click to dismiss.

## React Frontend

```bash
cd frontend && npm install && npm run dev
```

Terminal-style dashboard with dark/light theme support, built with React + TypeScript + Vite + Recharts + Lucide icons.

### Features

- **Dark/Light Theme** — toggle between absolute-black dark mode and clean light mode
- **Sidebar Navigation** — portfolio list with truncation, market data link, theme toggle
- **Live Price Feed** — WebSocket-driven prices with no polling
- **Portfolio Tabs** — four tabs for Positions, Orders, History, and P&L
  - **Positions** — open positions with live PnL, inline SL/TP editor, exit button
  - **Orders** — pending limit orders with target/stoploss display, cancel button
  - **History** — all completed trades with win rate stats (win %, wins, losses)
  - **P&L** — summary cards, cumulative P&L area chart, per-trade bar chart
- **Trading Terminal** — order form with symbol search, side toggle, limit/target/SL
- **Chart Browser** — simulated price charts with live WebSocket prices overlaid
- **Coin Icons** — 497 real coin icons from `public/icons/` (SVG/PNG), with automatic fallback
- **Toast Notifications** — success/error feedback on every API action

### Frontend Structure

```
frontend/src/
├── api/
│   └── api.ts               # REST API client
├── hooks/
│   ├── useWs.ts             # usePricesWs, usePortfolioWs hooks
│   └── useToast.tsx          # Toast notification context + hook
├── components/
│   ├── Dashboard.tsx        # Main layout: sidebar + workspace
│   ├── PortfolioDetail.tsx  # Tabbed view: positions, orders, history, P&L
│   ├── TradingTerminal.tsx  # Order placement form
│   ├── ChartBrowser.tsx     # Simulated price charts
│   └── CoinIcon.tsx         # Coin icons from public/icons/
├── config.ts                # API_BASE config
├── App.tsx                  # Root component (wraps ToastProvider)
├── main.tsx                 # Entry point
└── index.css                # Global styles, theme variables
```

## Testing

```bash
# Unit + API tests (no server needed, uses mocked market data)
pytest tests/test_sdk.py tests/test_api.py -v

# WebSocket + stress tests (server must be running)
quantrun serve
pytest tests/test_websocket.py tests/test_stress.py -v -s

# Run everything
pytest tests/ -v
```

73 tests across 4 files:

| File | Tests | Coverage |
|------|-------|----------|
| `test_sdk.py` | 28 | SDK client — portfolio CRUD, orders, positions, PnL, history, prices |
| `test_api.py` | 27 | REST API — all endpoints via TestClient, including error cases |
| `test_websocket.py` | 9 | WebSocket — price stream, portfolio stream, concurrent connections |
| `test_stress.py` | 10 | Stress — bulk create, rapid orders, sustained WS streams, full lifecycle |

## Project Structure

```
quantrun-cli/
├── quantrun/
│   ├── cli.py                   # CLI entry point (Click)
│   ├── client.py                # Python SDK with background daemon
│   ├── config.py                # Settings
│   ├── db/
│   │   ├── database.py          # SQLite engine (WAL mode)
│   │   └── models.py            # SQLModel tables
│   ├── services/
│   │   ├── execution_engine.py  # In-memory order matching + SL/TP
│   │   ├── market_data.py       # Binance WebSocket streamer
│   │   ├── portfolio_manager.py # Business logic
│   │   └── brokers/
│   │       ├── base.py          # Abstract adapter interface
│   │       ├── registry.py      # Broker registry
│   │       └── crypto/binance.py
│   └── commands/
│       ├── portfolio.py
│       ├── order.py
│       ├── position.py
│       ├── market.py
│       ├── pnl.py
│       ├── stream.py
│       └── serve.py
├── tests/
│   ├── conftest.py              # Shared fixtures, mocked market data
│   ├── test_sdk.py              # SDK unit tests
│   ├── test_api.py              # REST API tests
│   ├── test_websocket.py        # WebSocket tests
│   └── test_stress.py           # Stress / load tests
├── frontend/                    # React + Vite + TypeScript
│   ├── public/icons/            # 497 coin icon SVGs/PNGs
│   ├── src/
│   │   ├── api/api.ts
│   │   ├── hooks/useWs.ts
│   │   ├── hooks/useToast.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── PortfolioDetail.tsx
│   │   │   ├── TradingTerminal.tsx
│   │   │   ├── ChartBrowser.tsx
│   │   │   └── CoinIcon.tsx
│   │   ├── config.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   └── package.json
├── server.py                    # FastAPI REST + WebSocket server
├── start.bat                    # Windows quick start
├── start.sh                     # Linux/Mac quick start
├── pytest.ini                   # Pytest config (asyncio_mode = auto)
├── setup.py                     # Package + CLI entry point
├── requirements.txt             # Python dependencies
├── .gitignore
└── README.md
```

## Adding Brokers

Implement `BrokerAdapter` and register it:

```python
# quantrun/services/brokers/crypto/kraken.py
from quantrun.services.brokers.base import BrokerAdapter

class KrakenAdapter(BrokerAdapter):
    @property
    def broker_name(self): return "kraken"
    @property
    def asset_class(self): return "crypto"
    @property
    def websocket_url(self): return "wss://ws.kraken.com/v2"

    def normalize_symbol(self, symbol): ...
    def denormalize_symbol(self, symbol): ...
    def stream_name(self, symbol): ...
    def process_message(self, data): ...
    async def fetch_price(self, symbol): ...
    async def fetch_historical_data(self, symbol, interval): ...
```

Register in `quantrun/services/brokers/__init__.py`:

```python
from .crypto.kraken import KrakenAdapter
_registry.register("kraken", KrakenAdapter)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `QUANTRUN_DB_PATH` | `./data/paper_trading.db` | Path to SQLite database |
