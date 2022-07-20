from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from .metatraderAccountModel import MetatraderAccountModel
from .models import MetatraderSymbolSpecification, MetatraderAccountInformation, MetatraderPosition, MetatraderOrder, \
    MetatraderHistoryOrders, MetatraderDeals, MetatraderSymbolPrice, MetatraderCandle, MetatraderTick, MetatraderBook,\
    ServerTime
from datetime import datetime
from typing import Coroutine, List
import asyncio
from ..logger import LoggerManager
from .metaApiConnection import MetaApiConnection


class RpcMetaApiConnection(MetaApiConnection):
    """Exposes MetaApi MetaTrader RPC API connection to consumers."""

    def __init__(self, websocket_client: MetaApiWebsocketClient, account: MetatraderAccountModel):
        """Inits MetaApi MetaTrader RPC Api connection.

        Args:
            websocket_client: MetaApi websocket client.
            account: MetaTrader account id to connect to.
        """
        super().__init__(websocket_client, account, 'RPC')
        self._logger = LoggerManager.get_logger('RpcMetaApiConnection')

    async def connect(self):
        """Opens the connection. Can only be called the first time, next calls will be ignored.

        Returns:
            A coroutine resolving when the connection is opened
        """
        if not self._opened:
            self._opened = True
            self._websocketClient.add_account_region(self.account.id, self.account.region)

    async def close(self):
        """Closes the connection. The instance of the class should no longer be used after this method is invoked."""
        if not self._closed:
            self._websocketClient.remove_account_region(self.account.id)
            self._closed = True

    def get_account_information(self) -> 'Coroutine[asyncio.Future[MetatraderAccountInformation]]':
        """Returns account information (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readAccountInformation/).

        Returns:
            A coroutine resolving with account information.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_account_information(self._account.id)

    def get_positions(self) -> 'Coroutine[asyncio.Future[List[MetatraderPosition]]]':
        """Returns positions (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readPositions/).

        Returns:
            A coroutine resolving with array of open positions.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_positions(self._account.id)

    def get_position(self, position_id: str) -> 'Coroutine[asyncio.Future[MetatraderPosition]]':
        """Returns specific position (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readPosition/).

        Args:
            position_id: Position id.

        Returns:
            A coroutine resolving with MetaTrader position found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_position(self._account.id, position_id)

    def get_orders(self) -> 'Coroutine[asyncio.Future[List[MetatraderOrder]]]':
        """Returns open orders (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readOrders/).

        Returns:
            A coroutine resolving with open MetaTrader orders.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_orders(self._account.id)

    def get_order(self, order_id: str) -> 'Coroutine[asyncio.Future[MetatraderOrder]]':
        """Returns specific open order (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readOrder/).

        Args:
            order_id: Order id (ticket number).

        Returns:
            A coroutine resolving with metatrader order found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_order(self._account.id, order_id)

    def get_history_orders_by_ticket(self, ticket: str) -> 'Coroutine[MetatraderHistoryOrders]':
        """Returns the history of completed orders for a specific ticket number (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readHistoryOrdersByTicket/).

        Args:
            ticket: Ticket number (order id).

        Returns:
            A coroutine resolving with request results containing history orders found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_history_orders_by_ticket(self._account.id, ticket)

    def get_history_orders_by_position(self, position_id: str) -> 'Coroutine[MetatraderHistoryOrders]':
        """Returns the history of completed orders for a specific position id (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readHistoryOrdersByPosition/)

        Args:
            position_id: Position id.

        Returns:
            A coroutine resolving with request results containing history orders found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_history_orders_by_position(self._account.id, position_id)

    def get_history_orders_by_time_range(self, start_time: datetime, end_time: datetime, offset: int = 0,
                                         limit: int = 1000) -> 'Coroutine[MetatraderHistoryOrders]':
        """Returns the history of completed orders for a specific time range (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readHistoryOrdersByTimeRange/)

        Args:
            start_time: Start of time range, inclusive.
            end_time: End of time range, exclusive.
            offset: Pagination offset, default is 0.
            limit: Pagination limit, default is 1000.

        Returns:
            A coroutine resolving with request results containing history orders found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_history_orders_by_time_range(self._account.id, start_time, end_time,
                                                                      offset, limit)

    def get_deals_by_ticket(self, ticket: str) -> 'Coroutine[MetatraderDeals]':
        """Returns history deals with a specific ticket number (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readDealsByTicket/).

        Args:
            ticket: Ticket number (deal id for MT5 or order id for MT4).

        Returns:
            A coroutine resolving with request results containing deals found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_deals_by_ticket(self._account.id, ticket)

    def get_deals_by_position(self, position_id) -> 'Coroutine[MetatraderDeals]':
        """Returns history deals for a specific position id (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readDealsByPosition/).

        Args:
            position_id: Position id.

        Returns:
            A coroutine resolving with request results containing deals found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_deals_by_position(self._account.id, position_id)

    def get_deals_by_time_range(self, start_time: datetime, end_time: datetime, offset: int = 0,
                                limit: int = 1000) -> 'Coroutine[MetatraderDeals]':
        """Returns history deals with for a specific time range (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readDealsByTimeRange/).

        Args:
            start_time: Start of time range, inclusive.
            end_time: End of time range, exclusive.
            offset: Pagination offset, default is 0.
            limit: Pagination limit, default is 1000.

        Returns:
            A coroutine resolving with request results containing deals found.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_deals_by_time_range(self._account.id, start_time, end_time, offset, limit)

    def get_symbols(self) -> 'Coroutine[asyncio.Future[List[str]]]':
        """Retrieves available symbols for an account (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readSymbols/).

        Returns:
            A coroutine which resolves when symbols are retrieved.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_symbols(self._account.id)

    def get_symbol_specification(self, symbol: str) -> 'Coroutine[asyncio.Future[MetatraderSymbolSpecification]]':
        """Retrieves specification for a symbol (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readSymbolSpecification/).

        Args:
            symbol: Symbol to retrieve specification for.

        Returns:
            A coroutine which resolves when specification MetatraderSymbolSpecification is retrieved.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_symbol_specification(self._account.id, symbol)

    def get_symbol_price(self, symbol: str, keep_subscription: bool = False) -> \
            'Coroutine[asyncio.Future[MetatraderSymbolPrice]]':
        """Retrieves latest price for a symbol (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readSymbolPrice/).

        Args:
            symbol: Symbol to retrieve price for.
            keep_subscription: if set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when price MetatraderSymbolPrice is retrieved.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_symbol_price(self._account.id, symbol, keep_subscription)

    def get_candle(self, symbol: str, timeframe: str, keep_subscription: bool = False) -> \
            'Coroutine[asyncio.Future[MetatraderCandle]]':
        """Retrieves latest candle for a symbol and timeframe (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readCandle/).

        Args:
            symbol: Symbol to retrieve candle for.
            timeframe: Defines the timeframe according to which the candle must be generated. Allowed values for
            MT5 are 1m, 2m, 3m, 4m, 5m, 6m, 10m, 12m, 15m, 20m, 30m, 1h, 2h, 3h, 4h, 6h, 8h, 12h, 1d, 1w, 1mn.
            Allowed values for MT4 are 1m, 5m, 15m 30m, 1h, 4h, 1d, 1w, 1mn.
            keep_subscription: if set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when candle is retrieved.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_candle(self._account.id, symbol, timeframe, keep_subscription)

    def get_tick(self, symbol: str, keep_subscription: bool = False) -> 'Coroutine[asyncio.Future[MetatraderTick]]':
        """Retrieves latest tick for a symbol. MT4 G1 accounts do not support this API (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readTick/).

        Args:
            symbol: Symbol to retrieve tick for.
            keep_subscription: if set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when tick is retrieved.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_tick(self._account.id, symbol, keep_subscription)

    def get_book(self, symbol: str, keep_subscription: bool = False) -> 'Coroutine[asyncio.Future[MetatraderBook]]':
        """Retrieves latest order book for a symbol. MT4 G1 accounts do not support this API (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readBook/).

        Args:
            symbol: Symbol to retrieve order book for.
            keep_subscription: if set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when order book is retrieved.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_book(self._account.id, symbol, keep_subscription)

    def get_server_time(self) -> 'Coroutine[asyncio.Future[ServerTime]]':
        """Returns server time for a specified MetaTrader account (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readServerTime/).

        Returns:
            A coroutine resolving with server time.
        """
        self._check_is_connection_active()
        return self._websocketClient.get_server_time(self._account.id)

    async def wait_synchronized(self, timeout_in_seconds: float = 300):
        """Waits until synchronization to RPC application is completed.

        Args:
            timeout_in_seconds: Timeout for synchronization.

        Returns:
            A coroutine which resolves when synchronization to RPC application is completed.

        Raises:
            TimeoutException: If application failed to synchronize with the terminal within timeout allowed.
        """
        self._check_is_connection_active()
        start_time = datetime.now().timestamp()
        while True:
            try:
                await self._websocketClient.wait_synchronized(self._account.id, None, 'RPC', 5, 'RPC')
                break
            except Exception as err:
                if datetime.now().timestamp() > start_time + timeout_in_seconds:
                    raise err
