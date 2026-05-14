from decimal import Decimal
from typing import List, Optional

from db.models import Portfolio, Order, Position


class PortfolioManager:
    """
    Service layer responsible for:
    - portfolio management
    - order management
    - pnl calculations
    - holdings retrieval
    - portfolio analytics
    """

    async def create_portfolio(self, data: Portfolio) -> Portfolio:
        """
        Create a new portfolio and store it in database.

        Responsibilities:
        - validate portfolio name
        - initialize balances
        - assign ownership
        - persist to database

        Parameters:
        - data: Portfolio object

        Returns:
        - Created Portfolio
        """
        ...

    async def get_portfolios(self, user_id: int) -> List[Portfolio]:
        """
        Fetch all portfolios owned by a user.

        Parameters:
        - user_id: User identifier

        Returns:
        - List of portfolios
        """
        ...

    async def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """
        Fetch a single portfolio by ID.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Portfolio if found
        """
        ...

    async def delete_portfolio(self, portfolio_id: int) -> None:
        """
        Delete a portfolio.

        Responsibilities:
        - validate no active positions
        - validate no pending orders
        - remove portfolio

        Parameters:
        - portfolio_id: Portfolio identifier
        """
        ...

    async def get_positions(self, portfolio_id: int) -> List[Position]:
        """
        Fetch all active positions
        belonging to a portfolio.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - List of active positions
        """
        ...

    async def get_position(self, position_id: int) -> Optional[Position]:
        """
        Fetch a single active position.

        Parameters:
        - position_id: Position identifier

        Returns:
        - Position if found
        """
        ...

    async def get_position_summary(self, portfolio_id: int) -> dict:
        """
        Fetch summarized position information.

        Includes:
        - invested capital
        - unrealized pnl
        - number of positions
        - exposure

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Position summary dictionary
        """
        ...

    async def get_available_cash(self, portfolio_id: int) -> Decimal:
        """
        Return currently available cash
        for trading.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Available cash
        """
        ...

    async def get_invested_cash(self, portfolio_id: int) -> Decimal:
        """
        Calculate total invested capital
        across all open positions.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Invested cash amount
        """
        ...

    async def calculate_total_pnl(self, portfolio_id: int) -> Decimal:
        """
        Calculate total portfolio pnl.

        Includes:
        - unrealized pnl
        - realized pnl

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Total pnl
        """
        ...

    async def calculate_unrealized_pnl(self, portfolio_id: int) -> Decimal:
        """
        Calculate unrealized pnl
        from active positions.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Unrealized pnl
        """
        ...

    async def calculate_realized_pnl(self, portfolio_id: int) -> Decimal:
        """
        Calculate realized pnl
        from closed trades.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - Realized pnl
        """
        ...

    async def generate_pnl_report(self, portfolio_id: int) -> dict:
        """
        Generate complete pnl report.

        Includes:
        - realized pnl
        - unrealized pnl
        - win/loss metrics
        - capital usage

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - PnL report dictionary
        """
        ...

    async def place_order(self, order: Order) -> Order:
        """
        Create and register a new order.

        Responsibilities:
        - validate available cash
        - validate order parameters
        - store pending order
        - send to execution engine

        Parameters:
        - order: Order object

        Returns:
        - Created order
        """
        ...

    async def modify_order(self, order_id: int, limit_price: Optional[Decimal] = None, target: Optional[Decimal] = None, stoploss: Optional[Decimal] = None ) -> Order:
        """
        Modify an existing pending order.

        Allowed modifications:
        - limit price
        - target
        - stoploss

        Parameters:
        - order_id: Order identifier
        - limit_price: Updated limit price
        - target: Updated target
        - stoploss: Updated stoploss

        Returns:
        - Updated order
        """
        ...

    async def cancel_order(self, order_id: int) -> None:
        """
        Cancel a pending order.

        Responsibilities:
        - mark order cancelled
        - remove from in-memory orderbook

        Parameters:
        - order_id: Order identifier
        """
        ...

    async def get_orders(self, portfolio_id: int, status: Optional[str] = None) -> List[Order]:
        """
        Fetch portfolio orders.

        Parameters:
        - portfolio_id: Portfolio identifier
        - status: Optional status filter

        Returns:
        - List of orders
        """
        ...

    async def get_order(self, order_id: int) -> Optional[Order]:
        """
        Fetch a single order.

        Parameters:
        - order_id: Order identifier

        Returns:
        - Order if found
        """
        ...

    async def get_pending_orders(self, portfolio_id: int) -> List[Order]:
        """
        Fetch all pending orders
        for a portfolio.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - List of pending orders
        """
        ...

    async def get_executed_orders(self, portfolio_id: int) -> List[Order]:
        """
        Fetch all executed orders
        for a portfolio.

        Parameters:
        - portfolio_id: Portfolio identifier

        Returns:
        - List of executed orders
        """
        ...

    async def update_portfolio_metrics(self, portfolio_id: int) -> None:
        """
        Recalculate and update portfolio metrics.

        Includes:
        - available cash
        - invested cash
        - total pnl

        Parameters:
        - portfolio_id: Portfolio identifier
        """
        ...