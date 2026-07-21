"""Tests for the FastAPI REST API endpoints using TestClient (no server needed)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(fresh_db):
    """Return a TestClient that hits the FastAPI app in-process."""
    from server import app
    return TestClient(app)


class TestPortfolioEndpoints:
    def test_list_portfolios_empty(self, client):
        r = client.get("/api/portfolios")
        assert r.status_code == 200
        assert r.json()["portfolios"] == []

    def test_create_portfolio(self, client):
        r = client.post("/api/portfolios", json={"name": "APIFund", "cash": 25000})
        assert r.status_code == 200
        data = r.json()["portfolio"]
        assert data["name"] == "APIFund"
        assert data["available_cash"] == 25000.0

    def test_list_portfolios_after_create(self, client):
        client.post("/api/portfolios", json={"name": "P1", "cash": 1000})
        client.post("/api/portfolios", json={"name": "P2", "cash": 2000})
        r = client.get("/api/portfolios")
        assert r.status_code == 200
        assert len(r.json()["portfolios"]) >= 2

    def test_get_portfolio(self, client):
        create = client.post("/api/portfolios", json={"name": "GetMe", "cash": 5000})
        pid = create.json()["portfolio"]["portfolio_id"]
        r = client.get(f"/api/portfolios/{pid}")
        assert r.status_code == 200
        assert r.json()["portfolio"]["name"] == "GetMe"

    def test_get_nonexistent_portfolio(self, client):
        r = client.get("/api/portfolios/99999")
        assert r.status_code == 404

    def test_delete_portfolio(self, client):
        create = client.post("/api/portfolios", json={"name": "Del", "cash": 100})
        pid = create.json()["portfolio"]["portfolio_id"]
        r = client.delete(f"/api/portfolios/{pid}")
        assert r.status_code == 200
        # Verify gone
        r2 = client.get(f"/api/portfolios/{pid}")
        assert r2.status_code == 404


class TestOrderEndpoints:
    def test_market_buy(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdBuy", "cash": 100000}).json()["portfolio"]
        r = client.post(f"/api/portfolios/{p['portfolio_id']}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "usd": 500,
        })
        assert r.status_code == 200
        assert r.json()["order"]["status"] == "EXECUTED"

    def test_market_sell(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdSell", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01,
        })
        r = client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "SELL", "qty": 0.01,
        })
        assert r.status_code == 200
        assert r.json()["order"]["status"] == "EXECUTED"

    def test_limit_order(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdLim", "cash": 100000}).json()["portfolio"]
        r = client.post(f"/api/portfolios/{p['portfolio_id']}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.001, "limit": 60000,
        })
        assert r.status_code == 200
        assert r.json()["order"]["status"] == "PENDING"

    def test_order_with_sl_tp(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdSLTP", "cash": 100000}).json()["portfolio"]
        r = client.post(f"/api/portfolios/{p['portfolio_id']}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.001,
            "limit": 80000, "target": 90000, "stoploss": 75000,
        })
        assert r.status_code == 200
        o = r.json()["order"]
        assert o["target"] == 90000.0
        assert o["stoploss"] == 75000.0

    def test_order_insufficient_funds(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdPoor", "cash": 1}).json()["portfolio"]
        r = client.post(f"/api/portfolios/{p['portfolio_id']}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "usd": 100,
        })
        assert r.status_code == 400

    def test_order_unknown_symbol(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdBad", "cash": 100000}).json()["portfolio"]
        r = client.post(f"/api/portfolios/{p['portfolio_id']}/orders", json={
            "symbol": "FAKECOIN", "side": "BUY", "usd": 100,
        })
        assert r.status_code == 400

    def test_list_orders(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdList", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.001, "limit": 50000,
        })
        r = client.get(f"/api/portfolios/{pid}/orders")
        assert r.status_code == 200
        assert len(r.json()["orders"]) >= 1

    def test_cancel_order(self, client):
        p = client.post("/api/portfolios", json={"name": "OrdCancel", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        order = client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.001, "limit": 50000,
        }).json()["order"]
        r = client.delete(f"/api/orders/{order['order_id']}")
        assert r.status_code == 200

    def test_cancel_nonexistent_order(self, client):
        r = client.delete("/api/orders/99999")
        assert r.status_code == 400


class TestPositionEndpoints:
    def test_list_positions_empty(self, client):
        p = client.post("/api/portfolios", json={"name": "PosEmpty", "cash": 100000}).json()["portfolio"]
        r = client.get(f"/api/portfolios/{p['portfolio_id']}/positions")
        assert r.status_code == 200
        assert r.json()["positions"] == []

    def test_list_positions_after_buy(self, client):
        p = client.post("/api/portfolios", json={"name": "PosBuy", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01,
        })
        r = client.get(f"/api/portfolios/{pid}/positions")
        assert r.status_code == 200
        assert len(r.json()["positions"]) == 1

    def test_close_position(self, client):
        p = client.post("/api/portfolios", json={"name": "PosClose", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01,
        })
        positions = client.get(f"/api/portfolios/{pid}/positions").json()["positions"]
        pos_id = positions[0]["position_id"]
        r = client.delete(f"/api/positions/{pos_id}")
        assert r.status_code == 200
        # Verify closed
        r2 = client.get(f"/api/portfolios/{pid}/positions")
        assert len(r2.json()["positions"]) == 0

    def test_close_nonexistent_position(self, client):
        r = client.delete("/api/positions/99999")
        assert r.status_code == 400


class TestPnLEndpoints:
    def test_pnl_empty(self, client):
        p = client.post("/api/portfolios", json={"name": "PnlEmpty", "cash": 100000}).json()["portfolio"]
        r = client.get(f"/api/portfolios/{p['portfolio_id']}/pnl")
        assert r.status_code == 200
        assert r.json()["pnl"]["total_pnl"] == 0

    def test_pnl_with_position(self, client):
        p = client.post("/api/portfolios", json={"name": "PnlPos", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01,
        })
        r = client.get(f"/api/portfolios/{pid}/pnl")
        assert r.status_code == 200
        assert len(r.json()["pnl"]["positions"]) == 1


class TestHistoryEndpoints:
    def test_history_empty(self, client):
        p = client.post("/api/portfolios", json={"name": "HistEmpty", "cash": 100000}).json()["portfolio"]
        r = client.get(f"/api/portfolios/{p['portfolio_id']}/history")
        assert r.status_code == 200
        assert r.json()["history"] == []

    def test_history_after_close(self, client):
        p = client.post("/api/portfolios", json={"name": "HistClose", "cash": 100000}).json()["portfolio"]
        pid = p["portfolio_id"]
        client.post(f"/api/portfolios/{pid}/orders", json={
            "symbol": "BTCUSDT", "side": "BUY", "qty": 0.01,
        })
        positions = client.get(f"/api/portfolios/{pid}/positions").json()["positions"]
        client.delete(f"/api/positions/{positions[0]['position_id']}")
        r = client.get(f"/api/portfolios/{pid}/history")
        assert r.status_code == 200
        assert len(r.json()["history"]) == 1


class TestPriceEndpoints:
    def test_get_all_prices(self, client):
        r = client.get("/api/prices")
        assert r.status_code == 200
        assert "BTCUSDT" in r.json()["prices"]

    def test_get_filtered_prices(self, client):
        r = client.get("/api/prices?symbols=BTCUSDT,ETHUSDT")
        assert r.status_code == 200
        prices = r.json()["prices"]
        assert "BTCUSDT" in prices
        assert "ETHUSDT" in prices

    def test_get_single_price(self, client):
        r = client.get("/api/prices/BTCUSDT")
        assert r.status_code == 200
        assert r.json()["price"] == 85000.0

    def test_get_unknown_price(self, client):
        r = client.get("/api/prices/FAKECOIN")
        assert r.status_code == 404
