from .terminalState import TerminalState
import pytest
import asyncio
from datetime import datetime
from ..metaApi.models import date
from hashlib import md5
from mock import MagicMock, AsyncMock
state = TerminalState('accountId', MagicMock())


@pytest.fixture(autouse=True)
def run_around_tests():
    client_api_client = MagicMock()
    client_api_client.get_hashing_ignored_field_lists = AsyncMock(return_value={
        'g1': {
            'specification': [
                'description',
                'expirationTime',
                'expirationBrokerTime',
                'startTime',
                'startBrokerTime',
                'pipSize'
            ],
            'position': [
                'time',
                'updateTime',
                'comment',
                'brokerComment',
                'originalComment',
                'clientId',
                'profit',
                'realizedProfit',
                'unrealizedProfit',
                'currentPrice',
                'currentTickValue',
                'accountCurrencyExchangeRate',
                'updateSequenceNumber'
            ],
            'order': [
                'time',
                'expirationTime',
                'comment',
                'brokerComment',
                'originalComment',
                'clientId',
                'currentPrice',
                'accountCurrencyExchangeRate',
                'updateSequenceNumber'
            ]
        },
        'g2': {
            'specification': [
                'pipSize'
            ],
            'position': [
                'comment',
                'brokerComment',
                'originalComment',
                'clientId',
                'profit',
                'realizedProfit',
                'unrealizedProfit',
                'currentPrice',
                'currentTickValue',
                'accountCurrencyExchangeRate',
                'updateSequenceNumber'
            ],
            'order': [
                'comment',
                'brokerComment',
                'originalComment',
                'clientId',
                'currentPrice',
                'accountCurrencyExchangeRate',
                'updateSequenceNumber'
            ]
        }
    })
    global state
    state = TerminalState('accountId', client_api_client)
    yield


class TestTerminalState:

    @pytest.mark.asyncio
    async def test_return_connection_state(self):
        """Should return connection state."""
        assert not state.connected
        await state.on_connected('1:ps-mpa-1', 1)
        assert state.connected
        await state.on_disconnected('1:ps-mpa-1')
        assert not state.connected

    @pytest.mark.asyncio
    async def test_return_broker_connection_state(self):
        """Should return broker connection state."""
        assert not state.connected_to_broker
        await state.on_broker_connection_status_changed('1:ps-mpa-1', True)
        assert state.connected_to_broker
        await state.on_broker_connection_status_changed('1:ps-mpa-1', False)
        assert not state.connected_to_broker
        await state.on_broker_connection_status_changed('1:ps-mpa-1', True)
        await state.on_disconnected('1:ps-mpa-1')
        assert not state.connected_to_broker

    @pytest.mark.asyncio
    async def test_return_account_information(self):
        """Should return account information."""
        assert not state.account_information
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        assert state.account_information == {'balance': 1000}

    @pytest.mark.asyncio
    async def test_return_positions(self):
        """Should return positions."""
        assert len(state.positions) == 0
        await state.on_position_updated('1:ps-mpa-1', {'id': '1', 'profit': 10})
        await state.on_position_updated('1:ps-mpa-1', {'id': '2'})
        await state.on_position_updated('1:ps-mpa-1', {'id': '1', 'profit': 11})
        assert len(state.positions) == 2
        await state.on_position_removed('1:ps-mpa-1', '2')
        await state.on_position_removed('1:ps-mpa-1', '3')
        await state.on_position_removed('1:ps-mpa-1', '3')
        assert len(state.positions) == 1
        assert state.positions == [{'id': '1', 'profit': 11}]

    @pytest.mark.asyncio
    async def test_return_orders(self):
        """Should return orders."""
        assert len(state.orders) == 0
        await state.on_pending_order_updated('1:ps-mpa-1', {'id': '1', 'openPrice': 10})
        await state.on_pending_order_updated('1:ps-mpa-1', {'id': '2'})
        await state.on_pending_order_updated('1:ps-mpa-1', {'id': '1', 'openPrice': 11})
        assert len(state.orders) == 2
        await state.on_pending_order_completed('1:ps-mpa-1', '2')
        assert len(state.orders) == 1
        assert state.orders == [{'id': '1', 'openPrice': 11}]

    @pytest.mark.asyncio
    async def test_return_specifications(self):
        """Should return specifications."""
        assert len(state.specifications) == 0
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [{'symbol': 'EURUSD', 'tickSize': 0.00001},
                                                                    {'symbol': 'GBPUSD'}], [])
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [
            {'symbol': 'AUDNZD'}, {'symbol': 'EURUSD', 'tickSize': 0.0001}], ['AUDNZD'])
        assert len(state.specifications) == 2
        assert state.specifications == [{'symbol': 'EURUSD', 'tickSize': 0.0001}, {'symbol': 'GBPUSD'}]
        assert state.specification('EURUSD') == {'symbol': 'EURUSD', 'tickSize': 0.0001}

    @pytest.mark.asyncio
    async def test_return_price(self):
        """Should return price."""
        assert not state.price('EURUSD')
        await state.on_symbol_prices_updated('1:ps-mpa-1', [{
            'time': date('2022-01-01T00:00:00.000Z'), 'brokerTime': '2022-01-01 02:00:00.000',
            'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1}])
        await state.on_symbol_prices_updated('1:ps-mpa-1', [{
            'time': date('2022-01-01T00:00:01.000Z'), 'brokerTime': '2022-01-01 02:00:01.000', 'symbol': 'GBPUSD'}])
        await state.on_symbol_prices_updated('1:ps-mpa-1', [{
            'time': date('2022-01-01T00:00:02.000Z'), 'brokerTime': '2022-01-01 02:00:02.000',
            'symbol': 'EURUSD', 'bid': 1, 'ask': 1.2}])
        assert state.price('EURUSD') == {'time': date('2022-01-01T00:00:02.000Z'), 'symbol': 'EURUSD',
                                         'brokerTime': '2022-01-01 02:00:02.000', 'bid': 1, 'ask': 1.2}
        assert state.last_quote_time == {'time': date('2022-01-01T00:00:02.000Z'),
                                         'brokerTime': '2022-01-01 02:00:02.000'}

    @pytest.mark.asyncio
    async def test_wait_for_price(self):
        """Should wait for price."""
        assert state.price('EURUSD') is None
        promise = asyncio.create_task(state.wait_for_price('EURUSD'))
        await state.on_symbol_prices_updated('1:ps-mpa-1', [{'time': date('2022-01-01 02:00:00.000'),
                                                             'brokerTime': '2022-01-01 02:00:00.000',
                                             'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1}])
        assert (await promise) == {'time': date('2022-01-01 02:00:00.000'), 'brokerTime': '2022-01-01 02:00:00.000',
                                   'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1}

    @pytest.mark.asyncio
    async def test_update_account_equity_and_position(self):
        """Should update account equity and position profit on price update."""
        await state.on_account_information_updated('1:ps-mpa-1', {'equity': 1000, 'balance': 800, 'platform': 'mt4'})
        await state.on_positions_replaced('1:ps-mpa-1', [{
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'currentPrice': 9,
            'currentTickValue': 0.5,
            'openPrice': 8,
            'profit': 100,
            'volume': 2
        }])
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        await state.on_position_updated('1:ps-mpa-1', {
            'id': '2',
            'symbol': 'AUDUSD',
            'type': 'POSITION_TYPE_BUY',
            'currentPrice': 9,
            'currentTickValue': 0.5,
            'openPrice': 8,
            'profit': 100,
            'volume': 2
        })
        await state.on_positions_synchronized('1:ps-mpa-1', 'synchronizationId')
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [
            {'symbol': 'EURUSD', 'tickSize': 0.01, 'digits': 5}, {'symbol': 'AUDUSD', 'tickSize': 0.01, 'digits': 5}],
                                                     [])
        await state.on_symbol_prices_updated('1:ps-mpa-1', [
          {
            'time': datetime.now(),
            'brokerTime': '2022-01-01 02:00:00.000',
            'symbol': 'EURUSD',
            'profitTickValue': 0.5,
            'lossTickValue': 0.5,
            'bid': 10,
            'ask': 11
          },
          {
            'time': datetime.now(),
            'brokerTime': '2022-01-01 02:00:00.000',
            'symbol': 'AUDUSD',
            'profitTickValue': 0.5,
            'lossTickValue': 0.5,
            'bid': 10,
            'ask': 11
          }
        ])
        assert list(map(lambda p: p['profit'], state.positions)) == [200, 200]
        assert list(map(lambda p: p['unrealizedProfit'], state.positions)) == [200, 200]
        assert list(map(lambda p: p['currentPrice'], state.positions)) == [10, 10]
        assert state.account_information['equity'] == 1200

    @pytest.mark.asyncio
    async def test_update_margin_fields(self):
        """Should update margin fields on price update."""
        await state.on_account_information_updated('1:ps-mpa-1', {'equity': 1000, 'balance': 800})
        await state.on_symbol_prices_updated(
            '1:ps-mpa-1', [{'time': datetime.now(), 'brokerTime': '2022-01-01 02:00:00.000',
                            'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1}], 100, 200, 400, 40000)
        assert state.account_information['equity'] == 100
        assert state.account_information['margin'] == 200
        assert state.account_information['freeMargin'] == 400
        assert state.account_information['marginLevel'] == 40000

    @pytest.mark.asyncio
    async def test_update_order_current_price_on_price_update(self):
        """Should update order currentPrice on price update."""

        await state.on_pending_order_updated('1:ps-mpa-1', {
          'id': '1',
          'symbol': 'EURUSD',
          'type': 'ORDER_TYPE_BUY_LIMIT',
          'currentPrice': 9
        })
        await state.on_pending_order_updated('1:ps-mpa-1', {
            'id': '2',
            'symbol': 'AUDUSD',
            'type': 'ORDER_TYPE_SELL_LIMIT',
            'currentPrice': 9
        })
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [{'symbol': 'EURUSD', 'tickSize': 0.01}], [])
        await state.on_symbol_prices_updated('1:ps-mpa-1', [{
          'time': datetime.now(),
          'brokerTime': '2022-01-01 02:00:00.000',
          'symbol': 'EURUSD',
          'profitTickValue': 0.5,
          'lossTickValue': 0.5,
          'bid': 10,
          'ask': 11
        }])
        assert list(map(lambda o: o['currentPrice'], state.orders)) == [11, 9]

    @pytest.mark.asyncio
    async def test_close_stream(self):
        """Should remove state on closed stream."""
        assert not state.price('EURUSD')
        await state.on_symbol_prices_updated('1:ps-mpa-1', [{'time': datetime.fromtimestamp(1000000),
                                                             'brokerTime': '2022-01-01 02:00:00.000',
                                                             'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1}])
        assert state.price('EURUSD') == {'time': datetime.fromtimestamp(1000000),
                                         'brokerTime': '2022-01-01 02:00:00.000',
                                         'symbol': 'EURUSD', 'bid': 1, 'ask': 1.1}
        await state.on_disconnected('1:ps-mpa-1')

    @pytest.mark.asyncio
    async def test_on_synchronization_started(self):
        """Should reset state on synchronization started event."""
        specification = {'symbol': 'EURUSD', 'tickSize': 0.01}
        positions = [{
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'currentPrice': 9,
            'currentTickValue': 0.5,
            'openPrice': 8,
            'profit': 100,
            'volume': 2
        }]
        orders = [{
          'id': '1',
          'symbol': 'EURUSD',
          'type': 'ORDER_TYPE_BUY_LIMIT',
          'currentPrice': 9
        }]
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [specification], [])
        await state.on_positions_replaced('1:ps-mpa-1', positions)
        await state.on_pending_orders_replaced('1:ps-mpa-1', orders)
        assert state.account_information == {'balance': 1000}
        assert state.specification('EURUSD') == specification
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        await state.on_synchronization_started('1:ps-mpa-1', specifications_updated=False, positions_updated=False,
                                               orders_updated=False)
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        assert not state.account_information
        assert state.specification('EURUSD') == specification
        assert state.orders == orders
        assert state.positions == positions
        await state.on_synchronization_started('1:ps-mpa-1', specifications_updated=True, positions_updated=False,
                                               orders_updated=False)
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        assert not state.specification('EURUSD')
        assert state.orders == orders
        assert state.positions == positions
        await state.on_synchronization_started('1:ps-mpa-1', specifications_updated=True, positions_updated=False,
                                               orders_updated=True)
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        assert state.orders == []
        assert state.positions == positions
        await state.on_synchronization_started('1:ps-mpa-1', specifications_updated=True, positions_updated=True,
                                               orders_updated=True)
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        assert state.positions == []

    @pytest.mark.asyncio
    async def test_return_hashes_g1(self):
        """Should return hashes for terminal state data for cloud-g1 accounts."""
        specifications_hash = md5(
            ('[{"symbol":"AUDNZD","tickSize":0.01000000},{"symbol":"EURUSD",'
             '"tickSize":0.00000100,"contractSize":1.00000000,"maxVolume":30000.00000000,'
             '"hedgedMarginUsesLargerLeg":false,"digits":3}]').encode()).hexdigest()
        positions_hash = md5(
            ('[{"id":"46214692","type":"POSITION_TYPE_BUY","symbol":"GBPUSD","magic":1000,'
             '"openPrice":1.26101000,"volume":0.07000000,"swap":0.00000000,"commission":-0.25000000,'
             '"stopLoss":1.17721000}]'
             ).encode()).hexdigest()
        orders_hash = md5(('[{"id":"46871284","type":"ORDER_TYPE_BUY_LIMIT","state":"ORDER_STATE_PLACED",'
                           '"symbol":"AUDNZD","magic":123456,"platform":"mt5","openPrice":1.03000000,'
                           '"volume":0.01000000,"currentVolume":0.01000000}]').encode()).hexdigest()
        hashes = await state.get_hashes('cloud-g1', '1:ps-mpa-1')
        assert hashes['specificationsMd5'] is None
        assert hashes['positionsMd5'] is None
        assert hashes['ordersMd5'] is None
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [
            {'symbol': 'AUDNZD', 'tickSize': 0.01, "description": "Test1"},
            {'symbol': 'EURUSD', 'tickSize': 0.000001, "contractSize": 1, "maxVolume": 30000,
             "hedgedMarginUsesLargerLeg": False, 'digits': 3, "description": "Test2"}], [])
        await state.on_positions_replaced('1:ps-mpa-1', [{
            'id': '46214692',
            'type': 'POSITION_TYPE_BUY',
            'symbol': 'GBPUSD',
            'magic': 1000,
            'time': date('2020-04-15T02:45:06.521Z'),
            'updateTime': date('2020-04-15T02:45:06.521Z'),
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
            'realizedProfit': -6.536993168992922e-13,
            'updateSequenceNumber': 13246,
            'accountCurrencyExchangeRate': 1,
            'comment': 'test',
            'brokerComment': 'test2',
        }])
        await state.on_pending_orders_replaced('1:ps-mpa-1', [{
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
            'comment': 'COMMENT2',
            'updateSequenceNumber': 13246,
            'accountCurrencyExchangeRate': 1,
            'brokerComment': 'test2',
            'clientId': 'TE_GBPUSD_7hyINWqAlE',
        }])
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        hashes = await state.get_hashes('cloud-g1', '1:ps-mpa-1')
        assert hashes['specificationsMd5'] == specifications_hash
        assert hashes['positionsMd5'] == positions_hash
        assert hashes['ordersMd5'] == orders_hash

    @pytest.mark.asyncio
    async def test_return_hashes_g2(self):
        """Should return hashes for terminal state data for cloud-g2 accounts."""
        specifications_hash = md5(
            ('[{"symbol":"AUDNZD","tickSize":0.01,"description":"Test1"},{"symbol":"EURUSD","tickSize":0.000001,'
             '"contractSize":1,"maxVolume":30000,"hedgedMarginUsesLargerLeg":false,"description":"Test2"}]'
             ).encode()).hexdigest()
        positions_hash = md5(
            ('[{"id":"46214692","type":"POSITION_TYPE_BUY","symbol":"GBPUSD","magic":1000,'
             '"time":"2020-04-15T02:45:06.521Z","updateTime":"2020-04-15T02:45:06.521Z","openPrice":1.26101,'
             '"volume":0.07,"swap":0,"commission":-0.25,"stopLoss":1.17721}]').encode()).hexdigest()
        orders_hash = md5(('[{"id":"46871284","type":"ORDER_TYPE_BUY_LIMIT","state":"ORDER_STATE_PLACED",'
                           '"symbol":"AUDNZD","magic":123456,"platform":"mt5","time":"2020-04-20T08:38:58.270Z",'
                           '"openPrice":1.03,"volume":0.01,"currentVolume":0.01}]').encode()).hexdigest()
        hashes = await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert hashes['specificationsMd5'] is None
        assert hashes['positionsMd5'] is None
        assert hashes['ordersMd5'] is None
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [
            {'symbol': 'AUDNZD', 'tickSize': 0.01, "description": "Test1"},
            {'symbol': 'EURUSD', 'tickSize': 0.000001, "contractSize": 1, "maxVolume": 30000,
             "hedgedMarginUsesLargerLeg": False, "description": "Test2"}], [])
        await state.on_positions_replaced('1:ps-mpa-1', [{
            'id': '46214692',
            'type': 'POSITION_TYPE_BUY',
            'symbol': 'GBPUSD',
            'magic': 1000,
            'time': date('2020-04-15T02:45:06.521Z'),
            'updateTime': date('2020-04-15T02:45:06.521Z'),
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
            'realizedProfit': -6.536993168992922e-13,
            'updateSequenceNumber': 13246,
            'accountCurrencyExchangeRate': 1,
            'comment': 'test',
            'brokerComment': 'test2',
        }])
        await state.on_pending_orders_replaced('1:ps-mpa-1', [{
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
            'comment': 'COMMENT2',
            'updateSequenceNumber': 13246,
            'accountCurrencyExchangeRate': 1,
            'brokerComment': 'test2',
            'clientId': 'TE_GBPUSD_7hyINWqAlE',
        }])
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        hashes = await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert hashes['specificationsMd5'] == specifications_hash
        assert hashes['positionsMd5'] == positions_hash
        assert hashes['ordersMd5'] == orders_hash

    @pytest.mark.asyncio
    async def test_cache_specifications_hash(self):
        """Should cache specifications hash."""
        get_hash_mock = MagicMock(return_value='hash')
        state._get_hash = get_hash_mock
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [
            {'symbol': 'AUDNZD', 'tickSize': 0.01, 'description': 'Test1'}
        ], [])
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 1
        await state.on_symbol_specifications_updated('1:ps-mpa-1', [
               {'symbol': 'AUDNZD', 'tickSize': 0.02, 'description': 'Test1'}], [])
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_positions_hash(self):
        """Should cache positions hash."""
        get_hash_mock = MagicMock(return_value='hash')
        state._get_hash = get_hash_mock
        await state.on_positions_replaced('1:ps-mpa-1', [{
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'currentPrice': 9,
            'currentTickValue': 0.5,
            'openPrice': 8,
            'profit': 100,
            'volume': 2
        }])
        await state.on_positions_synchronized('1:ps-mpa-1', 'synchronizationId')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 1
        await state.on_position_updated('1:ps-mpa-1', {
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'currentPrice': 9,
            'currentTickValue': 0.5,
            'openPrice': 8,
            'profit': 100,
            'volume': 2
        })
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 2
        await state.on_position_removed('1:ps-mpa-1', '1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 3
        await state.on_positions_replaced('1:ps-mpa-1', [{
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'currentPrice': 9,
            'currentTickValue': 0.5,
            'openPrice': 8,
            'profit': 100,
            'volume': 2
        }])
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 4

    @pytest.mark.asyncio
    async def test_cache_orders_hash(self):
        """Should cache orders hash."""
        get_hash_mock = MagicMock(return_value='hash')
        state._get_hash = get_hash_mock
        await state.on_pending_orders_replaced('1:ps-mpa-1', [{
                'id': '1',
                'symbol': 'EURUSD',
                'type': 'ORDER_TYPE_BUY_LIMIT',
                'currentPrice': 9
        }])
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 2
        await state.on_pending_order_updated('1:ps-mpa-1', {
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'ORDER_TYPE_BUY_LIMIT',
            'currentPrice': 10
        })
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 3
        await state.on_pending_order_completed('1:ps-mpa-1', '1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 4
        await state.on_pending_orders_replaced('1:ps-mpa-1', [{
            'id': '1',
            'symbol': 'EURUSD',
            'type': 'ORDER_TYPE_BUY_LIMIT',
            'currentPrice': 10
        }])
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        await state.get_hashes('cloud-g2', '1:ps-mpa-1')
        assert get_hash_mock.call_count == 5

    @pytest.mark.asyncio
    async def test_delete_unfinished_states_except_latest_on_sync_started(self):
        """Should delete all unfinished states except for the latest on sync started."""
        await state.on_account_information_updated('2:ps-mpa-3', {'balance': 1000})
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        await state.on_account_information_updated('1:ps-mpa-2', {'balance': 1000})
        await state.on_synchronization_started('1:ps-mpa-4', True, True, True)
        assert '1:ps-mpa-1' in state._stateByInstanceIndex
        assert '1:ps-mpa-2' not in state._stateByInstanceIndex
        assert '2:ps-mpa-3' in state._stateByInstanceIndex

    @pytest.mark.asyncio
    async def test_delete_disconnected_states_on_sync_finished(self):
        """Should delete all disconnected states on sync finished."""
        await state.on_account_information_updated('2:ps-mpa-3', {'balance': 1000})
        await state.on_pending_orders_synchronized('2:ps-mpa-3', 'synchronizationId')
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        await state.on_connected('1:ps-mpa-1', 1)
        await state.on_account_information_updated('1:ps-mpa-2', {'balance': 1000})
        await state.on_pending_orders_synchronized('1:ps-mpa-2', 'synchronizationId2')
        await state.on_account_information_updated('1:ps-mpa-4', {'balance': 1000})
        await state.on_pending_orders_synchronized('1:ps-mpa-4', 'synchronizationId2')
        assert '1:ps-mpa-1' in state._stateByInstanceIndex
        assert '1:ps-mpa-2' not in state._stateByInstanceIndex
        assert '2:ps-mpa-3' in state._stateByInstanceIndex

    @pytest.mark.asyncio
    async def test_delete_state_on_disconnected_if_there_is_another_synced_state(self):
        """Should delete state on disconnected if there is another synced state."""
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        await state.on_connected('1:ps-mpa-1', 1)
        await state.on_pending_orders_synchronized('1:ps-mpa-1', 'synchronizationId2')
        await state.on_account_information_updated('1:ps-mpa-2', {'balance': 1000})
        await state.on_connected('1:ps-mpa-2', 1)
        await state.on_pending_orders_synchronized('1:ps-mpa-2', 'synchronizationId2')
        await state.on_stream_closed('1:ps-mpa-2')
        assert '1:ps-mpa-1' in state._stateByInstanceIndex
        assert '1:ps-mpa-2' not in state._stateByInstanceIndex

    @pytest.mark.asyncio
    async def test_delete_partially_synced_state_on_disconnected_if_there_is_fresher_state(self):
        """Should delete partially synced state on disconnected if there is another fresher state."""
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        await state.on_connected('1:ps-mpa-1', 1)
        await state.on_account_information_updated('1:ps-mpa-2', {'balance': 1000})
        await state.on_connected('1:ps-mpa-2', 1)
        await state.on_stream_closed('1:ps-mpa-1')
        assert '1:ps-mpa-1' not in state._stateByInstanceIndex
        assert '1:ps-mpa-2' in state._stateByInstanceIndex

    @pytest.mark.asyncio
    async def test_not_delete_partially_synced_state_on_disconnected_if_there_is_no_fresher_state(self):
        """Should not delete partially synced state on disconnected if there is no fresher state."""
        await state.on_synchronization_started('1:ps-mpa-1', False, False, False)
        await state.on_account_information_updated('1:ps-mpa-1', {'balance': 1000})
        await state.on_connected('1:ps-mpa-1', 1)
        await asyncio.sleep(0.1)
        await state.on_synchronization_started('1:ps-mpa-2', False, False, False)
        await state.on_account_information_updated('1:ps-mpa-2', {'balance': 1000})
        await state.on_connected('1:ps-mpa-2', 1)
        await state.on_disconnected('1:ps-mpa-2')
        assert '1:ps-mpa-1' in state._stateByInstanceIndex
        assert '1:ps-mpa-2' in state._stateByInstanceIndex
