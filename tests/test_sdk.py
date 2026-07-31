"""Unit tests for the QuantRun SDK client."""
import pytest
from decimal import Decimal


class TestPortfolioCRUD:
    def test_create_portfolio(self, sdk):
        p = sdk.create_portfolio("TestFund", cash=50000, description="unit test")
        assert p.portfolio_id is not None
        assert p.name == "TestFund"
        assert p.available_cash == 50000.0

    def test_list_portfolios(self, sdk):
        sdk.create_portfolio("A", cash=1000)
        sdk.create_portfolio("B", cash=2000)
        portfolios = sdk.list_portfolios()
        assert len(portfolios) >= 2
        names = {p.name for p in portfolios}
        assert "A" in names
        assert "B" in names

    def test_get_portfolio(self, sdk):
        p = sdk.create_portfolio("GetMe", cash=7777)
        fetched = sdk.get_portfolio(p.portfolio_id)
        assert fetched is not None
        assert fetched.name == "GetMe"
        assert fetched.available_cash == 7777.0

    def test_get_nonexistent_portfolio(self, sdk):
        assert sdk.get_portfolio(99999) is None

    def test_delete_portfolio(self, sdk):
        p = sdk.create_portfolio("ToDelete", cash=100)
        sdk.delete_portfolio(p.portfolio_id)
        assert sdk.get_portfolio(p.portfolio_id) is None

    def test_delete_nonexistent_portfolio(self, sdk):
        with pytest.raises(ValueError, match="not found"):
            sdk.delete_portfolio(99999)


class TestOrders:
    def test_market_buy(self, sdk):
        p = sdk.create_portfolio("OrdTest", cash=100000)
        result = sdk.buy(p.portfolio_id, "BTCUSDT", usd=500)
        assert result.status == "EXECUTED"
        assert result.order_id is not None
        assert result.price is not None
        assert result.cost is not None

    def test_market_sell(self, sdk):
        p = sdk.create_portfolio("SellTest", cash=100000)
        # Buy first so we have something to sell
        buy = sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.01)
        assert buy.status == "EXECUTED"
        result = sdk.sell(p.portfolio_id, "BTCUSDT", qty=0.01)
        assert result.status == "EXECUTED"

    def test_limit_order(self, sdk):
        p = sdk.create_portfolio("LimitTest", cash=100000)
        result = sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.001, limit=60000)
        assert result.status == "PENDING"
        assert result.order_id is not None

    def test_order_with_target_and_stoploss(self, sdk):
        p = sdk.create_portfolio("SLTP", cash=100000)
        result = sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.001, limit=80000, target=90000, stoploss=75000)
        assert result.status == "PENDING"
        assert result.target == 90000.0
        assert result.stoploss == 75000.0

    def test_order_no_usd_or_qty(self, sdk):
        p = sdk.create_portfolio("Bad", cash=100000)
        result = sdk.buy(p.portfolio_id, "BTCUSDT")
        assert result.status == "ERROR"
        assert "Specify" in result.error

    def test_order_both_usd_and_qty(self, sdk):
        p = sdk.create_portfolio("Bad2", cash=100000)
        result = sdk.buy(p.portfolio_id, "BTCUSDT", usd=100, qty=0.01)
        assert result.status == "ERROR"

    def test_order_unknown_symbol(self, sdk):
        p = sdk.create_portfolio("BadSym", cash=100000)
        result = sdk.buy(p.portfolio_id, "FAKECOIN", usd=100)
        assert result.status == "ERROR"

    def test_cancel_order(self, sdk):
        p = sdk.create_portfolio("CancelTest", cash=100000)
        order = sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.001, limit=50000)
        assert order.status == "PENDING"
        sdk.cancel_order(order.order_id)
        # Verify cancelled
        from quantrun.db.models import Order, OrderStatus
        from quantrun.db import get_session
        session = get_session()
        try:
            o = session.get(Order, order.order_id)
            assert o.status == OrderStatus.CANCELLED
        finally:
            session.close()

    def test_cancel_nonexistent_order(self, sdk):
        with pytest.raises(ValueError, match="not found"):
            sdk.cancel_order(99999)


class TestPositions:
    def test_get_positions_empty(self, sdk):
        p = sdk.create_portfolio("PosTest", cash=100000)
        positions = sdk.get_positions(p.portfolio_id)
        assert positions == []

    def test_get_positions_after_buy(self, sdk):
        p = sdk.create_portfolio("PosBuy", cash=100000)
        sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.01)
        positions = sdk.get_positions(p.portfolio_id)
        assert len(positions) == 1
        assert positions[0].symbol == "BTCUSDT"
        assert positions[0].quantity == 0.01

    def test_close_position(self, sdk):
        p = sdk.create_portfolio("ClosePos", cash=100000)
        buy = sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.01)
        positions = sdk.get_positions(p.portfolio_id)
        assert len(positions) == 1
        sdk.close_position(positions[0].position_id)
        positions_after = sdk.get_positions(p.portfolio_id)
        assert len(positions_after) == 0

    def test_close_nonexistent_position(self, sdk):
        with pytest.raises(ValueError, match="not found"):
            sdk.close_position(99999)


class TestPnL:
    def test_pnl_empty_portfolio(self, sdk):
        p = sdk.create_portfolio("PnlEmpty", cash=100000)
        pnl = sdk.get_pnl(p.portfolio_id)
        assert pnl.total_pnl == 0
        assert pnl.realized_pnl == 0
        assert pnl.unrealized_pnl == 0

    def test_pnl_with_position(self, sdk):
        p = sdk.create_portfolio("PnlPos", cash=100000)
        sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.01)
        pnl = sdk.get_pnl(p.portfolio_id)
        assert len(pnl.positions) == 1
        assert pnl.positions[0].symbol == "BTCUSDT"

    def test_history_empty(self, sdk):
        p = sdk.create_portfolio("HistEmpty", cash=100000)
        history = sdk.get_history(p.portfolio_id)
        assert history == []

    def test_history_after_close(self, sdk):
        p = sdk.create_portfolio("HistClose", cash=100000)
        sdk.buy(p.portfolio_id, "BTCUSDT", qty=0.01)
        positions = sdk.get_positions(p.portfolio_id)
        sdk.close_position(positions[0].position_id)
        history = sdk.get_history(p.portfolio_id)
        assert len(history) == 1
        assert history[0]["symbol"] == "BTCUSDT"


class TestPrices:
    def test_get_single_price(self, sdk):
        price = sdk.get_price("BTCUSDT")
        assert price == 85000.0

    def test_get_multiple_prices(self, sdk):
        prices = sdk.get_prices(["BTCUSDT", "ETHUSDT"])
        assert "BTCUSDT" in prices
        assert "ETHUSDT" in prices
        assert prices["BTCUSDT"] == 85000.0

    def test_get_all_prices(self, sdk):
        prices = sdk.get_prices()
        assert len(prices) >= 4

    def test_unknown_symbol_price(self, sdk):
        price = sdk.get_price("FAKECOIN")
        assert price is None
