from .rpcMetaApiConnection import RpcMetaApiConnection
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from .models import MetatraderHistoryOrders, MetatraderDeals
from ..clients.metaApi.reconnectListener import ReconnectListener
from ..clients.metaApi.synchronizationListener import SynchronizationListener
from .metatraderAccount import MetatraderAccount
from ..clients.timeoutException import TimeoutException
from datetime import datetime, timedelta
from mock import MagicMock, AsyncMock
from .models import date
from typing import Coroutine
import pytest
import asyncio


class MockClient(MetaApiWebsocketClient):
    def get_account_information(self, account_id: str) -> asyncio.Future:
        pass

    def get_positions(self, account_id: str) -> asyncio.Future:
        pass

    def get_position(self, account_id: str, position_id: str) -> asyncio.Future:
        pass

    def get_orders(self, account_id: str) -> asyncio.Future:
        pass

    def get_order(self, account_id: str, order_id: str) -> asyncio.Future:
        pass

    def get_history_orders_by_ticket(self, account_id: str, ticket: str) -> MetatraderHistoryOrders:
        pass

    def get_history_orders_by_position(self, account_id: str, position_id: str) -> MetatraderHistoryOrders:
        pass

    def get_history_orders_by_time_range(self, account_id: str, start_time: datetime, end_time: datetime,
                                         offset=0, limit=1000) -> MetatraderHistoryOrders:
        pass

    def get_deals_by_ticket(self, account_id: str, ticket: str) -> MetatraderDeals:
        pass

    def get_deals_by_position(self, account_id: str, position_id: str) -> MetatraderDeals:
        pass

    def get_deals_by_time_range(self, account_id: str, start_time: datetime, end_time: datetime, offset: int = 0,
                                limit: int = 1000) -> MetatraderDeals:
        pass

    def remove_history(self, account_id: str, application: str = None) -> Coroutine:
        pass

    def trade(self, account_id: str, trade) -> asyncio.Future:
        pass

    def reconnect(self, account_id: str):
        pass

    def subscribe(self, account_id: str, instance_index: str = None):
        pass

    def add_synchronization_listener(self, account_id: str, listener):
        pass

    def add_reconnect_listener(self, listener: ReconnectListener, account_id: str):
        pass

    def remove_synchronization_listener(self, account_id: str, listener: SynchronizationListener):
        pass

    def get_symbol_specification(self, account_id: str, symbol: str) -> asyncio.Future:
        pass

    def get_symbol_price(self, account_id: str, symbol: str) -> asyncio.Future:
        pass

    async def wait_synchronized(self, account_id: str, instance_index: str, application_pattern: str,
                                timeout_in_seconds: float, application: str = None):
        pass

    def add_account_region(self, account_id: str, region: str):
        pass

    def remove_account_region(self, account_id: str):
        pass


class MockAccount(MetatraderAccount):

    def __init__(self, data, metatrader_account_client,
                 meta_api_websocket_client, connection_registry):
        super(MockAccount, self).__init__(data, metatrader_account_client, meta_api_websocket_client,
                                          connection_registry, MagicMock(), MagicMock(), 'MetaApi')
        self._state = 'DEPLOYED'

    @property
    def id(self):
        return 'accountId'

    @property
    def synchronization_mode(self):
        return 'user'

    @property
    def state(self):
        return self._state

    @property
    def reliability(self) -> str:
        return 'regular'

    async def reload(self):
        pass


class AutoMockAccount(MetatraderAccount):
    @property
    def id(self):
        return 'accountId'

    @property
    def synchronization_mode(self):
        return 'automatic'


account: MockAccount = None
auto_account: AutoMockAccount = None
client: MockClient = None
api: RpcMetaApiConnection = None
empty_hash = 'd41d8cd98f00b204e9800998ecf8427e'


@pytest.fixture(autouse=True)
async def run_around_tests():
    global account
    account = MockAccount(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    global auto_account
    auto_account = AutoMockAccount(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),
                                   'MetaApi')
    global client
    client = MockClient(MagicMock(), 'token')
    global api
    api = RpcMetaApiConnection(client, account)
    yield


class TestRpcMetaApiConnection:
    @pytest.mark.asyncio
    async def test_wait_synchronized(self):
        """Should wait until RPC application is synchronized."""
        await api.connect()
        client.wait_synchronized = AsyncMock(side_effect=[TimeoutException('timeout'), TimeoutException('timeout'),
                                                          MagicMock()])
        await api.wait_synchronized()

    @pytest.mark.asyncio
    async def test_timeout_synchronization(self):
        """Should time out waiting for synchronization."""
        await api.connect()
        async def wait_synchronized(account_id: str, instance_index: str, application_pattern: str,
                                    timeout_in_seconds: float, application: str = None):
            await asyncio.sleep(0.1)
            raise TimeoutException('timeout')

        client.wait_synchronized = wait_synchronized
        try:
            await api.wait_synchronized(0.09)
            raise Exception('TimeoutError is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'

    @pytest.mark.asyncio
    async def test_retrieve_account_information(self):
        """Should retrieve account information."""
        await api.connect()
        account_information = {
            'broker': 'True ECN Trading Ltd',
            'currency': 'USD',
            'server': 'ICMarketsSC-Demo',
            'balance': 7319.9,
            'equity': 7306.649913200001,
            'margin': 184.1,
            'freeMargin': 7120.22,
            'leverage': 100,
            'marginLevel': 3967.58283542
        }
        client.get_account_information = AsyncMock(return_value=account_information)
        actual = await api.get_account_information()
        assert actual == account_information
        client.get_account_information.assert_called_with('accountId')

    @pytest.mark.asyncio
    async def test_not_process_request_if_connection_not_open(self):
        """Should not process request if connection is not open."""
        try:
            await api.get_account_information()
            pytest.fail()
        except Exception as err:
            assert err.args[0] == 'This connection has not been initialized yet, please ' + \
                                  'invoke await connection.connect()'

    @pytest.mark.asyncio
    async def test_not_process_request_if_connection_closed(self):
        """Should not process request if connection is closed."""
        await api.connect()
        await api.close()
        try:
            await api.get_account_information()
            pytest.fail()
        except Exception as err:
            assert err.args[0] == 'This connection has been closed, please create a new connection'

    @pytest.mark.asyncio
    async def test_retrieve_positions(self):
        """Should retrieve positions."""
        await api.connect()
        positions = [{
            'id': '46214692',
            'type': 'POSITION_TYPE_BUY',
            'symbol': 'GBPUSD',
            'magic': 1000,
            'time': '2020-04-15T02:45:06.521Z',
            'updateTime': '2020-04-15T02:45:06.521Z',
            'openPrice': 1.26101,
            'currentPrice': 1.24883,
            'currentTickValue': 1,
            'volume': 0.07,
            'swap': 0,
            'profit': -85.25999999999966,
            'commission': -0.25,
            'clientId': 'TE_GBPUSD_7hyINWqAlE',
            'stopLoss': 1.17721,
            'unrealizedProfit': -85.25999999999901,
            'realizedProfit': -6.536993168992922e-13
        }]
        client.get_positions = AsyncMock(return_value=positions)
        actual = await api.get_positions()
        assert actual == positions
        client.get_positions.assert_called_with('accountId')

    @pytest.mark.asyncio
    async def test_retrieve_position_by_id(self):
        """Should retrieve position by id."""
        await api.connect()
        position = {
            'id': '46214692',
            'type': 'POSITION_TYPE_BUY',
            'symbol': 'GBPUSD',
            'magic': 1000,
            'time': '2020-04-15T02:45:06.521Z',
            'updateTime': '2020-04-15T02:45:06.521Z',
            'openPrice': 1.26101,
            'currentPrice': 1.24883,
            'currentTickValue': 1,
            'volume': 0.07,
            'swap': 0,
            'profit': -85.25999999999966,
            'commission': -0.25,
            'clientId': 'TE_GBPUSD_7hyINWqAlE',
            'stopLoss': 1.17721,
            'unrealizedProfit': -85.25999999999901,
            'realizedProfit': -6.536993168992922e-13
        }
        client.get_position = AsyncMock(return_value=position)
        actual = await api.get_position('46214692')
        assert actual == position
        client.get_position.assert_called_with('accountId', '46214692')

    @pytest.mark.asyncio
    async def test_retrieve_orders(self):
        """Should retrieve orders."""
        await api.connect()
        orders = [{
            'id': '46871284',
            'type': 'ORDER_TYPE_BUY_LIMIT',
            'state': 'ORDER_STATE_PLACED',
            'symbol': 'AUDNZD',
            'magic': 123456,
            'platform': 'mt5',
            'time': '2020-04-20T08:38:58.270Z',
            'openPrice': 1.03,
            'currentPrice': 1.05206,
            'volume': 0.01,
            'currentVolume': 0.01,
            'comment': 'COMMENT2'
        }]
        client.get_orders = AsyncMock(return_value=orders)
        actual = await api.get_orders()
        assert actual == orders
        client.get_orders.assert_called_with('accountId')

    @pytest.mark.asyncio
    async def test_retrieve_order_by_id(self):
        """Should retrieve order by id."""
        await api.connect()
        order = {
            'id': '46871284',
            'type': 'ORDER_TYPE_BUY_LIMIT',
            'state': 'ORDER_STATE_PLACED',
            'symbol': 'AUDNZD',
            'magic': 123456,
            'platform': 'mt5',
            'time': '2020-04-20T08:38:58.270Z',
            'openPrice': 1.03,
            'currentPrice': 1.05206,
            'volume': 0.01,
            'currentVolume': 0.01,
            'comment': 'COMMENT2'
        }
        client.get_order = AsyncMock(return_value=order)
        actual = await api.get_order('46871284')
        assert actual == order
        client.get_order.assert_called_with('accountId', '46871284')

    @pytest.mark.asyncio
    async def test_retrieve_history_orders_by_ticket(self):
        """Should retrieve history orders by ticket."""
        await api.connect()
        history_orders = {
            'historyOrders': [{
                'clientId': 'TE_GBPUSD_7hyINWqAlE',
                'currentPrice': 1.261,
                'currentVolume': 0,
                'doneTime': '2020-04-15T02:45:06.521Z',
                'id': '46214692',
                'magic': 1000,
                'platform': 'mt5',
                'positionId': '46214692',
                'state': 'ORDER_STATE_FILLED',
                'symbol': 'GBPUSD',
                'time': '2020-04-15T02:45:06.260Z',
                'type': 'ORDER_TYPE_BUY',
                'volume': 0.07
                }],
            'synchronizing': False
        }
        client.get_history_orders_by_ticket = AsyncMock(return_value=history_orders)
        actual = await api.get_history_orders_by_ticket('46214692')
        assert actual == history_orders
        client.get_history_orders_by_ticket.assert_called_with('accountId', '46214692')

    @pytest.mark.asyncio
    async def test_retrieve_history_orders_by_position(self):
        """Should retrieve history orders by position."""
        await api.connect()
        history_orders = {
            'historyOrders': [{
                'clientId': 'TE_GBPUSD_7hyINWqAlE',
                'currentPrice': 1.261,
                'currentVolume': 0,
                'doneTime': '2020-04-15T02:45:06.521Z',
                'id': '46214692',
                'magic': 1000,
                'platform': 'mt5',
                'positionId': '46214692',
                'state': 'ORDER_STATE_FILLED',
                'symbol': 'GBPUSD',
                'time': '2020-04-15T02:45:06.260Z',
                'type': 'ORDER_TYPE_BUY',
                'volume': 0.07
            }],
            'synchronizing': False
        }
        client.get_history_orders_by_position = AsyncMock(return_value=history_orders)
        actual = await api.get_history_orders_by_position('46214692')
        assert actual == history_orders
        client.get_history_orders_by_position.assert_called_with('accountId', '46214692')

    @pytest.mark.asyncio
    async def test_retrieve_history_orders_by_time_range(self):
        """Should retrieve history orders by time range."""
        await api.connect()
        history_orders = {
            'historyOrders': [{
                'clientId': 'TE_GBPUSD_7hyINWqAlE',
                'currentPrice': 1.261,
                'currentVolume': 0,
                'doneTime': '2020-04-15T02:45:06.521Z',
                'id': '46214692',
                'magic': 1000,
                'platform': 'mt5',
                'positionId': '46214692',
                'state': 'ORDER_STATE_FILLED',
                'symbol': 'GBPUSD',
                'time': '2020-04-15T02:45:06.260Z',
                'type': 'ORDER_TYPE_BUY',
                'volume': 0.07
            }],
            'synchronizing': False
        }
        client.get_history_orders_by_time_range = AsyncMock(return_value=history_orders)
        start_time = datetime.now() - timedelta(seconds=1)
        end_time = datetime.now()
        actual = await api.get_history_orders_by_time_range(start_time, end_time, 1, 100)
        assert actual == history_orders
        client.get_history_orders_by_time_range.assert_called_with('accountId', start_time, end_time, 1, 100)

    @pytest.mark.asyncio
    async def test_retrieve_history_deals_by_ticket(self):
        """Should retrieve history deals by ticket."""
        await api.connect()
        deals = {
            'deals': [{
                'clientId': 'TE_GBPUSD_7hyINWqAlE',
                'commission': -0.25,
                'entryType': 'DEAL_ENTRY_IN',
                'id': '33230099',
                'magic': 1000,
                'platform': 'mt5',
                'orderId': '46214692',
                'positionId': '46214692',
                'price': 1.26101,
                'profit': 0,
                'swap': 0,
                'symbol': 'GBPUSD',
                'time': '2020-04-15T02:45:06.521Z',
                'type': 'DEAL_TYPE_BUY',
                'volume': 0.07
            }],
            'synchronizing': False
        }
        client.get_deals_by_ticket = AsyncMock(return_value=deals)
        actual = await api.get_deals_by_ticket('46214692')
        assert actual == deals
        client.get_deals_by_ticket.assert_called_with('accountId', '46214692')

    @pytest.mark.asyncio
    async def test_retrieve_history_deals_by_position(self):
        """Should retrieve history deals by position."""
        await api.connect()
        deals = {
            'deals': [{
                'clientId': 'TE_GBPUSD_7hyINWqAlE',
                'commission': -0.25,
                'entryType': 'DEAL_ENTRY_IN',
                'id': '33230099',
                'magic': 1000,
                'platform': 'mt5',
                'orderId': '46214692',
                'positionId': '46214692',
                'price': 1.26101,
                'profit': 0,
                'swap': 0,
                'symbol': 'GBPUSD',
                'time': '2020-04-15T02:45:06.521Z',
                'type': 'DEAL_TYPE_BUY',
                'volume': 0.07
            }],
            'synchronizing': False
        }
        client.get_deals_by_position = AsyncMock(return_value=deals)
        actual = await api.get_deals_by_position('46214692')
        assert actual == deals
        client.get_deals_by_position.assert_called_with('accountId', '46214692')

    @pytest.mark.asyncio
    async def test_retrieve_history_deals_by_time_range(self):
        """Should retrieve history deals by time range."""
        await api.connect()
        deals = {
            'deals': [{
                'clientId': 'TE_GBPUSD_7hyINWqAlE',
                'commission': -0.25,
                'entryType': 'DEAL_ENTRY_IN',
                'id': '33230099',
                'magic': 1000,
                'platform': 'mt5',
                'orderId': '46214692',
                'positionId': '46214692',
                'price': 1.26101,
                'profit': 0,
                'swap': 0,
                'symbol': 'GBPUSD',
                'time': '2020-04-15T02:45:06.521Z',
                'type': 'DEAL_TYPE_BUY',
                'volume': 0.07
            }],
            'synchronizing': False
        }
        client.get_deals_by_time_range = AsyncMock(return_value=deals)
        start_time = datetime.now() - timedelta(seconds=1)
        end_time = datetime.now()
        actual = await api.get_deals_by_time_range(start_time, end_time, 1, 100)
        assert actual == deals
        client.get_deals_by_time_range.assert_called_with('accountId', start_time, end_time, 1, 100)

    @pytest.mark.asyncio
    async def test_create_market_buy_order(self):
        """Should create market buy order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_market_buy_order('GBPUSD', 0.07, 0.9, 2.0, {'comment': 'comment',
                                                                              'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_BUY', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'stopLoss': 0.9, 'takeProfit': 2.0,
                                                      'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'},
                                        'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_market_buy_order_with_relative_sl_tp(self):
        """Should create market buy order with relative SL/TP."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_market_buy_order('GBPUSD', 0.07, {'value': 0.1, 'units': 'RELATIVE_PRICE'},
                                                   {'value': 2000, 'units': 'RELATIVE_POINTS'},
                                                   {'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_BUY', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'stopLoss': 0.1,
                                                      'stopLossUnits': 'RELATIVE_PRICE', 'takeProfit': 2000,
                                                      'takeProfitUnits': 'RELATIVE_POINTS', 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_market_sell_order(self):
        """Should create market sell order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_market_sell_order('GBPUSD', 0.07, 0.9, 2.0, {'comment': 'comment',
                                                                               'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_SELL', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'stopLoss': 0.9, 'takeProfit': 2.0,
                                                      'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'},
                                        'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_limit_buy_order(self):
        """Should create limit buy order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_limit_buy_order('GBPUSD', 0.07, 1.0, 0.9, 2.0, {'comment': 'comment',
                                                                                  'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_BUY_LIMIT', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'openPrice': 1.0, 'stopLoss': 0.9,
                                                      'takeProfit': 2.0, 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_limit_sell_order(self):
        """Should create limit sell order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_limit_sell_order('GBPUSD', 0.07, 1.0, 0.9, 2.0, {'comment': 'comment',
                                                                                   'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_SELL_LIMIT', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'openPrice': 1.0, 'stopLoss': 0.9,
                                                      'takeProfit': 2.0, 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_stop_buy_order(self):
        """Should create stop buy order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_stop_buy_order('GBPUSD', 0.07, 1.0, 0.9, 2.0, {'comment': 'comment',
                                                                                 'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_BUY_STOP', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'openPrice': 1.0, 'stopLoss': 0.9,
                                                      'takeProfit': 2.0, 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_stop_sell_order(self):
        """Should create stop sell order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_stop_sell_order('GBPUSD', 0.07, 1.0, 0.9, 2.0, {'comment': 'comment',
                                                                                  'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_SELL_STOP', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'openPrice': 1.0, 'stopLoss': 0.9,
                                                      'takeProfit': 2.0, 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_stop_limit_buy_order(self):
        """Should create stop limit buy order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_stop_limit_buy_order('GBPUSD', 0.07, 1.5, 1.4, 0.9, 2.0, {
            'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_BUY_STOP_LIMIT', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'openPrice': 1.5, 'stopLimitPrice': 1.4,
                                                      'stopLoss': 0.9, 'takeProfit': 2.0, 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_create_stop_limit_sell_order(self):
        """Should create stop limit sell order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.create_stop_limit_sell_order('GBPUSD', 0.07, 1.0, 1.1, 2.0, 0.9, {
            'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_TYPE_SELL_STOP_LIMIT', 'symbol': 'GBPUSD',
                                                      'volume': 0.07, 'openPrice': 1.0, 'stopLimitPrice': 1.1,
                                                      'stopLoss': 2.0, 'takeProfit': 0.9, 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_modify_position(self):
        """Should modify position."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.modify_position('46870472', 2.0, 0.9)
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'POSITION_MODIFY', 'positionId': '46870472',
                                                      'stopLoss': 2.0, 'takeProfit': 0.9}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_close_position_partially(self):
        """Should close position partially."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.close_position_partially('46870472', 0.9)
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'POSITION_PARTIAL', 'positionId': '46870472',
                                                      'volume': 0.9}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_close_position(self):
        """Should close position."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.close_position('46870472')
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'POSITION_CLOSE_ID', 'positionId': '46870472'},
                                        'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_close_position_by_opposite(self):
        """Should close position by an opposite one."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'positionId': '46870472',
            'closeByPositionId': '46870482'
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.close_by('46870472', '46870482', {'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'})
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'POSITION_CLOSE_BY', 'positionId': '46870472',
                                                      'closeByPositionId': '46870482', 'comment': 'comment',
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, 'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_close_positions_by_symbol(self):
        """Should close positions by symbol."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.close_positions_by_symbol('EURUSD')
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'POSITIONS_CLOSE_SYMBOL', 'symbol': 'EURUSD'},
                                        'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_modify_order(self):
        """Should modify order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.modify_order('46870472', 1.0, 2.0, 0.9)
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_MODIFY', 'orderId': '46870472',
                                                      'openPrice': 1.0, 'stopLoss': 2.0, 'takeProfit': 0.9},
                                        'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """Should cancel order."""
        await api.connect()
        trade_result = {
            'error': 10009,
            'description': 'TRADE_RETCODE_DONE',
            'orderId': 46870472
        }
        client.trade = AsyncMock(return_value=trade_result)
        actual = await api.cancel_order('46870472')
        assert actual == trade_result
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_CANCEL', 'orderId': '46870472'},
                                        'RPC', 'regular')

    @pytest.mark.asyncio
    async def test_calculate_margin(self):
        """Should calculate margin."""
        await api.connect()
        margin = {
            'margin': 110
        }
        order = {
            'symbol': 'EURUSD',
            'type': 'ORDER_TYPE_BUY',
            'volume': 0.1,
            'openPrice': 1.1
        }
        client.calculate_margin = AsyncMock(return_value=margin)
        actual = await api.calculate_margin(order)
        assert actual == margin
        client.calculate_margin.assert_called_with('accountId', 'RPC', 'regular', order)

    @pytest.mark.asyncio
    async def test_retrieve_symbols(self):
        """Should retrieve symbols."""
        await api.connect()
        symbols = ['EURUSD']
        client.get_symbols = AsyncMock(return_value=symbols)
        actual = await api.get_symbols()
        assert actual == symbols
        client.get_symbols.assert_called_with('accountId')

    @pytest.mark.asyncio
    async def test_retrieve_symbol_specification(self):
        """Should retrieve symbol specification."""
        await api.connect()
        specification = {
            'symbol': 'AUDNZD',
            'tickSize': 0.00001,
            'minVolume': 0.01,
            'maxVolume': 100,
            'volumeStep': 0.01
        }
        client.get_symbol_specification = AsyncMock(return_value=specification)
        actual = await api.get_symbol_specification('AUDNZD')
        assert actual == specification
        client.get_symbol_specification.assert_called_with('accountId', 'AUDNZD')

    @pytest.mark.asyncio
    async def test_retrieve_symbol_price(self):
        """Should retrieve symbol price."""
        await api.connect()
        price = {
            'symbol': 'AUDNZD',
            'bid': 1.05297,
            'ask': 1.05309,
            'profitTickValue': 0.59731,
            'lossTickValue': 0.59736
        }
        client.get_symbol_price = AsyncMock(return_value=price)
        actual = await api.get_symbol_price('AUDNZD', True)
        assert actual == price

        client.get_symbol_price.assert_called_with('accountId', 'AUDNZD', True)

    @pytest.mark.asyncio
    async def test_retrieve_current_candle(self):
        """Should retrieve current candle."""
        await api.connect()
        candle = {
            'symbol': 'AUDNZD',
            'timeframe': '15m',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'open': 1.03297,
            'high': 1.06309,
            'low': 1.02705,
            'close': 1.043,
            'tickVolume': 1435,
            'spread': 17,
            'volume': 345
        }
        client.get_candle = AsyncMock(return_value=candle)
        actual = await api.get_candle('AUDNZD', '15m', True)
        candle['time'] = date(candle['time'])
        assert actual == candle
        client.get_candle.assert_called_with('accountId', 'AUDNZD', '15m', True)

    @pytest.mark.asyncio
    async def test_retrieve_latest_tick(self):
        """Should retrieve latest tick."""
        await api.connect()
        tick = {
            'symbol': 'AUDNZD',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'bid': 1.05297,
            'ask': 1.05309,
            'last': 0.5298,
            'volume': 0.13,
            'side': 'buy'
        }
        client.get_tick = AsyncMock(return_value=tick)
        actual = await api.get_tick('AUDNZD', True)
        tick['time'] = date(tick['time'])
        assert actual == tick
        client.get_tick.assert_called_with('accountId', 'AUDNZD', True)

    @pytest.mark.asyncio
    async def test_retrieve_latest_order_book(self):
        """Should retrieve latest order book."""
        await api.connect()
        book = {
            'symbol': 'AUDNZD',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'book': [
                {
                    'type': 'BOOK_TYPE_SELL',
                    'price': 1.05309,
                    'volume': 5.67
                },
                {
                    'type': 'BOOK_TYPE_BUY',
                    'price': 1.05297,
                    'volume': 3.45
                }
            ]
        }
        client.get_book = AsyncMock(return_value=book)
        actual = await api.get_book('AUDNZD', True)
        book['time'] = date(book['time'])
        assert actual == book
        client.get_book.assert_called_with('accountId', 'AUDNZD', True)

    @pytest.mark.asyncio
    async def test_retrieve_latest_server_time(self):
        """Should retrieve latest server time."""
        await api.connect()
        server_time = {
            'time': date('2022-01-01T00:00:00.000Z'),
            'brokerTime': '2022-01-01 02:00:00.000Z'
        }
        client.get_server_time = AsyncMock(return_value=server_time)
        actual = await api.get_server_time()
        assert actual == server_time
        client.get_server_time.assert_called_with('accountId')
