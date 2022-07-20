from .streamingMetaApiConnection import StreamingMetaApiConnection
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from .models import MetatraderHistoryOrders, MetatraderDeals
from ..clients.metaApi.reconnectListener import ReconnectListener
from ..clients.metaApi.synchronizationListener import SynchronizationListener
from ..clients.metaApi.clientApi_client import ClientApiClient
from .metatraderAccount import MetatraderAccount
from datetime import datetime
from .historyStorage import HistoryStorage
from mock import MagicMock, AsyncMock, patch, ANY
from .models import date
from typing import Coroutine
import pytest
import asyncio
from asyncio import sleep


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

    def synchronize(self, account_id: str, instance_index: str, synchronization_id: str,
                    starting_history_order_time: datetime, starting_deal_time: datetime) -> Coroutine:
        pass

    def subscribe(self, account_id: str, instance_index: str = None):
        pass

    def subscribe_to_market_data(self, account_id: str, instance_index: str, symbol: str) -> Coroutine:
        pass

    def unsubscribe_from_market_data(self, account_id: str, instance_index: str, symbol: str) -> Coroutine:
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
                                timeout_in_seconds: float):
        pass


class MockAccount(MetatraderAccount):

    def __init__(self, data, metatrader_account_client,
                 meta_api_websocket_client, connection_registry, application):
        super(MockAccount, self).__init__(data, metatrader_account_client, meta_api_websocket_client,
                                          connection_registry, MagicMock(), MagicMock(), application)
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
    def reliability(self) -> str:
        return 'regular'

    @property
    def synchronization_mode(self):
        return 'automatic'


storage: HistoryStorage = None
account: MockAccount = None
auto_account: AutoMockAccount = None
client: MockClient = None
client_api_client: ClientApiClient = None
api: StreamingMetaApiConnection = None


@pytest.fixture(autouse=True)
async def run_around_tests():
    global account
    account = MockAccount(MagicMock(), MagicMock(), MagicMock(), MagicMock(), 'MetaApi')
    global auto_account
    auto_account = AutoMockAccount(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(),
                                   'MetaApi')
    global client
    client = MockClient(MagicMock(), 'token')
    global storage
    storage = MagicMock()
    storage.initialize = AsyncMock()
    storage.last_history_order_time = AsyncMock(return_value=datetime.now())
    storage.last_deal_time = AsyncMock(return_value=datetime.now())
    storage.on_history_order_added = AsyncMock()
    storage.on_deal_added = AsyncMock()
    global client_api_client
    client_api_client = MagicMock()
    client_api_client.get_hashing_ignored_field_lists = AsyncMock(return_value={
        'g1': {
            'specification': [
                'description',
            ],
            'position': [
                'time',
            ],
            'order': [
                'time',
            ]
        },
        'g2': {
            'specification': [
                'pipSize'
            ],
            'position': [
                'comment',
            ],
            'order': [
                'comment',
            ]
        }
    })
    global api
    registry = MagicMock()
    registry.connect = MagicMock()
    api = StreamingMetaApiConnection(client, client_api_client, account, storage, registry)
    api.terminal_state.specification = MagicMock(return_value={'symbol': 'EURUSD'})
    yield
    api.health_monitor.stop()


class TestStreamingMetaApiConnection:

    @pytest.mark.asyncio
    async def test_remove_application(self):
        """Should remove application."""
        await api.connect()
        client.remove_application = AsyncMock()
        api.history_storage.clear = AsyncMock()
        await api.remove_application()
        api.history_storage.clear.assert_called()
        client.remove_application.assert_called_with('accountId')

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
                                                      'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None,
                                        'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'comment': 'comment', 'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None,
                                        'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                                      'stopLoss': 2.0, 'takeProfit': 0.9}, None, 'regular')

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
                                                      'volume': 0.9}, None, 'regular')

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
                                        None, 'regular')

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
                                                      'clientId': 'TE_GBPUSD_7hyINWqAlE'}, None, 'regular')

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
                                        None, 'regular')

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
                                                      'openPrice': 1.0, 'stopLoss': 2.0, 'takeProfit': 0.9}, None,
                                        'regular')

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
        client.trade.assert_called_with('accountId', {'actionType': 'ORDER_CANCEL', 'orderId': '46870472'}, None,
                                        'regular')

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
        client.calculate_margin.assert_called_with('accountId', None, 'regular', order)

    @pytest.mark.asyncio
    async def test_subscribe_to_terminal(self):
        """Should subscribe to terminal."""
        await api.connect()
        client.ensure_subscribe = AsyncMock()
        await api.subscribe()
        client.ensure_subscribe.assert_any_call('accountId', 0)
        client.ensure_subscribe.assert_any_call('accountId', 1)

    @pytest.mark.asyncio
    async def test_not_subscribe_if_not_open(self):
        """Should not subscribe if connection is not open."""
        client.ensure_subscribe = AsyncMock()
        try:
            await api.subscribe()
            pytest.fail()
        except Exception as err:
            assert err.args[0] == 'This connection has not been initialized yet, please invoke await ' + \
                'connection.connect()'
        client.ensure_subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_subscribe_if_closed(self):
        """Should not subscribe if connection is closed."""
        await api.connect()
        client.ensure_subscribe = AsyncMock()
        client.unsubscribe = AsyncMock()
        await api.close()
        try:
            await api.subscribe()
            pytest.fail()
        except Exception as err:
            assert err.args[0] == 'This connection has been closed, please create a new connection'
        client.ensure_subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_synchronize_state_with_terminal(self):
        """Should synchronize state with terminal."""
        client.synchronize = AsyncMock()
        with patch('lib.metaApi.streamingMetaApiConnection.random_id', return_value='synchronizationId'):
            api = StreamingMetaApiConnection(client, client_api_client, account, None, MagicMock())
            await api.connect()
            await api.history_storage.on_history_order_added('1:ps-mpa-1',
                                                             {'id': '1', 'type': 'ORDER_TYPE_SELL',
                                                              'state': 'ORDER_STATE_FILLED',
                                                              'doneTime': date('2020-01-01T00:00:00.000Z')})
            await api.history_storage.on_deal_added('1:ps-mpa-1', {'id': '1', 'type': 'DEAL_TYPE_SELL',
                                                                   'entryType': 'DEAL_ENTRY_IN',
                                                                   'time': date('2020-01-02T00:00:00.000Z')})
            await api.synchronize('1:ps-mpa-1')
            client.synchronize.assert_called_with('accountId', 1, 'ps-mpa-1', 'synchronizationId',
                                                  date('2020-01-01T00:00:00.000Z'), date('2020-01-02T00:00:00.000Z'),
                                                  ANY)

    @pytest.mark.asyncio
    async def test_synchronize_state_with_terminal_from_time(self):
        """Should synchronize state with terminal from specified time."""
        client.synchronize = AsyncMock()
        with patch('lib.metaApi.streamingMetaApiConnection.random_id', return_value='synchronizationId'):
            api = StreamingMetaApiConnection(client, client_api_client, account, None, MagicMock(),
                                             date('2020-10-07T00:00:00.000Z'))
            await api.connect()
            await api.history_storage.on_history_order_added('1:ps-mpa-1',
                                                             {'id': '1', 'type': 'ORDER_TYPE_SELL',
                                                              'state': 'ORDER_STATE_FILLED',
                                                              'doneTime': date('2020-01-01T00:00:00.000Z')})
            await api.history_storage.on_deal_added('1:ps-mpa-1', {'id': '1', 'type': 'DEAL_TYPE_SELL',
                                                                   'entryType': 'DEAL_ENTRY_IN',
                                                                   'time': date('2020-01-02T00:00:00.000Z')})
            await api.synchronize('1:ps-mpa-1')
            client.synchronize.assert_called_with('accountId', 1, 'ps-mpa-1', 'synchronizationId',
                                                  date('2020-10-07T00:00:00.000Z'), date('2020-10-07T00:00:00.000Z'),
                                                  ANY)

    @pytest.mark.asyncio
    async def test_subscribe_to_market_data(self):
        """Should subscribe to market data."""
        await api.connect()
        client.subscribe_to_market_data = AsyncMock()
        promise = asyncio.create_task(api.subscribe_to_market_data('EURUSD', None))
        api.terminal_state.wait_for_price = AsyncMock(return_value={'time': datetime.fromtimestamp(1000000),
                                                                    'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1})
        await promise
        assert 'EURUSD' in api.subscribed_symbols
        client.subscribe_to_market_data.assert_called_with('accountId', 'EURUSD', [{'type': 'quotes'}], 'regular')
        assert api.subscriptions('EURUSD') == [{'type': 'quotes'}]
        await api.subscribe_to_market_data('EURUSD', [{'type': 'books'}, {'type': 'candles', 'timeframe': '1m'}])
        assert api.subscriptions('EURUSD') == [{'type': 'quotes'}, {'type': 'books'},
                                               {'type': 'candles', 'timeframe': '1m'}]
        await api.subscribe_to_market_data('EURUSD', [{'type': 'quotes'}, {'type': 'candles', 'timeframe': '5m'}])
        assert api.subscriptions('EURUSD') == [{'type': 'quotes'}, {'type': 'books'},
                                               {'type': 'candles', 'timeframe': '1m'},
                                               {'type': 'candles', 'timeframe': '5m'}]

    @pytest.mark.asyncio
    async def test_not_subscribe_if_no_specification(self):
        """Should not subscribe to symbol that has no specification"""
        await api.connect()
        client.subscribe_to_market_data = AsyncMock()
        api.terminal_state.wait_for_price = AsyncMock(return_value={'time': datetime.fromtimestamp(1000000),
                                                                    'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1})
        await api.subscribe_to_market_data('EURUSD', None, 1)
        client.subscribe_to_market_data.assert_called_with('accountId', 'EURUSD', [{'type': 'quotes'}], 'regular')
        api.terminal_state.specification = MagicMock(return_value=None)
        try:
            await api.subscribe_to_market_data('AAAAA', None, 1)
            raise Exception('ValidationException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @pytest.mark.asyncio
    async def test_unsubscribe_from_market_data(self):
        """Should unsubscribe from market data."""
        await api.connect()
        client.subscribe_to_market_data = AsyncMock()
        client.unsubscribe_from_market_data = AsyncMock()
        api.terminal_state.wait_for_price = AsyncMock(return_value={'time': datetime.fromtimestamp(1000000),
                                                                    'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1})
        await api.subscribe_to_market_data('EURUSD', [{'type': 'quotes'}])
        assert 'EURUSD' in api.subscribed_symbols
        await api.unsubscribe_from_market_data('EURUSD', [{'type': 'quotes'}])
        assert 'EURUSD' not in api.subscribed_symbols
        client.unsubscribe_from_market_data.assert_called_with('accountId', 'EURUSD', [{'type': 'quotes'}], 'regular')
        await api.subscribe_to_market_data('EURUSD', [{'type': 'quotes'}, {'type': 'books'},
                                                      {'type': 'candles', 'timeframe': '1m'},
                                                      {'type': 'candles', 'timeframe': '5m'}], 1)
        assert api.subscriptions('EURUSD') == [{'type': 'quotes'}, {'type': 'books'},
                                               {'type': 'candles', 'timeframe': '1m'},
                                               {'type': 'candles', 'timeframe': '5m'}]
        await api.unsubscribe_from_market_data('EURUSD', [{'type': 'quotes'},
                                                          {'type': 'candles', 'timeframe': '5m'}])
        assert api.subscriptions('EURUSD') == [{'type': 'books'}, {'type': 'candles', 'timeframe': '1m'}]

    @pytest.mark.asyncio
    async def test_unsubscribe_during_subscription_downgrade(self):
        """Should unsubscribe during market data subscription downgrade."""
        await api.connect()
        api.subscribe_to_market_data = AsyncMock()
        api.unsubscribe_from_market_data = AsyncMock()
        await api.on_subscription_downgraded('1:ps-mpa-1', 'EURUSD', None, [{'type': 'ticks'}, {'type': 'books'}])
        api.unsubscribe_from_market_data.assert_called_with('EURUSD', [{'type': 'ticks'}, {'type': 'books'}])
        api.subscribe_to_market_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_market_data_subscription_on_downgrade(self):
        """Should update market data subscription on downgrade."""
        await api.connect()
        api.subscribe_to_market_data = AsyncMock()
        api.unsubscribe_from_market_data = AsyncMock()
        await api.on_subscription_downgraded('1:ps-mpa-1', 'EURUSD',
                                             [{'type': 'quotes', 'intervalInMilliseconds': 30000}])
        api.subscribe_to_market_data.assert_called_with('EURUSD', [{'type': 'quotes', 'intervalInMilliseconds': 30000}])
        api.unsubscribe_from_market_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_uptime_stats(self):
        """Should save uptime stats to the server."""
        await api.connect()
        client.save_uptime = AsyncMock()
        await api.save_uptime({'1h': 100})
        client.save_uptime.assert_called_with('accountId', {'1h': 100})

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Should initialize listeners, terminal state and history storage for accounts with user sync mode."""
        client.add_synchronization_listener = MagicMock()
        api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
        await api.connect()
        assert api.terminal_state
        assert api.history_storage
        client.add_synchronization_listener.assert_any_call('accountId', api)
        client.add_synchronization_listener.assert_any_call('accountId', api.terminal_state)
        client.add_synchronization_listener.assert_any_call('accountId', api.history_storage)

    @pytest.mark.asyncio
    async def test_add_sync_listeners(self):
        """Should add synchronization listeners for account with user synchronization mode."""
        client.add_synchronization_listener = MagicMock()
        api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
        await api.connect()
        listener = {}
        api.add_synchronization_listener(listener)
        client.add_synchronization_listener.assert_called_with('accountId', listener)

    @pytest.mark.asyncio
    async def test_remove_sync_listeners(self):
        """Should remove synchronization listeners."""
        client.remove_synchronization_listener = MagicMock()
        api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
        await api.connect()
        listener = {}
        api.remove_synchronization_listener(listener)
        client.remove_synchronization_listener.assert_called_with('accountId', listener)

    @pytest.mark.asyncio
    async def test_sync_on_connection(self):
        """Should synchronize on connection."""
        with patch('lib.metaApi.streamingMetaApiConnection.random_id', return_value='synchronizationId'):
            client.synchronize = AsyncMock()
            api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
            storage.last_history_order_time = AsyncMock(return_value=date('2020-01-01T00:00:00.000Z'))
            storage.last_deal_time = AsyncMock(return_value=date('2020-01-02T00:00:00.000Z'))
            await api.connect()
            await api.on_connected('1:ps-mpa-1', 1)
            await asyncio.sleep(0.05)
            client.synchronize.assert_called_with('accountId', 1, 'ps-mpa-1', 'synchronizationId',
                                                  date('2020-01-01T00:00:00.000Z'), date('2020-01-02T00:00:00.000Z'),
                                                  ANY)

    @pytest.mark.asyncio
    async def test_maintain_sync(self):
        """Should maintain synchronization if connection has failed."""
        with patch('lib.metaApi.streamingMetaApiConnection.random_id', return_value='synchronizationId'):
            client.synchronize = AsyncMock(side_effect=[Exception('test error'), None])
            api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
            await api.connect()
            storage.last_history_order_time = AsyncMock(return_value=date('2020-01-01T00:00:00.000Z'))
            storage.last_deal_time = AsyncMock(return_value=date('2020-01-02T00:00:00.000Z'))
            await api.on_connected('1:ps-mpa-1', 1)
            await asyncio.sleep(0.05)
            client.synchronize.assert_called_with('accountId', 1,  'ps-mpa-1', 'synchronizationId',
                                                  date('2020-01-01T00:00:00.000Z'), date('2020-01-02T00:00:00.000Z'),
                                                  ANY)

    @pytest.mark.asyncio
    async def test_not_sync_if_connection_closed(self):
        """Should not synchronize if connection is closed."""
        with patch('lib.metaApi.streamingMetaApiConnection.random_id', return_value='synchronizationId'):
            client.synchronize = AsyncMock()
            client.unsubscribe = AsyncMock()
            api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
            await api.connect()
            await api.history_storage.on_history_order_added('1:ps-mpa-1',
                                                             {'doneTime': date('2020-01-01T00:00:00.000Z')})
            await api.history_storage.on_deal_added('1:ps-mpa-1', {'time': date('2020-01-02T00:00:00.000Z')})
            await api.close()
            await api.on_connected('1:ps-mpa-1', 1)
            client.synchronize.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_from_events_on_close(self):
        """Should unsubscribe from events on close."""
        client.add_synchronization_listener = MagicMock()
        client.remove_synchronization_listener = MagicMock()
        client.unsubscribe = AsyncMock()
        api = StreamingMetaApiConnection(client, client_api_client, account, storage, MagicMock())
        await api.connect()
        await api.close()
        client.unsubscribe.assert_any_call('accountId')
        client.remove_synchronization_listener.assert_any_call('accountId', api)
        client.remove_synchronization_listener.assert_any_call('accountId', api.terminal_state)
        client.remove_synchronization_listener.assert_any_call('accountId', api.history_storage)

    @pytest.mark.timeout(60)
    @pytest.mark.asyncio
    async def test_wait_sync_complete_user_mode(self):
        """Should wait until synchronization complete."""
        await api.connect()
        assert not (await api.is_synchronized('1:ps-mpa-1'))
        api._historyStorage.update_disk_storage = AsyncMock()
        try:
            await api.wait_synchronized({'applicationPattern': 'app.*', 'synchronizationId': 'synchronizationId',
                                         'timeoutInSeconds': 1, 'intervalInMilliseconds': 10})
            raise Exception('TimeoutError is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
        await api.on_history_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        await api.on_deals_synchronized('1:ps-mpa-1', 'synchronizationId')
        promise = api.wait_synchronized({'applicationPattern': 'app.*', 'synchronizationId': 'synchronizationId',
                                         'timeoutInSeconds': 1, 'intervalInMilliseconds': 10})
        start_time = datetime.now()
        await promise
        assert pytest.approx(10, 10) == (datetime.now() - start_time).seconds * 1000
        assert (await api.is_synchronized('1:ps-mpa-1', 'synchronizationId'))

    @pytest.mark.asyncio
    async def test_time_out_waiting_for_sync(self):
        """Should time out waiting for synchronization complete."""
        await api.connect()
        try:
            await api.wait_synchronized({'applicationPattern': 'app.*', 'synchronizationId': 'synchronizationId',
                                         'timeoutInSeconds': 1, 'intervalInMilliseconds': 10})
            raise Exception('TimeoutError is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
        assert not (await api.is_synchronized('1:ps-mpa-1', 'synchronizationId'))

    @pytest.mark.asyncio
    async def test_load_history_storage_from_disk(self):
        """Should load data to history storage from disk."""
        await api.connect()
        api._historyStorage.initialize = AsyncMock()
        await api.initialize()
        api._historyStorage.initialize.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Should set synchronized false on disconnect."""
        await api.connect()
        client.synchronize = AsyncMock()
        await api.on_connected('1:ps-mpa-1', 2)
        await asyncio.sleep(0.05)
        assert api.synchronized
        client.subscribe = AsyncMock()
        account.reload = AsyncMock()
        await api.on_disconnected('1:ps-mpa-1')
        assert not api.synchronized

    @pytest.mark.asyncio
    async def test_on_stream_closed(self):
        """Should delete state if stream closed."""
        await api.connect()
        client.synchronize = AsyncMock()
        await api.on_connected('1:ps-mpa-1', 2)
        await asyncio.sleep(0.05)
        assert api.synchronized
        await api.on_stream_closed('1:ps-mpa-1')
        assert not api.synchronized

    @pytest.mark.asyncio
    async def test_create_refresh_market_data_subscriptions_job(self):
        """Should create refresh subscriptions job."""
        with patch('lib.metaApi.streamingMetaApiConnection.asyncio.sleep', new=lambda x: sleep(x / 10)):
            with patch('lib.metaApi.streamingMetaApiConnection.uniform', new=MagicMock(return_value=1)):
                await api.connect()
                client.refresh_market_data_subscriptions = AsyncMock()
                client.subscribe_to_market_data = AsyncMock()
                client.add_synchronization_listener = MagicMock()
                client.remove_synchronization_listener = MagicMock()
                client.unsubscribe = AsyncMock()
                api.terminal_state.wait_for_price = AsyncMock()
                await api.on_synchronization_started('1:ps-mpa-1')
                await sleep(0.05)
                client.refresh_market_data_subscriptions.assert_called_with('accountId', 1, [])
                await api.subscribe_to_market_data('EURUSD', [{'type': 'quotes'}], 1)
                await sleep(0.11)
                client.refresh_market_data_subscriptions.assert_called_with(
                    'accountId', 1, [{'symbol': 'EURUSD', 'subscriptions': [{'type': 'quotes'}]}])
                assert client.refresh_market_data_subscriptions.call_count == 2
                await api.on_synchronization_started('1:ps-mpa-1')
                await sleep(0.05)
                assert client.refresh_market_data_subscriptions.call_count == 3
                await api.close()
                await sleep(0.11)
                assert client.refresh_market_data_subscriptions.call_count == 3

    @pytest.mark.asyncio
    async def test_queue_events(self):
        """Should queue events."""
        client.queue_event = MagicMock()

        def event_callable():
            pass

        api.queue_event('test', event_callable)
        client.queue_event.assert_called_with('accountId', 'test', event_callable)
