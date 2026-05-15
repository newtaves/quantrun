# Paper Trading API Documentation

This document provides a comprehensive reference for the `paper` trading engine's API, including request fields, types, and expected responses.

## Table of Contents
1. [Market Data](#market-data)
2. [Portfolio Management](#portfolio-management)
3. [Positions & Execution](#positions--execution)
4. [Orders](#orders)
5. [Analytics & History](#analytics--history)
6. [Service Internals](#service-internals)

---

## Market Data

### `GET /prices`
Returns current market prices for all symbols currently being tracked by the streamer.
- **Response**: `Dict[str, float]` (e.g., `{ "BTCUSDT": 64231.5, "ETHUSDT": 3450.2 }`)

### `GET /symbol/{symbol}`
Returns the latest price for a specific symbol.
- **Path Param**: `symbol` (str) - e.g., `BTCUSDT`
- **Response**:
  ```json
  {
    "symbol": "BTCUSDT",
    "price": 64231.5
  }
  ```

---

## Portfolio Management

### `POST /portfolio`
Create a new portfolio for a user.
- **Body (JSON)**:
  | Field | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `user_id` | int | Yes | Owner's user ID |
  | `name` | str | Yes | Name of the portfolio |
  | `description` | str | No | Optional description |
  | `available_cash` | decimal | No | Starting cash (defaults to 0) |

### `GET /portfolio`
List all portfolios for a user.
- **Query Params**:
  | Param | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `user_id` | int | Yes | User ID to filter by |

### `GET /portfolio/{portfolio_id}`
Retrieve a single portfolio's details.

### `PUT /portfolio/{portfolio_id}`
Update portfolio metadata.
- **Query Params**:
  | Param | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `name` | str | No | New name |
  | `description` | str | No | New description |

---

## Positions & Execution

### `GET /portfolio/{portfolio_id}/positions`
Returns all open positions with real-time unrealized PnL.
- **Response Fields per Position**:
  - `position_id`, `symbol`, `side` (BUY/SELL), `quantity`, `entry_price`, `current_price`, `unrealized_pnl`, `target`, `stoploss`, `opened_at`.

### `PUT /portfolio/{portfolio_id}/positions/{position_id}`
Update the Exit Strategy (Stoploss/Target) for an active position.
- **Query Params**:
  | Param | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `target` | decimal | No | New price level to take profit |
  | `stoploss` | decimal | No | New price level to cut losses |

### `DELETE /portfolio/{portfolio_id}/positions/{position_id}`
Manually close an open position at the current market price.
- **Reason**: Sets `exit_reason` to `MANUAL` in history.

---

## Orders

### `POST /order`
Place a new Order. If `limit_price` is omitted, it executes as a **Market Order** on the next price tick.
- **Body (JSON)**:
  | Field | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `portfolio_id` | int | Yes | Portfolio to assign the order to |
  | `symbol` | str | Yes | Trading symbol (e.g. BTCUSDT) |
  | `side` | str | Yes | `BUY` (Long) or `SELL` (Short) |
  | `quantity` | decimal | Yes | Amount to trade |
  | `limit_price` | decimal | No | If null, executes at market price |
  | `target` | decimal | No | Auto-close position at this price |
  | `stoploss` | decimal | No | Auto-close position at this price |

### `PUT /order/{order_id}`
Modify a **PENDING** order's levels before it is executed.
- **Query Params**: `limit_price`, `target`, `stoploss` (all optional).

### `DELETE /order/{order_id}`
Cancel a pending order. It will be marked as `CANCELLED` in the database.

---

## Analytics & History

### `GET /portfolio/{portfolio_id}/pnl`
Full PnL Report.
- **Returns**: `total_pnl`, `unrealized_pnl`, `realized_pnl`, `available_cash`, `invested_cash`, and a list of active positions.

### `GET /portfolio/{portfolio_id}/history`
Retrieve all closed trades for analytics.
- **Fields**: `entry_price`, `exit_price`, `realized_pnl`, `exit_reason` (STOPLOSS/TARGET/MANUAL), `opened_at`, `closed_at`.

---

## Service Internals

The system uses two primary services to maintain state and performance:

1.  **`OrderExecutor`**: An in-memory engine that holds sorted orderbooks and active positions. It processes every price tick from the websocket to ensure microsecond-level accuracy for SL/TP hits without hitting the database repeatedly.
2.  **`PortfolioManager`**: Handles the persistence layer and high-level business rules (like checking if you have enough cash before allowing an order).
