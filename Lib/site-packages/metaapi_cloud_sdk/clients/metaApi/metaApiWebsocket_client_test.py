from .metaApiWebsocket_client import MetaApiWebsocketClient
from socketio import AsyncServer
from aiohttp import web
from ...metaApi.models import date, format_date
from ..httpClient import HttpClient
import pytest
import asyncio
import copy
from mock import patch
from urllib.parse import parse_qs
from mock import MagicMock, AsyncMock
from copy import deepcopy
from datetime import datetime, timedelta
from freezegun import freeze_time
from ..timeoutException import TimeoutException
from asyncio import sleep
import json
sio = None
http_client = HttpClient()
client: MetaApiWebsocketClient = None
future_close = asyncio.Future()
fake_server = None
empty_hash = 'd41d8cd98f00b204e9800998ecf8427e'
connections = []
session_id = ''
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


async def close_client():
    future_close.set_result(None)


class FakeServer:

    def __init__(self):
        self.app = web.Application()
        self.runner = None

    async def start(self, port=8080):
        global sio
        sio = AsyncServer(async_mode='aiohttp')

        @sio.event
        async def connect(sid, environ):
            connections.append(sid)
            qs = parse_qs(environ['QUERY_STRING'])
            if ('auth-token' not in qs) or (qs['auth-token'] != ['token']):
                environ.emit({'error': 'UnauthorizedError', 'message': 'Authorization token invalid'})
                environ.close()

        sio.attach(self.app, socketio_path='ws')
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, 'localhost', port)
        await site.start()

    async def stop(self):
        await self.runner.cleanup()


@pytest.fixture(autouse=True)
async def run_around_tests():
    global connections
    connections = []
    global http_client
    http_client = HttpClient()
    global fake_server
    fake_server = FakeServer()
    await fake_server.start()
    global client
    client = MetaApiWebsocketClient(http_client, 'token', {'application': 'application',
                                                           'domain': 'project-stock.agiliumlabs.cloud',
                                                           'requestTimeout': 3, 'useSharedClientApi': True,
                                                           'retryOpts': {'retries': 3, 'minDelayInSeconds': 0.1,
                                                                         'maxDelayInSeconds': 0.5}})
    client.set_url('http://localhost:8080')
    client._socketInstances = {'vint-hill': {0: [], 1: []}, 'new-york': {0: []}}
    client._regionsByAccounts['accountId'] = {'region': 'vint-hill', 'connections': 1}
    client._socketInstancesByAccounts = {0: {'accountId': 0}, 1: {'accountId': 0}}
    client._connectedHosts = {'accountId:0:ps-mpa-1': 'ps-mpa-1'}
    await client.connect(0, 'new-york')
    await client.connect(1, 'vint-hill')
    await client.connect(0, 'vint-hill')
    client._socketInstances['vint-hill'][0][0]['synchronizationThrottler']._accountsBySynchronizationIds = {}
    client._socketInstances['vint-hill'][1][0]['synchronizationThrottler']._accountsBySynchronizationIds = {}
    global session_id
    session_id = client.socket_instances['vint-hill'][0][0]['sessionId']
    client._resolved = True
    global future_close
    future_close = asyncio.Future()

    def return_packet(packet):
        return [packet]

    client._packetOrderer.restore_order = MagicMock(side_effect=return_packet)
    yield
    await client.close()
    await fake_server.stop()
    tasks = [task for task in asyncio.all_tasks() if task is not
             asyncio.tasks.current_task()]
    list(map(lambda task: task.cancel(), tasks))


def FinalMock():
    # This method closes the client once the required socket event has been called
    async def async_magic_close(*args):
        await close_client()

    return AsyncMock(side_effect=async_magic_close)


@pytest.mark.asyncio
async def test_change_client_id_on_reconnect():
    """Should change client id on reconnect."""
    with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 30)):
        with freeze_time() as frozen_datetime:
            frozen_datetime.move_to('2020-10-10 01:00:01.000')
            connect_amount = 0
            client_id = None
            await client.close()

            @sio.event
            async def connect(sid, environ):
                async def disconnect():
                    await sleep(0.02)
                    await sio.disconnect(sid)

                await sio.emit('response', {'type': 'response'})
                nonlocal connect_amount
                nonlocal client_id
                connect_amount += 1
                qs = parse_qs(environ['QUERY_STRING'])
                if environ['aiohttp.request'].headers['Client-Id'] != qs['clientId'][0] or \
                        client_id == qs['clientId'][0]:
                    pytest.fail()
                client_id = qs['clientId'][0]
                if connect_amount < 3:
                    asyncio.create_task(disconnect())

            await client.connect(0, 'vint-hill')
            await sleep(0.05)
            frozen_datetime.tick(1.5)
            await sleep(0.05)
            frozen_datetime.tick(1.5)
            await sleep(0.05)
            assert connect_amount >= 3


@pytest.mark.asyncio
async def test_retry_connection_if_timed_out():
    """Should retry connection if first attempt timed out."""
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
    client = MetaApiWebsocketClient(http_client, 'token', {
        'application': 'application',
        'domain': 'project-stock.agiliumlabs.cloud', 'requestTimeout': 1.5, 'useSharedClientApi': False,
        'connectTimeout': 0.1,
        'retryOpts': {'retries': 3, 'minDelayInSeconds': 0.1, 'maxDelayInSeconds': 0.5}})
    client.set_url('http://localhost:6785')

    async def delayed_start():
        await asyncio.sleep(0.2)
        fake_server = FakeServer()
        await fake_server.start(6785)

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'getPositions' and data['accountId'] == 'accountId' \
                    and data['application'] == 'RPC':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'positions': positions})

    asyncio.create_task(delayed_start())
    actual = await client.get_positions('accountId')
    positions[0]['time'] = date(positions[0]['time'])
    positions[0]['updateTime'] = date(positions[0]['updateTime'])
    assert actual == positions


@pytest.mark.asyncio
async def test_connect_to_shared_server():
    """Should connect to shared server."""
    async def fake_request(arg):
        if arg['url'] == 'https://mt-provisioning-api-v1.project-stock.agiliumlabs.cloud/' + \
                'users/current/servers/mt-client-api':
            return {
                'domain': 'v3.agiliumlabs.cloud'
            }

    client = MetaApiWebsocketClient(http_client, 'token', {
        'application': 'application', 'domain': 'project-stock.agiliumlabs.cloud',
        'requestTimeout': 1.5, 'useSharedClientApi': True})
    client._httpClient.request = AsyncMock(side_effect=fake_request)
    client._socketInstances = {
        'vint-hill': {0: [{
            'connected': True,
            'requestResolves': [],
        }]}
    }
    url = await client._get_server_url(0, 0, 'vint-hill')
    assert url == 'https://mt-client-api-v1.vint-hill-a.v3.agiliumlabs.cloud'


@pytest.mark.asyncio
async def test_connect_to_dedicated_server():
    """Should connect to dedicated server."""
    async def fake_request(arg):
        if arg['url'] == 'https://mt-provisioning-api-v1.project-stock.agiliumlabs.cloud/' + \
                'users/current/servers/mt-client-api':
            return {
                'url': 'http://localhost:8081',
                'hostname': 'mt-client-api-dedicated',
                'domain': 'project-stock.agiliumlabs.cloud'
            }

    client = MetaApiWebsocketClient(http_client, 'token', {
        'application': 'application', 'domain': 'project-stock.agiliumlabs.cloud',
        'requestTimeout': 1.5, 'useSharedClientApi': False})
    client._httpClient.request = AsyncMock(side_effect=fake_request)
    client._socketInstances = {
        'vint-hill': {0: [{
            'connected': True,
            'requestResolves': [],
        }]}
    }
    url = await client._get_server_url(0, 0, 'vint-hill')
    assert url == 'https://mt-client-api-dedicated.vint-hill-a.project-stock.agiliumlabs.cloud'


@pytest.mark.asyncio
async def test_add_account_region():
    """Should add account region."""
    with freeze_time() as frozen_datetime:
        with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 7200)):
            client = MetaApiWebsocketClient(http_client, 'token', {
                'application': 'application', 'domain': 'project-stock.agiliumlabs.cloud',
                'requestTimeout': 3})
            client.add_account_region('accountId2', 'vint-hill')
            assert client.get_account_region('accountId2') == 'vint-hill'
            client.add_account_region('accountId2', 'vint-hill')
            assert client.get_account_region('accountId2') == 'vint-hill'
            client.remove_account_region('accountId2')
            assert client.get_account_region('accountId2') == 'vint-hill'
            client.remove_account_region('accountId2')
            assert client.get_account_region('accountId2') == 'vint-hill'
            frozen_datetime.tick(7201)
            await sleep(0.27)
            assert client.get_account_region('accountId2') is None


@pytest.mark.asyncio
async def test_delay_region_deletion():
    """Should delay region deletion if a request is made."""

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getAccountInformation' and data['accountId'] == 'accountId2' \
                and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'],
                                        'accountInformation': account_information}, sid)

    with freeze_time() as frozen_datetime:
        with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 7200)):
            frozen_datetime.move_to('2020-10-10 01:00:00.000')
            client = MetaApiWebsocketClient(http_client, 'token', {
                'application': 'application', 'domain': 'project-stock.agiliumlabs.cloud',
                'requestTimeout': 3})
            client.set_url('http://localhost:8080')

            client._socketInstances = {'vint-hill': {0: [], 1: []}}
            client._regionsByAccounts['accountId'] = {'region': 'vint-hill', 'connections': 1,
                                                      'lastUsed': datetime.now().timestamp()}
            client._socketInstancesByAccounts = {0: {'accountId': 0}, 1: {'accountId': 0}}
            client._connectedHosts = {'accountId:0:ps-mpa-1': 'ps-mpa-1'}
            await client.connect(1, 'vint-hill')
            await client.connect(0, 'vint-hill')
            client._socketInstances['vint-hill'][0][0]['synchronizationThrottler']._accountsBySynchronizationIds = {}
            client._socketInstances['vint-hill'][1][0]['synchronizationThrottler']._accountsBySynchronizationIds = {}

            client.add_account_region('accountId2', 'vint-hill')
            assert client.get_account_region('accountId2') == 'vint-hill'
            await client.get_account_information('accountId2')
            assert client.get_account_region('accountId2') == 'vint-hill'
            frozen_datetime.move_to('2020-10-10 03:00:05.000')
            await sleep(0.27)
            frozen_datetime.move_to('2020-10-10 01:00:00.000')
            assert client.get_account_region('accountId2') == 'vint-hill'
            await client.get_account_information('accountId2')
            client.remove_account_region('accountId2')
            frozen_datetime.move_to('2020-10-10 02:35:05.000')
            await sleep(0.27)
            frozen_datetime.move_to('2020-10-10 01:00:00.000')
            assert client.get_account_region('accountId2') == 'vint-hill'
            frozen_datetime.move_to('2020-10-10 00:30:00.000')
            await client.get_account_information('accountId2')
            frozen_datetime.move_to('2020-10-10 02:35:05.000')
            await sleep(0.27)
            frozen_datetime.move_to('2020-10-10 01:00:00.000')
            assert client.get_account_region('accountId2') is None


@pytest.mark.asyncio
async def test_retrieve_account():
    """Should retrieve MetaTrader account information from API."""

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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getAccountInformation' and data['accountId'] == 'accountId' \
                and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'accountInformation': account_information})

    actual = await client.get_account_information('accountId')
    assert actual == account_information


@pytest.mark.asyncio
async def test_retrieve_positions():
    """Should retrieve MetaTrader positions from API."""

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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getPositions' and data['accountId'] == 'accountId' \
                and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'positions': positions})
        else:
            raise Exception('Wrong request')

    actual = await client.get_positions('accountId')
    positions[0]['time'] = date(positions[0]['time'])
    positions[0]['updateTime'] = date(positions[0]['updateTime'])
    assert actual == positions


@pytest.mark.asyncio
async def test_retrieve_position():
    """Should retrieve MetaTrader position from API."""

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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getPosition' and data['accountId'] == 'accountId' and data['positionId'] == '46214692' \
                and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'position': position})

    actual = await client.get_position('accountId', '46214692')
    position['time'] = date(position['time'])
    position['updateTime'] = date(position['updateTime'])
    assert actual == position


@pytest.mark.asyncio
async def test_retrieve_orders():
    """Should retrieve MetaTrader orders from API."""

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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getOrders' and data['accountId'] == 'accountId' \
                and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'orders': orders})

    actual = await client.get_orders('accountId')
    orders[0]['time'] = date(orders[0]['time'])
    assert actual == orders


@pytest.mark.asyncio
async def test_retrieve_order():
    """Should retrieve MetaTrader order from API by id."""

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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getOrder' and data['accountId'] == 'accountId' and data['orderId'] == '46871284' \
                and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'order': order})

    actual = await client.get_order('accountId', '46871284')
    order['time'] = date(order['time'])
    assert actual == order


@pytest.mark.asyncio
async def test_retrieve_history_orders_by_ticket():
    """Should retrieve MetaTrader history orders from API by ticket."""

    history_orders = [{
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
    }]

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getHistoryOrdersByTicket' and data['accountId'] == 'accountId' and \
                data['ticket'] == '46214692' and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'historyOrders': history_orders,
                                        'synchronizing': False})

    actual = await client.get_history_orders_by_ticket('accountId', '46214692')
    history_orders[0]['time'] = date(history_orders[0]['time'])
    history_orders[0]['doneTime'] = date(history_orders[0]['doneTime'])
    assert actual == {'historyOrders': history_orders, 'synchronizing': False}


@pytest.mark.asyncio
async def test_retrieve_history_orders_by_position():
    """Should retrieve MetaTrader history orders from API by position."""

    history_orders = [{
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
    }]

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getHistoryOrdersByPosition' and data['accountId'] == 'accountId' and \
                data['positionId'] == '46214692' and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'historyOrders': history_orders,
                                        'synchronizing': False})

    actual = await client.get_history_orders_by_position('accountId', '46214692')
    history_orders[0]['time'] = date(history_orders[0]['time'])
    history_orders[0]['doneTime'] = date(history_orders[0]['doneTime'])
    assert actual == {'historyOrders': history_orders, 'synchronizing': False}


@pytest.mark.asyncio
async def test_retrieve_history_orders_by_time_range():
    """Should retrieve MetaTrader history orders from API by time range."""

    history_orders = [{
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
    }]

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getHistoryOrdersByTimeRange' and data['accountId'] == 'accountId' and \
                data['startTime'] == '2020-04-15T02:45:00.000Z' and data['application'] == 'RPC' and \
                data['endTime'] == '2020-04-15T02:46:00.000Z' and data['offset'] == 1 and data['limit'] == 100:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'historyOrders': history_orders,
                                        'synchronizing': False})

    actual = await client.get_history_orders_by_time_range('accountId', date('2020-04-15T02:45:00.000Z'),
                                                           date('2020-04-15T02:46:00.000Z'), 1, 100)
    history_orders[0]['time'] = date(history_orders[0]['time'])
    history_orders[0]['doneTime'] = date(history_orders[0]['doneTime'])
    assert actual == {'historyOrders': history_orders, 'synchronizing': False}


@pytest.mark.asyncio
async def test_retrieve_deals_by_ticket():
    """Should retrieve MetaTrader deals from API by ticket."""

    deals = [{
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
    }]

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getDealsByTicket' and data['accountId'] == 'accountId' and \
                data['ticket'] == '46214692' and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'deals': deals,
                                        'synchronizing': False})

    actual = await client.get_deals_by_ticket('accountId', '46214692')
    deals[0]['time'] = date(deals[0]['time'])
    assert actual == {'deals': deals, 'synchronizing': False}


@pytest.mark.asyncio
async def test_retrieve_deals_by_position():
    """Should retrieve MetaTrader deals from API by position."""

    deals = [{
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
    }]

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getDealsByPosition' and data['accountId'] == 'accountId' and \
                data['positionId'] == '46214692' and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'deals': deals,
                                        'synchronizing': False})

    actual = await client.get_deals_by_position('accountId', '46214692')
    deals[0]['time'] = date(deals[0]['time'])
    assert actual == {'deals': deals, 'synchronizing': False}


@pytest.mark.asyncio
async def test_retrieve_deals_by_time_range():
    """Should retrieve MetaTrader deals from API by time range."""

    deals = [{
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
    }]

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getDealsByTimeRange' and data['accountId'] == 'accountId' and \
                data['startTime'] == '2020-04-15T02:45:00.000Z' and data['application'] == 'RPC' and \
                data['endTime'] == '2020-04-15T02:46:00.000Z' and data['offset'] == 1 and data['limit'] == 100:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'deals': deals,
                                        'synchronizing': False})

    actual = await client.get_deals_by_time_range('accountId', date('2020-04-15T02:45:00.000Z'),
                                                  date('2020-04-15T02:46:00.000Z'), 1, 100)
    deals[0]['time'] = date(deals[0]['time'])
    assert actual == {'deals': deals, 'synchronizing': False}


@pytest.mark.asyncio
async def test_remove_application():
    """Should remove application from API."""

    request_received = False

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'removeApplication' and data['accountId'] == 'accountId' \
                and data['application'] == 'application':
            nonlocal request_received
            request_received = True
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId']})

    await client.remove_application('accountId')
    assert request_received


@pytest.mark.asyncio
async def test_execute_trade():
    """Should execute a trade via new API version."""
    trade = {
        'actionType': 'ORDER_TYPE_SELL',
        'symbol': 'AUDNZD',
        'volume': 0.07,
        'expiration': {
            'type': 'ORDER_TIME_SPECIFIED',
            'time': date('2020-04-15T02:45:00.000Z')
        }
    }
    response = {
        'numericCode': 10009,
        'stringCode': 'TRADE_RETCODE_DONE',
        'message': 'Request completed',
        'orderId': '46870472'
    }
    client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)
    await sio.emit('response', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                'instanceIndex': 0, 'replicas': 1})

    await asyncio.sleep(0.1)

    @sio.on('request')
    async def on_request(sid, data):
        assert data['trade'] == trade
        if data['type'] == 'trade' and data['accountId'] == 'accountId' and data['application'] == 'application' \
                and data['instanceIndex'] == 0:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'response': response})

    actual = await client.trade('accountId', trade)
    assert actual == response


@pytest.mark.asyncio
async def test_execute_rpc_trade():
    """Should execute an RPC trade."""
    trade = {
        'actionType': 'ORDER_TYPE_SELL',
        'symbol': 'AUDNZD',
        'volume': 0.07,
        'expiration': {
            'type': 'ORDER_TIME_SPECIFIED',
            'time': date('2020-04-15T02:45:00.000Z')
        }
    }
    response = {
        'numericCode': 10009,
        'stringCode': 'TRADE_RETCODE_DONE',
        'message': 'Request completed',
        'orderId': '46870472'
    }
    client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)
    await sio.emit('response', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                'instanceIndex': 0, 'replicas': 1})

    await asyncio.sleep(0.1)

    @sio.on('request')
    async def on_request(sid, data):
        assert data['trade'] == trade
        if data['type'] == 'trade' and data['accountId'] == 'accountId' and data['application'] == 'RPC' \
                and 'instanceIndex' not in data:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'response': response})

    actual = await client.trade('accountId', trade, 'RPC')
    assert actual == response


@pytest.mark.asyncio
async def test_fail_trade_on_old_api():
    """Should execute a trade via API and receive trade error from old API version."""

    trade = {
        'actionType': 'ORDER_TYPE_SELL',
        'symbol': 'AUDNZD',
        'volume': 0.07
    }
    response = {
        'error': 10006,
        'description': 'TRADE_RETCODE_REJECT',
        'message': 'Request rejected',
        'orderId': '46870472'
    }

    @sio.on('request')
    async def on_request(sid, data):
        assert data['trade'] == trade
        if data['type'] == 'trade' and data['accountId'] == 'accountId' and data['application'] == 'application':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'response': response})

    try:
        await client.trade('accountId', trade)
        raise Exception('TradeException expected')
    except Exception as err:
        assert err.__class__.__name__ == 'TradeException'
        assert err.__str__() == 'Request rejected'
        assert err.stringCode == 'TRADE_RETCODE_REJECT'
        assert err.numericCode == 10006


@pytest.mark.asyncio
async def test_connect_to_terminal():
    """Should connect to MetaTrader terminal."""
    request_received = False

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'subscribe' and data['accountId'] == 'accountId' \
                and data['application'] == 'application' and data['instanceIndex'] == 1:
            nonlocal request_received
            request_received = True
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId']})

    await client.subscribe('accountId', 1)
    assert request_received


@pytest.mark.asyncio
async def test_create_new_instance():
    """Should create new instance when account limit is reached."""
    assert len(client.socket_instances['vint-hill'][0]) == 1
    for i in range(100):
        client._socketInstancesByAccounts[0]['accountId' + str(i)] = 0
        client._regionsByAccounts['accountId' + str(i)] = {'region': 'vint-hill', 'connections': 1}

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'subscribe' and data['accountId'] == 'accountId101' \
                and data['application'] == 'application' and data['instanceIndex'] == 0:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId']})

    client._regionsByAccounts['accountId101'] = {'region': 'vint-hill', 'connections': 1}
    await client.subscribe('accountId101', 0)
    assert len(client.socket_instances['vint-hill'][0]) == 2


@pytest.mark.asyncio
async def test_return_error_if_failed():
    """Should return error if connect to MetaTrader terminal failed."""
    request_received = False

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'subscribe' and data['accountId'] == 'accountId' \
                and data['application'] == 'application':
            nonlocal request_received
            request_received = True
        await sio.emit('processingError', {'id': 1, 'error': 'NotAuthenticatedError', 'message': 'Error message',
                                           'requestId': data['requestId']})

    success = True
    try:
        await client.subscribe('accountId')
        await asyncio.sleep(0.05)
        success = False
    except Exception as err:
        assert err.__class__.__name__ == 'NotConnectedException'
    assert success
    assert request_received


@pytest.mark.asyncio
async def test_retrieve_symbols():
    """Should retrieve symbols from API."""
    symbols = ['EURUSD']

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getSymbols' and data['accountId'] == 'accountId' and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'symbols': symbols})

    actual = await client.get_symbols('accountId')
    assert actual == symbols


@pytest.mark.asyncio
async def test_retrieve_symbol_specification():
    """Should retrieve symbol specification from API."""

    specification = {
        'symbol': 'AUDNZD',
        'tickSize': 0.00001,
        'minVolume': 0.01,
        'maxVolume': 100,
        'volumeStep': 0.01
    }

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getSymbolSpecification' and data['accountId'] == 'accountId' and \
                data['symbol'] == 'AUDNZD' and data['application'] == 'RPC':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'specification': specification})

    actual = await client.get_symbol_specification('accountId', 'AUDNZD')
    assert actual == specification


@pytest.mark.asyncio
async def test_retrieve_symbol_price():
    """Should retrieve symbol price from API."""

    price = {
        'symbol': 'AUDNZD',
        'bid': 1.05297,
        'ask': 1.05309,
        'profitTickValue': 0.59731,
        'lossTickValue': 0.59736
    }

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getSymbolPrice' and data['accountId'] == 'accountId' and \
                data['symbol'] == 'AUDNZD' and data['application'] == 'RPC' and data['keepSubscription']:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'price': price})

    actual = await client.get_symbol_price('accountId', 'AUDNZD', True)
    assert actual == price


@pytest.mark.asyncio
async def test_retrieve_candle():
    """Should retrieve candle from API."""

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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getCandle' and data['accountId'] == 'accountId' and \
                data['symbol'] == 'AUDNZD' and data['application'] == 'RPC' and data['timeframe'] == '15m' and \
                data['keepSubscription']:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'candle': candle})

    actual = await client.get_candle('accountId', 'AUDNZD', '15m', True)
    candle['time'] = date(candle['time'])
    assert actual == candle


@pytest.mark.asyncio
async def test_retrieve_tick():
    """Should retrieve latest tick from API."""
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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getTick' and data['accountId'] == 'accountId' and \
                data['symbol'] == 'AUDNZD' and data['application'] == 'RPC' and data['keepSubscription']:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'tick': tick})

    actual = await client.get_tick('accountId', 'AUDNZD', True)
    tick['time'] = date(tick['time'])
    assert actual == tick


@pytest.mark.asyncio
async def test_retrieve_book():
    """Should retrieve latest order book from API."""
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

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'getBook' and data['accountId'] == 'accountId' and \
                data['symbol'] == 'AUDNZD' and data['application'] == 'RPC' and data['keepSubscription']:
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId'], 'book': book})

    actual = await client.get_book('accountId', 'AUDNZD', True)
    book['time'] = date(book['time'])
    assert actual == book


@pytest.mark.asyncio
async def test_send_uptime_stats():
    """Should send uptime stats to the server."""

    @sio.on('request')
    async def on_request(sid, data):
        if data['type'] == 'saveUptime' and data['accountId'] == 'accountId' and \
                data['uptime'] == {'1h': 100} and data['application'] == 'application':
            await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                        'requestId': data['requestId']})
    await client.save_uptime('accountId', {'1h': 100})


class TestUnsubscribe:

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Should unsubscribe from account data."""
        request_received = False

        response = {'type': 'response', 'accountId': 'accountId'}
        assert 'accountId' in client.socket_instances_by_accounts[0]

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'unsubscribe' and data['accountId'] == 'accountId':
                nonlocal request_received
                request_received = True
                await sio.emit('response', {'requestId': data['requestId'], **response})

        await client.unsubscribe('accountId')
        assert request_received
        assert len(client.socket_instances_by_accounts.keys()) == 0

    @pytest.mark.asyncio
    async def test_ignore_not_found_unsubscribe(self):
        """Should ignore not found exception on unsubscribe."""

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError', {'id': 1, 'error': 'ValidationError', 'message': 'Validation failed',
                                               'details': [{'parameter': 'volume', 'message': 'Required value.'}],
                                               'requestId': data['requestId']})

        try:
            await client.unsubscribe('accountId')
            raise Exception('ValidationException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError', {'id': 2, 'error': 'NotFoundError', 'message': 'Account not found',
                                               'requestId': data['requestId']})

        await client.unsubscribe('accountId')

    @pytest.mark.asyncio
    async def test_ignore_timeout_error_on_unsubscribe(self):
        """Should ignore timeout error on unsubscribe."""
        client.rpc_request = AsyncMock(side_effect=TimeoutException('timeout'))
        await client.unsubscribe('accountId')

    @pytest.mark.asyncio
    async def test_repeat_unsubscription(self):
        """Should repeat unsubscription on synchronization packets if account must be unsubscribed."""
        with freeze_time() as frozen_datetime:
            frozen_datetime.move_to('2020-10-10 01:00:01.000')
            subscribe_server_handler = MagicMock()
            unsubscribe_server_handler = MagicMock()

            @sio.on('request')
            async def on_request(sid, data):
                server_handler = None
                if data['type'] == 'subscribe' and data['accountId'] == 'accountId':
                    server_handler = subscribe_server_handler
                elif data['type'] == 'unsubscribe' and data['accountId'] == 'accountId':
                    server_handler = unsubscribe_server_handler
                if server_handler:
                    server_handler()
                    response = {'type': 'response', 'accountId': 'accountId', 'requestId': data['requestId']}
                    await sio.emit('response', response)

            # Subscribing
            await client.subscribe('accountId', 0)
            await asyncio.sleep(0.05)
            assert subscribe_server_handler.call_count == 1
            # Unsubscribing
            await client.unsubscribe('accountId')
            await asyncio.sleep(0.05)
            assert unsubscribe_server_handler.call_count == 2
            # Sending a packet, should throttle first repeat unsubscribe request
            await sio.emit('synchronization', {
                'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1', 'connected': True, 'instanceIndex': 0
            })
            await asyncio.sleep(0.05)
            assert unsubscribe_server_handler.call_count == 2
            # Repeat a packet after a while, should unsubscribe again
            frozen_datetime.tick(11)
            await asyncio.sleep(0.05)
            await sio.emit('synchronization', {
                'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1', 'connected': True, 'instanceIndex': 0
            })
            await asyncio.sleep(0.05)
            assert unsubscribe_server_handler.call_count == 4
            # Repeat a packet, should throttle unsubscribe request
            await sio.emit('synchronization', {
                'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1', 'connected': True, 'instanceIndex': 0
            })
            await asyncio.sleep(0.05)
            assert unsubscribe_server_handler.call_count == 4
            # Repeat a packet after a while, should not throttle unsubscribe request
            frozen_datetime.tick(11)
            await sio.emit('synchronization', {
                'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1', 'connected': True, 'instanceIndex': 0
            })
            await asyncio.sleep(0.05)
            assert unsubscribe_server_handler.call_count == 6


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_handle_validation_exception(self):
        """Should handle ValidationError."""

        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD'
        }

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError', {'id': 1, 'error': 'ValidationError', 'message': 'Validation failed',
                           'details': [{'parameter': 'volume', 'message': 'Required value.'}],
                                               'requestId': data['requestId']})

        try:
            await client.trade('accountId', trade)
            raise Exception('ValidationError expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @pytest.mark.asyncio
    async def test_handle_not_found_exception(self):
        """Should handle NotFoundError."""

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError',  {'id': 1, 'error': 'NotFoundError',
                                                'message': 'Position id 1234 not found',
                                                'requestId': data['requestId']})

        try:
            await client.get_position('accountId', '1234')
            raise Exception('NotFoundException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'NotFoundException'

    @pytest.mark.asyncio
    async def test_handle_not_synchronized_exception(self):
        """Should handle NotSynchronizedError."""

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError', {'id': 1, 'error': 'NotSynchronizedError', 'message': 'Error message',
                                               'requestId': data['requestId']})

        try:
            await client.get_position('accountId', '1234')
            raise Exception('NotSynchronizedError expected')
        except Exception as err:
            assert err.__class__.__name__ == 'NotSynchronizedException'

    @pytest.mark.asyncio
    async def test_handle_not_connected_exception(self):
        """Should handle NotSynchronizedError."""

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError', {'id': 1, 'error': 'NotAuthenticatedError', 'message': 'Error message',
                                               'requestId': data['requestId']})

        try:
            await client.get_position('accountId', '1234')
            raise Exception('NotConnectedError expected')
        except Exception as err:
            assert err.__class__.__name__ == 'NotConnectedException'

    @pytest.mark.asyncio
    async def test_handle_other_exceptions(self):
        """Should handle other errors."""

        @sio.on('request')
        async def on_request(sid, data):
            await sio.emit('processingError', {'id': 1, 'error': 'Error', 'message': 'Error message',
                                               'requestId': data['requestId']})

        try:
            await client.get_position('accountId', '1234')
            raise Exception('InternalError expected')
        except Exception as err:
            assert err.__class__.__name__ == 'InternalException'


class TestConnectionStatusSynchronization:

    @pytest.fixture()
    def sub_active(self):
        client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)

    @pytest.mark.asyncio
    async def test_process_auth_sync_event(self, sub_active):
        """Should process authenticated synchronization event."""
        listener = MagicMock()
        listener.on_connected = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 1, 'replicas': 2})
        await future_close
        listener.on_connected.assert_called_with('1:ps-mpa-1', 2)

    @pytest.mark.asyncio
    async def test_send_trade_to_both_instances(self, sub_active):
        """Should send trade requests to both instances."""
        instance_called0 = False
        instance_called1 = False

        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD',
            'volume': 0.07,
        }
        response = {
            'numericCode': 10009,
            'stringCode': 'TRADE_RETCODE_DONE',
            'message': 'Request completed',
            'orderId': '46870472'
        }

        listener = MagicMock()
        listener.on_connected = AsyncMock()

        client.add_synchronization_listener('accountId', listener)

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'trade' and data['accountId'] == 'accountId' and data['application'] == 'application':
                if sid == connections[1]:
                    nonlocal instance_called1
                    instance_called1 = True
                elif sid == connections[2]:
                    nonlocal instance_called0
                    instance_called0 = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'response': response})

        await client.trade('accountId', trade, None, 'high')
        await asyncio.sleep(0.1)
        assert instance_called0
        assert instance_called1

    @pytest.mark.asyncio
    async def test_not_send_request_to_mismatching_instances(self, sub_active):
        """Should not send requests to mismatching instances."""
        request_received_assigned0 = False
        request_received_assigned1 = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'subscribe' and data['accountId'] == 'accountId' \
                    and data['application'] == 'application':
                if sid == connections[2] and data['instanceIndex'] == 0:
                    nonlocal request_received_assigned0
                    request_received_assigned0 = True
                    await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                                'requestId': data['requestId']})
                elif sid == connections[1] and data['instanceIndex'] == 1:
                    nonlocal request_received_assigned1
                    request_received_assigned1 = True
                    await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                                'requestId': data['requestId']})

        await client.subscribe('accountId', 0)
        assert request_received_assigned0
        await client.subscribe('accountId', 1)
        assert request_received_assigned1

        request_received_authenticated0 = False
        request_received_authenticated1 = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'removeApplication' and data['accountId'] == 'accountId' \
                    and data['application'] == 'application':
                if sid == connections[2] and data['instanceIndex'] == 0:
                    nonlocal request_received_authenticated0
                    request_received_authenticated0 = True
                    await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                                'requestId': data['requestId']})
                elif sid == connections[1] and data['instanceIndex'] == 1:
                    nonlocal request_received_authenticated1
                    request_received_authenticated1 = True
                    await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                                'requestId': data['requestId']})

        await client.remove_application('accountId')
        assert request_received_authenticated0
        assert not request_received_authenticated1

        request_received_authenticated0 = False

        client._connectedHosts = {'accountId:1:ps-mpa-1': 'ps-mpa-1'}

        await client.remove_application('accountId')
        assert not request_received_authenticated0
        assert request_received_authenticated1

        instance_called_trade0 = False
        instance_called_trade1 = False

        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD',
            'volume': 0.07,
        }
        response = {
            'numericCode': 10009,
            'stringCode': 'TRADE_RETCODE_DONE',
            'message': 'Request completed',
            'orderId': '46870472'
        }

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'trade' and data['accountId'] == 'accountId' \
                    and data['application'] == 'application':
                if sid == connections[2] and data['instanceIndex'] == 0:
                    nonlocal instance_called_trade0
                    instance_called_trade0 = True
                    await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                                'requestId': data['requestId'], 'response': response})
                elif sid == connections[1] and data['instanceIndex'] == 1:
                    nonlocal instance_called_trade1
                    instance_called_trade1 = True
                    await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                                'requestId': data['requestId'], 'response': response})

        client._connectedHosts = {'accountId:0:ps-mpa-1': 'ps-mpa-1'}
        await client.trade('accountId', trade, None, 'regular')
        assert instance_called_trade0
        assert not instance_called_trade1

        instance_called_trade0 = False
        client._connectedHosts = {'accountId:1:ps-mpa-1': 'ps-mpa-1'}

        await client.trade('accountId', trade, None, 'regular')
        assert not instance_called_trade0
        assert instance_called_trade1

    @pytest.mark.asyncio
    async def test_process_auth_sync_event_with_session_id(self, sub_active):
        """Should process authenticated synchronization event with session id."""
        listener = MagicMock()
        listener.on_connected = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'instanceIndex': 0,
                                           'replicas': 4, 'sessionId': 'wrong', 'host': 'ps-mpa-1'}, connections[2])
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'instanceIndex': 0,
                                           'replicas': 2, 'host': 'ps-mpa-1',
                                           'sessionId': client._socketInstances['vint-hill'][0][0]['sessionId']},
                       connections[2])
        await future_close
        assert listener.on_connected.call_count == 1
        listener.on_connected.assert_called_with('0:ps-mpa-1', 2)

    @pytest.mark.asyncio
    async def test_cancel_subscribe_on_authenticated_event(self, sub_active):
        """Should cancel subscribe on authenticated event."""
        cancel_subscribe_stub = MagicMock()
        client._subscriptionManager.cancel_subscribe = cancel_subscribe_stub
        cancel_account_stub = MagicMock()
        client._subscriptionManager.cancel_account = cancel_account_stub
        client._socketInstancesByAccounts[0]['accountId2'] = 0
        client._socketInstancesByAccounts[1]['accountId2'] = 0
        client._regionsByAccounts['accountId2'] = {'region': 'vint-hill', 'connections': 1}
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0, 'replicas': 2, 'sessionId': session_id})
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId2', 'host': 'ps-mpa-2',
                                           'instanceIndex': 0, 'replicas': 1, 'sessionId': session_id})
        await asyncio.sleep(0.05)
        cancel_subscribe_stub.assert_any_call('accountId:0')
        cancel_account_stub.assert_any_call('accountId2')

    @pytest.mark.asyncio
    async def test_process_broker_connection_status_event(self, sub_active):
        """Should process broker connection status event."""
        listener = MagicMock()
        listener.on_connected = AsyncMock()
        listener.on_broker_connection_status_changed = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0, 'replicas': 1}, connections[2])
        await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'connected': True, 'instanceIndex': 0}, connections[2])
        await future_close
        listener.on_broker_connection_status_changed.assert_called_with('0:ps-mpa-1', True)

    @pytest.mark.asyncio
    async def test_call_disconnect(self, sub_active):
        """Should call an on_disconnect if there was no signal for a long time"""
        with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 50)):
            listener = MagicMock()
            listener.on_connected = AsyncMock()
            listener.on_broker_connection_status_changed = AsyncMock()
            listener.on_stream_closed = AsyncMock()
            listener.on_disconnected = FinalMock()
            client.add_synchronization_listener('accountId', listener)
            await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'instanceIndex': 0, 'replicas': 2}, connections[2])
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'connected': True, 'instanceIndex': 0}, connections[2])
            await sleep(0.2)
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'connected': True, 'instanceIndex': 0}, connections[2])
            await sleep(1.1)
            listener.on_disconnected.assert_not_called()
            await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'instanceIndex': 0, 'replicas': 2}, connections[2])
            await sleep(0.2)
            listener.on_disconnected.assert_not_called()
            await sleep(1.1)
            listener.on_disconnected.assert_called_with('0:ps-mpa-1')

    @pytest.mark.asyncio
    async def test_close_stream_on_timeout(self, sub_active):
        """Should close stream on timeout if another stream exists"""
        with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 50)):
            listener = MagicMock()
            listener.on_connected = AsyncMock()
            listener.on_broker_connection_status_changed = AsyncMock()
            listener.on_disconnected = FinalMock()
            listener.on_stream_closed = AsyncMock()
            client._subscriptionManager.on_timeout = AsyncMock()
            client._subscriptionManager.on_disconnected = AsyncMock()
            client.add_synchronization_listener('accountId', listener)
            await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'instanceIndex': 0, 'replicas': 2})
            await sleep(0.3)
            await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                               'instanceIndex': 0, 'replicas': 2})
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'connected': True, 'instanceIndex': 0})
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                               'connected': True, 'instanceIndex': 0})
            await sleep(0.3)
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'connected': True, 'instanceIndex': 0})
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                               'connected': True, 'instanceIndex': 0})
            await sleep(1.1)
            listener.on_disconnected.assert_not_called()
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                               'connected': True, 'instanceIndex': 0})
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                               'connected': True, 'instanceIndex': 0})
            await sleep(0.3)
            await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                               'connected': True, 'instanceIndex': 0})
            listener.on_disconnected.assert_not_called()
            await sleep(1.1)
            listener.on_stream_closed.assert_called_with('0:ps-mpa-1')
            listener.on_disconnected.assert_not_called()
            client._subscriptionManager.on_timeout.assert_not_called()
            await sleep(0.3)
            listener.on_disconnected.assert_called_with('0:ps-mpa-2')
            client._subscriptionManager.on_disconnected.assert_not_called()
            client._subscriptionManager.on_timeout.assert_called_with('accountId', 0)

    @pytest.mark.asyncio
    async def test_process_server_health_status(self, sub_active):
        """Should process server-side health status event."""
        listener = MagicMock()
        listener.on_connected = AsyncMock()
        listener.on_broker_connection_status_changed = AsyncMock()
        listener.on_health_status = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 1, 'replicas': 1})
        await sio.emit('synchronization', {'type': 'status', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'connected': True, 'healthStatus': {'restApiHealthy': True},
                                           'instanceIndex': 1})
        await future_close
        listener.on_health_status.assert_called_with('1:ps-mpa-1', {'restApiHealthy': True})

    @pytest.mark.asyncio
    async def test_process_disconnected_synchronization_event(self, sub_active):
        """Should process disconnected synchronization event."""

        listener = MagicMock()
        listener.on_connected = AsyncMock()
        listener.on_stream_closed = FinalMock()
        listener.on_disconnected = AsyncMock()
        client._subscriptionManager.on_disconnected = AsyncMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0, 'replicas': 1})
        await sio.emit('synchronization', {'type': 'disconnected', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0})
        await future_close
        client._subscriptionManager.on_disconnected.assert_called_with('accountId', 0)
        listener.on_disconnected.assert_called_with('0:ps-mpa-1')
        listener.on_stream_closed.assert_called_with('0:ps-mpa-1')

    @pytest.mark.asyncio
    async def test_on_stream_closed(self, sub_active):
        """Should close the stream if host name disconnected and another stream exists."""

        listener = MagicMock()
        listener.on_connected = AsyncMock()
        listener.on_disconnected = FinalMock()
        listener.on_stream_closed = AsyncMock()
        client._subscriptionManager.on_disconnected = AsyncMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0, 'replicas': 2})
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                           'instanceIndex': 0, 'replicas': 2})
        await sio.emit('synchronization', {'type': 'disconnected', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0})
        await asyncio.sleep(0.1)
        listener.on_stream_closed.assert_called_with('0:ps-mpa-1')
        listener.on_disconnected.assert_not_called()
        client._subscriptionManager.on_disconnected.assert_not_called()
        await sio.emit('synchronization', {'type': 'disconnected', 'accountId': 'accountId', 'host': 'ps-mpa-2',
                                           'instanceIndex': 0})
        await future_close
        listener.on_disconnected.assert_called()
        client._subscriptionManager.on_disconnected.assert_called_with('accountId', 0)


class TestTerminalStateSynchronization:

    @pytest.fixture()
    def sub_active(self):
        client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)

    @pytest.mark.asyncio
    async def test_accept_own_packets(self, sub_active):
        """Should only accept packets with own synchronization ids."""
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].schedule_synchronize = AsyncMock()
        listener = MagicMock()
        listener.on_account_information_updated = AsyncMock()
        listener.on_synchronization_started = AsyncMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'accountInformation', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0},
                       connections[2])
        await asyncio.sleep(0.05)
        assert listener.on_account_information_updated.call_count == 1
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'synchronizationId': 'synchronizationId',
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'}, connections[2])
        await asyncio.sleep(0.05)
        await sio.emit('synchronization', {'type': 'accountInformation', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0,
                                           'synchronizationId': 'wrong'}, connections[2])
        await asyncio.sleep(0.05)
        assert listener.on_account_information_updated.call_count == 1
        await sio.emit('synchronization', {'type': 'accountInformation', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0,
                                           'synchronizationId': 'synchronizationId'}, connections[2])
        await asyncio.sleep(0.1)
        assert listener.on_account_information_updated.call_count == 2

    @pytest.mark.asyncio
    async def test_synchronize_with_metatrader_terminal(self, sub_active):
        """Should synchronize with MetaTrader terminal."""

        request_received = False

        async def get_hashes():
            return {
                'specificationsMd5': '1111',
                'positionsMd5': '2222',
                'ordersMd5': '3333'
            }

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'synchronize' and data['accountId'] == 'accountId' and \
                    data['host'] == 'ps-mpa-1' and \
                    data['startingHistoryOrderTime'] == '2020-01-01T00:00:00.000Z' and \
                    data['startingDealTime'] == '2020-01-02T00:00:00.000Z' and \
                    data['requestId'] == 'synchronizationId' and data['application'] == 'application' and \
                    data['instanceIndex'] == 0:
                nonlocal request_received
                request_received = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})

        await client.synchronize('accountId', 0, 'ps-mpa-1', 'synchronizationId', date('2020-01-01T00:00:00.000Z'),
                                 date('2020-01-02T00:00:00.000Z'), get_hashes)
        assert request_received

    @pytest.mark.asyncio
    async def test_process_sync_started(self, sub_active):
        """Should process synchronization started event."""
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        listener = MagicMock()
        listener.on_synchronization_started = AsyncMock()
        listener.on_positions_synchronized = AsyncMock()
        listener.on_pending_orders_synchronized = AsyncMock()
        listener.on_account_information_updated = AsyncMock()

        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'synchronizationId': 'synchronizationId',
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await sio.emit('synchronization', {'type': 'accountInformation', 'synchronizationId': 'synchronizationId',
                                           'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0})
        await asyncio.sleep(0.05)
        listener.on_synchronization_started.assert_called_with(
            '0:ps-mpa-1', specifications_updated=True, positions_updated=True, orders_updated=True,
            synchronization_id='synchronizationId')
        listener.on_positions_synchronized.assert_not_called()
        listener.on_pending_orders_synchronized.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_sync_started_with_no_updates(self, sub_active):
        """Should process synchronization started event with no updates."""
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        listener = MagicMock()
        listener.on_synchronization_started = AsyncMock()
        listener.on_positions_synchronized = AsyncMock()
        listener.on_pending_orders_synchronized = AsyncMock()
        listener.on_account_information_updated = AsyncMock()

        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'synchronizationId': 'synchronizationId',
                                           'specificationsUpdated': False,
                                           'positionsUpdated': False, 'ordersUpdated': False,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await sio.emit('synchronization', {'type': 'accountInformation', 'synchronizationId': 'synchronizationId',
                                           'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0})
        await asyncio.sleep(0.05)
        listener.on_synchronization_started.assert_called_with(
            '0:ps-mpa-1', specifications_updated=False, positions_updated=False, orders_updated=False,
            synchronization_id='synchronizationId')
        listener.on_positions_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')
        listener.on_pending_orders_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')

    @pytest.mark.asyncio
    async def test_process_sync_started_without_updating_positions(self, sub_active):
        """Should process synchronization started event without updating positions."""
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
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        listener = MagicMock()
        listener.on_synchronization_started = AsyncMock()
        listener.on_positions_synchronized = AsyncMock()
        listener.on_pending_orders_replaced = AsyncMock()
        listener.on_pending_orders_synchronized = AsyncMock()
        listener.on_account_information_updated = AsyncMock()

        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'synchronizationId': 'synchronizationId',
                                           'positionsUpdated': False, 'ordersUpdated': True,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await sio.emit('synchronization', {'type': 'accountInformation', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0,
                                           'synchronizationId': 'synchronizationId'})
        await asyncio.sleep(0.05)
        listener.on_synchronization_started.assert_called_with(
            '0:ps-mpa-1', specifications_updated=True, positions_updated=False, orders_updated=True,
            synchronization_id='synchronizationId')
        listener.on_positions_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')
        listener.on_pending_orders_synchronized.assert_not_called()
        await sio.emit('synchronization', {'type': 'orders', 'accountId': 'accountId', 'orders': orders,
                                           'synchronizationId': 'synchronizationId',
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await asyncio.sleep(0.05)
        listener.on_pending_orders_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')

    @pytest.mark.asyncio
    async def test_process_sync_started_without_updating_orders(self, sub_active):
        """Should process synchronization started event without updating orders."""
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
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        listener = MagicMock()
        listener.on_synchronization_started = AsyncMock()
        listener.on_positions_synchronized = AsyncMock()
        listener.on_positions_replaced = AsyncMock()
        listener.on_pending_orders_synchronized = AsyncMock()
        listener.on_account_information_updated = AsyncMock()

        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'synchronizationId': 'synchronizationId',
                                           'positionsUpdated': True, 'ordersUpdated': False,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await sio.emit('synchronization', {'type': 'accountInformation', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0,
                                           'synchronizationId': 'synchronizationId'})
        await asyncio.sleep(0.05)
        listener.on_synchronization_started.assert_called_with(
            '0:ps-mpa-1', specifications_updated=True, positions_updated=True, orders_updated=False,
            synchronization_id='synchronizationId')
        listener.on_positions_synchronized.assert_not_called()
        listener.on_pending_orders_synchronized.assert_not_called()
        await sio.emit('synchronization', {'type': 'positions', 'accountId': 'accountId', 'positions': positions,
                                           'synchronizationId': 'synchronizationId',
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await asyncio.sleep(0.05)
        listener.on_positions_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')
        listener.on_pending_orders_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')

    @pytest.mark.asyncio
    async def test_synchronize_account_information(self, sub_active):
        """Should synchronize account information."""
        listener = MagicMock()
        listener.on_account_information_updated = FinalMock()

        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'accountInformation', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'accountInformation': account_information, 'instanceIndex': 0})
        await future_close
        listener.on_account_information_updated.assert_called_with('0:ps-mpa-1', account_information)

    @pytest.mark.asyncio
    async def test_synchronize_positions(self, sub_active):
        """Should synchronize positions."""

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
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        listener = MagicMock()
        listener.on_positions_replaced = AsyncMock()
        listener.on_positions_synchronized = FinalMock()

        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'synchronizationId': 'synchronizationId',
                                           'positionsUpdated': True, 'ordersUpdated': False,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await asyncio.sleep(0.05)
        await sio.emit('synchronization', {'type': 'positions', 'accountId': 'accountId', 'positions': positions,
                                           'synchronizationId': 'synchronizationId',
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await future_close
        positions[0]['time'] = date(positions[0]['time'])
        positions[0]['updateTime'] = date(positions[0]['updateTime'])
        listener.on_positions_replaced.assert_called_with('0:ps-mpa-1', positions)
        listener.on_positions_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')

    @pytest.mark.asyncio
    async def test_synchronize_orders(self, sub_active):
        """Should synchronize orders."""

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
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        listener = MagicMock()
        listener.on_synchronization_started = AsyncMock()
        listener.on_pending_orders_replaced = AsyncMock()
        listener.on_pending_orders_synchronized = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'sequenceTimestamp': 1603124267178,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'synchronizationId'})
        await asyncio.sleep(0.05)
        await sio.emit('synchronization', {'type': 'orders', 'accountId': 'accountId', 'orders': orders,
                                           'synchronizationId': 'synchronizationId',
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await future_close
        orders[0]['time'] = date(orders[0]['time'])
        listener.on_pending_orders_replaced.assert_called_with('0:ps-mpa-1', orders)
        listener.on_pending_orders_synchronized.assert_called_with('0:ps-mpa-1', 'synchronizationId')

    @pytest.mark.asyncio
    async def test_synchronize_history_orders(self, sub_active):
        """Should synchronize history orders."""

        history_orders = [{
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
        }]
        listener = MagicMock()
        listener.on_history_order_added = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'historyOrders', 'accountId': 'accountId',
                                           'historyOrders': history_orders, 'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await future_close
        history_orders[0]['time'] = date(history_orders[0]['time'])
        history_orders[0]['doneTime'] = date(history_orders[0]['doneTime'])
        listener.on_history_order_added.assert_called_with('0:ps-mpa-1', history_orders[0])

    @pytest.mark.asyncio
    async def test_synchronize_deals(self, sub_active):
        """Should synchronize deals."""

        deals = [{
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
        }]
        listener = MagicMock()
        listener.on_deal_added = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'deals', 'accountId': 'accountId', 'deals': deals,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1'})
        await future_close
        deals[0]['time'] = date(deals[0]['time'])
        listener.on_deal_added.assert_called_with('0:ps-mpa-1', deals[0])

    @pytest.mark.asyncio
    async def test_process_synchronization_updates(self, sub_active):
        """Should process synchronization updates."""

        update = {
            'accountInformation': {
                'broker': 'True ECN Trading Ltd',
                'currency': 'USD',
                'server': 'ICMarketsSC-Demo',
                'balance': 7319.9,
                'equity': 7306.649913200001,
                'margin': 184.1,
                'freeMargin': 7120.22,
                'leverage': 100,
                'marginLevel': 3967.58283542
            },
            'updatedPositions': [{
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
            }],
            'removedPositionIds': ['1234'],
            'updatedOrders': [{
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
            }],
            'completedOrderIds': ['2345'],
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
            }]
        }
        listener = MagicMock()
        listener.on_account_information_updated = AsyncMock()
        listener.on_position_updated = AsyncMock()
        listener.on_position_removed = AsyncMock()
        listener.on_pending_order_updated = AsyncMock()
        listener.on_pending_order_completed = AsyncMock()
        listener.on_history_order_added = AsyncMock()
        listener.on_deal_added = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        emit = copy.deepcopy(update)
        emit['type'] = 'update'
        emit['accountId'] = 'accountId'
        emit['instanceIndex'] = 0
        emit['host'] = 'ps-mpa-1'
        await sio.emit('synchronization', emit)
        await future_close
        update['updatedPositions'][0]['time'] = date(update['updatedPositions'][0]['time'])
        update['updatedPositions'][0]['updateTime'] = date(update['updatedPositions'][0]['updateTime'])
        update['updatedOrders'][0]['time'] = date(update['updatedOrders'][0]['time'])
        update['historyOrders'][0]['time'] = date(update['historyOrders'][0]['time'])
        update['historyOrders'][0]['doneTime'] = date(update['historyOrders'][0]['doneTime'])
        update['deals'][0]['time'] = date(update['deals'][0]['time'])
        listener.on_account_information_updated.assert_called_with('0:ps-mpa-1', update['accountInformation'])
        listener.on_position_updated.assert_called_with('0:ps-mpa-1', update['updatedPositions'][0])
        listener.on_position_removed.assert_called_with('0:ps-mpa-1', update['removedPositionIds'][0])
        listener.on_pending_order_updated.assert_called_with('0:ps-mpa-1', update['updatedOrders'][0])
        listener.on_pending_order_completed.assert_called_with('0:ps-mpa-1', update['completedOrderIds'][0])
        listener.on_history_order_added.assert_called_with('0:ps-mpa-1', update['historyOrders'][0])
        listener.on_deal_added.assert_called_with('0:ps-mpa-1', update['deals'][0])

    @pytest.mark.asyncio
    async def test_retrieve_server_time(self):
        """Should retrieve server time from API."""
        server_time = {
            'time': '2022-01-01T00:00:00.000Z',
            'brokerTime': '2022-01-01 02:00:00.000Z'
        }

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'getServerTime' and data['accountId'] == 'accountId' and data['application'] == 'RPC':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'serverTime': server_time})

        actual = await client.get_server_time('accountId')
        server_time = deepcopy(server_time)
        server_time['time'] = date(server_time['time'])
        assert actual == server_time

    @pytest.mark.asyncio
    async def test_calculate_margin(self):
        """Should calculate margin."""
        margin = {
            'margin': 110
        }
        order = {
            'symbol': 'EURUSD',
            'type': 'ORDER_TYPE_BUY',
            'volume': 0.1,
            'openPrice': 1.1
        }

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'calculateMargin' and data['accountId'] == 'accountId' and \
                    data['application'] == 'MetaApi' and json.dumps(data['order'] == json.dumps(order)):
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'margin': margin})

        actual = await client.calculate_margin('accountId', 'MetaApi', 'high', order)
        assert actual == margin


class TestMarketDataSynchronization:

    @pytest.fixture()
    def sub_active(self):
        client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, sub_active):
        """Should retry request on failure."""
        request_counter = 0
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

        @sio.on('request')
        async def on_request(sid, data):
            nonlocal request_counter
            if request_counter > 1 and data['type'] == 'getOrder' and data['accountId'] == 'accountId' and \
                    data['orderId'] == '46871284' and data['application'] == 'RPC':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'order': order})
            request_counter += 1

        actual = await client.get_order('accountId', '46871284')
        order['time'] = date(order['time'])
        assert actual == order

    @pytest.mark.asyncio
    async def test_retry_too_many_requests(self, sub_active):
        """Should wait specified amount of time on too many requests exception."""
        request_counter = 0
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

        @sio.on('request')
        async def on_request(sid, data):
            nonlocal request_counter
            if request_counter > 0 and data['type'] == 'getOrder' and data['accountId'] == 'accountId' and \
                    data['orderId'] == '46871284' and data['application'] == 'RPC':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'order': order})
            else:
                await sio.emit('processingError', {
                    'id': 1, 'requestId': data['requestId'], 'error': 'TooManyRequestsError',
                    'message': 'The API allows 10000 requests per 60 minutes ' +
                    'to avoid overloading our servers.', 'status_code': 429, 'metadata': {
                        'periodInMinutes': 60, 'maxRequestsForPeriod': 10000,
                        'recommendedRetryTime': format_date(datetime.now() + timedelta(seconds=1))}})
            request_counter += 1

        start_time = datetime.now().timestamp()
        actual = await client.get_order('accountId', '46871284')
        order['time'] = date(order['time'])
        assert actual == order
        assert 0.9 < datetime.now().timestamp() - start_time < 1.1

    @pytest.mark.asyncio
    async def test_return_too_many_requests_if_long_wait(self, sub_active):
        """Should return too many requests exception if recommended time is beyond max request time."""
        request_counter = 0
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

        @sio.on('request')
        async def on_request(sid, data):
            nonlocal request_counter
            if request_counter > 0 and data['type'] == 'getOrder' and data['accountId'] == 'accountId' and \
                    data['orderId'] == '46871284' and data['application'] == 'RPC':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'order': order})
            else:
                await sio.emit('processingError', {
                    'id': 1, 'requestId': data['requestId'], 'error': 'TooManyRequestsError',
                    'message': 'The API allows 10000 requests per 60 minutes ' +
                    'to avoid overloading our servers.', 'status_code': 429, 'metadata': {
                        'periodInMinutes': 60, 'maxRequestsForPeriod': 10000,
                        'recommendedRetryTime': format_date(datetime.now() + timedelta(seconds=60))}})
            request_counter += 1

        try:
            await client.get_order('accountId', '46871284')
            raise Exception('TooManyRequestsException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TooManyRequestsException'
            await client.close()

    @pytest.mark.asyncio
    async def test_not_retry_on_failure(self, sub_active):
        """Should not retry request on validation error."""
        request_counter = 0

        @sio.on('request')
        async def on_request(sid, data):
            nonlocal request_counter
            if request_counter > 0 and data['type'] == 'subscribeToMarketData' and data['accountId'] == 'accountId' \
                    and data['symbol'] == 'EURUSD' and data['application'] == 'application' and \
                    data['instanceIndex'] == 1:
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})
            else:
                await sio.emit('processingError', {'id': 1, 'error': 'ValidationError', 'message': 'Validation failed',
                                                   'details': [{'parameter': 'volume', 'message': 'Required value.'}],
                                                   'requestId': data['requestId']})
            request_counter += 1
            try:
                await client.subscribe_to_market_data('accountId', 1, 'EURUSD')
                raise Exception('ValidationException expected')
            except Exception as err:
                assert err.__class__.__name__ == 'ValidationException'
                await client.close()
            assert request_counter == 1

    @pytest.mark.asyncio
    async def test_not_retry_trade(self, sub_active):
        """Should not retry trade requests on fail."""
        request_counter = 0
        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD',
            'volume': 0.07
        }

        @sio.on('request')
        async def on_request(sid, data):
            nonlocal request_counter
            if request_counter > 0:
                pytest.fail()
            request_counter += 1

        try:
            await client.trade('accountId', trade)
            raise Exception('TimeoutException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            await client.close()

    @pytest.mark.asyncio
    async def test_not_retry_if_connection_closed_between_retries(self, sub_active):
        """Should not retry request if connection closed between retries."""
        request_counter = 0
        response = {'type': 'response', 'accountId': 'accountId'}

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'unsubscribe' and data['accountId'] == 'accountId':
                await sio.emit('response', {'requestId': data['requestId'], **response})

            if data['type'] == 'getOrders' and data['accountId'] == 'accountId' \
                    and data['application'] == 'RPC':
                nonlocal request_counter
                request_counter += 1
                await sio.emit('processingError',
                               {'id': 1, 'error': 'NotSynchronizedError', 'message': 'Error message',
                                'requestId': data['requestId']})

        asyncio.create_task(client.unsubscribe('accountId'))
        try:
            await client.get_orders('accountId')
            raise Exception('NotSynchronizedException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'NotSynchronizedException'
            await client.close()
        assert request_counter == 1
        assert 'accountId' not in client.socket_instances_by_accounts

    @pytest.mark.asyncio
    async def test_timeout_on_no_response(self, sub_active):
        """Should return timeout error if no server response received."""

        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD',
            'volume': 0.07
        }

        @sio.on('request')
        async def on_request(sid, data):
            pass

        try:
            await client.trade('accountId', trade)
            raise Exception('TimeoutException expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            await client.close()

    @pytest.mark.asyncio
    async def test_subscribe_to_market_data_with_mt_terminal(self, sub_active):
        """Should subscribe to market data with MetaTrader terminal."""

        request_received = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'subscribeToMarketData' and data['accountId'] == 'accountId' and \
                    data['symbol'] == 'EURUSD' and data['application'] == 'application' and \
                    data['instanceIndex'] == 0 and data['subscriptions'] == [{'type': 'quotes'}]:
                nonlocal request_received
                request_received = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})

        await client.subscribe_to_market_data('accountId', 'EURUSD', [{'type': 'quotes'}], 'regular')
        assert request_received

    @pytest.mark.asyncio
    async def test_subscribe_to_market_data_with_mt_terminal_high_reliability(self, sub_active):
        """Should subscribe to market data with MetaTrader terminal for high reliability account."""

        request_received = False
        request_received1 = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'subscribeToMarketData' and data['accountId'] == 'accountId' and \
                    data['symbol'] == 'EURUSD' and data['application'] == 'application' and \
                    data['subscriptions'] == [{'type': 'quotes'}]:
                if data['instanceIndex'] == 0 and sid == connections[2]:
                    nonlocal request_received
                    request_received = True
                elif data['instanceIndex'] == 1 and sid == connections[1]:
                    nonlocal request_received1
                    request_received1 = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})

        await client.subscribe_to_market_data('accountId', 'EURUSD', [{'type': 'quotes'}], 'high')
        assert request_received
        assert request_received1

    @pytest.mark.asyncio
    async def test_refresh_market_data_subscriptions(self, sub_active):
        """Should refresh market data subscriptions."""
        request_received = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'refreshMarketDataSubscriptions' and data['accountId'] == 'accountId' and \
                    data['application'] == 'application' and data['instanceIndex'] == 1 and \
                    data['subscriptions'] == [{'symbol': 'EURUSD'}]:
                nonlocal request_received
                request_received = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})

        await client.refresh_market_data_subscriptions('accountId', 1, [{'symbol': 'EURUSD'}])
        assert request_received

    @pytest.mark.asyncio
    async def test_unsubscribe_from_market_data_with_mt_terminal(self, sub_active):
        """Should unsubscribe from market data with MetaTrader terminal."""

        request_received = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'unsubscribeFromMarketData' and data['accountId'] == 'accountId' and \
                    data['symbol'] == 'EURUSD' and data['application'] == 'application' and \
                    data['instanceIndex'] == 0 and data['subscriptions'] == [{'type': 'quotes'}]:
                nonlocal request_received
                request_received = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})

        await client.unsubscribe_from_market_data('accountId', 'EURUSD', [{'type': 'quotes'}], 'regular')
        assert request_received

    @pytest.mark.asyncio
    async def test_synchronize_symbol_specifications(self, sub_active):
        """Should synchronize symbol specifications."""

        specifications = [{
            'symbol': 'EURUSD',
            'tickSize': 0.00001,
            'minVolume': 0.01,
            'maxVolume': 200,
            'volumeStep': 0.01
        }]
        listener = MagicMock()
        listener.on_symbol_specifications_updated = AsyncMock()
        listener.on_symbol_specification_updated = AsyncMock()
        listener.on_symbol_specification_removed = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'specifications', 'accountId': 'accountId',
                                           'specifications': specifications, 'instanceIndex': 1,
                                           'removedSymbols': ['AUDNZD'], 'host': 'ps-mpa-1'})
        await future_close
        listener.on_symbol_specifications_updated.assert_called_with('1:ps-mpa-1', specifications, ['AUDNZD'])
        listener.on_symbol_specification_updated.assert_called_with('1:ps-mpa-1', specifications[0])
        listener.on_symbol_specification_removed.assert_called_with('1:ps-mpa-1', 'AUDNZD')

    @pytest.mark.asyncio
    async def test_synchronize_symbol_prices(self, sub_active):
        """Should synchronize symbol prices."""

        prices = [{
            'symbol': 'AUDNZD',
            'bid': 1.05916,
            'ask': 1.05927,
            'profitTickValue': 0.602,
            'lossTickValue': 0.60203
        }]
        ticks = [{
            'symbol': 'AUDNZD',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'bid': 1.05297,
            'ask': 1.05309,
            'last': 0.5298,
            'volume': 0.13,
            'side': 'buy'
        }]
        candles = [{
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
        }]
        books = [{
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
        }]
        listener = MagicMock()
        listener.on_symbol_prices_updated = AsyncMock()
        listener.on_candles_updated = AsyncMock()
        listener.on_ticks_updated = AsyncMock()
        listener.on_books_updated = AsyncMock()
        listener.on_symbol_price_updated = FinalMock()
        client.add_synchronization_listener('accountId', listener)
        await sio.emit('synchronization', {'type': 'prices', 'accountId': 'accountId', 'prices': prices,
                                           'ticks': ticks, 'candles': candles, 'books': books,
                                           'equity': 100, 'margin': 200, 'freeMargin': 400, 'marginLevel': 40000,
                                           'instanceIndex': 1, 'host': 'ps-mpa-1'})
        await future_close
        ticks[0]['time'] = date(ticks[0]['time'])
        candles[0]['time'] = date(candles[0]['time'])
        books[0]['time'] = date(books[0]['time'])
        listener.on_symbol_prices_updated.assert_called_with('1:ps-mpa-1', prices, 100, 200, 400, 40000, None)
        listener.on_candles_updated.assert_called_with('1:ps-mpa-1', candles, 100, 200, 400, 40000, None)
        listener.on_ticks_updated.assert_called_with('1:ps-mpa-1', ticks, 100, 200, 400, 40000, None)
        listener.on_books_updated.assert_called_with('1:ps-mpa-1', books, 100, 200, 400, 40000, None)
        listener.on_symbol_price_updated.assert_called_with('1:ps-mpa-1', prices[0])


class TestServerSideSynchronization:

    @pytest.mark.asyncio
    async def test_wait_for_server_side_sync(self):
        """Should wait for server-side terminal state synchronization."""

        request_received = False

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'waitSynchronized' and data['accountId'] == 'accountId' and \
                    data['applicationPattern'] == 'app.*' and data['timeoutInSeconds'] == 10 \
                    and data['application'] == 'application' and data['instanceIndex'] == 1:
                nonlocal request_received
                request_received = True
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId']})

        await client.wait_synchronized('accountId', 1, 'app.*', 10)
        assert request_received


class TestLatencyMonitoring:

    @pytest.fixture()
    def sub_active(self):
        client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)

    @pytest.mark.asyncio
    async def test_invoke_latency_listener(self, sub_active):
        """Should invoke latency listener on response."""

        account_id = None
        request_type = None
        actual_timestamps = None

        async def on_response(aid, type, ts):
            nonlocal account_id
            account_id = aid
            nonlocal request_type
            request_type = type
            nonlocal actual_timestamps
            actual_timestamps = ts

        listener = MagicMock()
        listener.on_response = on_response
        client.add_latency_listener(listener)
        price = {}
        timestamps = None

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'getSymbolPrice' and data['accountId'] == 'accountId' and data['symbol'] == \
                    'AUDNZD' and data['application'] == 'RPC' and 'clientProcessingStarted' in data['timestamps']:
                nonlocal timestamps
                timestamps = deepcopy(data['timestamps'])
                timestamps['serverProcessingStarted'] = format_date(datetime.now())
                timestamps['serverProcessingFinished'] = format_date(datetime.now())
                timestamps['clientProcessingStarted'] = format_date(date(timestamps['clientProcessingStarted']))
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'price': price, 'timestamps': timestamps})

        await client.get_symbol_price('accountId', 'AUDNZD')
        await asyncio.sleep(0.05)
        assert account_id == 'accountId'
        assert request_type == 'getSymbolPrice'
        assert actual_timestamps['clientProcessingStarted'] == date(timestamps['clientProcessingStarted'])
        assert actual_timestamps['serverProcessingStarted'] == date(timestamps['serverProcessingStarted'])
        assert actual_timestamps['serverProcessingFinished'] == date(timestamps['serverProcessingFinished'])
        assert 'clientProcessingFinished' in actual_timestamps

    @pytest.mark.asyncio
    async def test_measure_price_latencies(self, sub_active):
        """Should measure price streaming latencies."""
        prices = [{
            'symbol': 'AUDNZD',
            'timestamps': {
                'eventGenerated': format_date(datetime.now()),
                'serverProcessingStarted': format_date(datetime.now()),
                'serverProcessingFinished': format_date(datetime.now())
            }
        }]
        account_id = None
        symbol = None
        actual_timestamps = None
        listener = MagicMock()

        async def on_symbol_price(aid, sym, ts):
            nonlocal account_id
            account_id = aid
            nonlocal symbol
            symbol = sym
            nonlocal actual_timestamps
            actual_timestamps = ts
            await close_client()

        listener.on_symbol_price = on_symbol_price
        client.add_latency_listener(listener)
        await sio.emit('synchronization', {'type': 'prices', 'accountId': 'accountId', 'prices': prices,
                                           'equity': 100, 'margin': 200, 'freeMargin': 400, 'marginLevel': 40000})
        await future_close
        assert account_id == 'accountId'
        assert symbol == 'AUDNZD'
        assert actual_timestamps['serverProcessingFinished'] == \
            date(prices[0]['timestamps']['serverProcessingFinished'])
        assert actual_timestamps['serverProcessingStarted'] == \
               date(prices[0]['timestamps']['serverProcessingStarted'])
        assert actual_timestamps['eventGenerated'] == \
               date(prices[0]['timestamps']['eventGenerated'])
        assert 'clientProcessingFinished' in actual_timestamps

    @pytest.mark.asyncio
    async def test_measure_update_latencies(self, sub_active):
        """Should measure update latencies."""
        update = {
            'timestamps': {
                'eventGenerated': format_date(datetime.now()),
                'serverProcessingStarted': format_date(datetime.now()),
                'serverProcessingFinished': format_date(datetime.now())
            }
        }
        account_id = None
        actual_timestamps = None
        listener = MagicMock()

        async def on_update(aid, ts):
            nonlocal account_id
            account_id = aid
            nonlocal actual_timestamps
            actual_timestamps = ts
            await close_client()

        listener.on_update = on_update
        client.add_latency_listener(listener)
        await sio.emit('synchronization', {'type': 'update', 'accountId': 'accountId', **update})
        await future_close
        assert account_id == 'accountId'
        assert actual_timestamps['serverProcessingFinished'] == \
               date(update['timestamps']['serverProcessingFinished'])
        assert actual_timestamps['serverProcessingStarted'] == \
               date(update['timestamps']['serverProcessingStarted'])
        assert actual_timestamps['eventGenerated'] == \
               date(update['timestamps']['eventGenerated'])
        assert 'clientProcessingFinished' in actual_timestamps

    @pytest.mark.asyncio
    async def test_process_trade_latency(self, sub_active):
        """Should process trade latency."""
        trade = {}
        response = {
            'numericCode': 10009,
            'stringCode': 'TRADE_RETCODE_DONE',
            'message': 'Request completed',
            'orderId': '46870472'
        }
        timestamps = {
            'clientExecutionStarted': format_date(datetime.now()),
            'serverExecutionStarted': format_date(datetime.now()),
            'serverExecutionFinished': format_date(datetime.now()),
            'tradeExecuted': format_date(datetime.now())
        }
        account_id = None
        actual_timestamps = None
        listener = MagicMock()

        async def on_trade(aid, ts):
            nonlocal account_id
            account_id = aid
            nonlocal actual_timestamps
            actual_timestamps = ts

        listener.on_trade = on_trade
        client.add_latency_listener(listener)

        @sio.on('request')
        async def on_request(sid, data):
            assert data['trade'] == trade
            if data['type'] == 'trade' and data['accountId'] == 'accountId' and data['application'] == 'application':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'response': response,
                                            'timestamps': timestamps})

        await client.trade('accountId', trade)
        assert account_id == 'accountId'
        assert actual_timestamps['clientExecutionStarted'] == \
               date(timestamps['clientExecutionStarted'])
        assert actual_timestamps['serverExecutionStarted'] == \
               date(timestamps['serverExecutionStarted'])
        assert actual_timestamps['serverExecutionFinished'] == \
               date(timestamps['serverExecutionFinished'])
        assert actual_timestamps['tradeExecuted'] == \
               date(timestamps['tradeExecuted'])
        assert 'clientProcessingFinished' in actual_timestamps


@pytest.mark.asyncio
async def test_reconnect():
    """Should reconnect to server on disconnect."""
    with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 15)):
        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD',
            'volume': 0.07
        }
        response = {
            'numericCode': 10009,
            'stringCode': 'TRADE_RETCODE_DONE',
            'message': 'Request completed',
            'orderId': '46870472'
        }
        listener = MagicMock()
        listener.on_reconnected = AsyncMock()
        client.add_reconnect_listener(listener, 'accountId')
        client._packetOrderer.on_reconnected = MagicMock()
        client._subscriptionManager.on_reconnected = MagicMock()
        request_counter = 0

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'trade':
                nonlocal request_counter
                request_counter += 1
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'response': response})
            await sio.disconnect(sid)

        await client.trade('accountId', trade)
        await sleep(0.1)
        listener.on_reconnected.assert_called_once()
        client._subscriptionManager.on_reconnected.assert_called_with(0, 0, ['accountId'])
        client._packetOrderer.on_reconnected.assert_called_with(['accountId'])
        await client.trade('accountId', trade)
        assert request_counter == 2
        await client.close()


@pytest.mark.asyncio
async def test_cancel_sync_on_disconnect():
    """Should cancel synchronization on disconnect."""
    with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 15)):
        await client.connect(0, 'vint-hill')
        client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler']._accountsBySynchronizationIds = {
            'synchronizationId': {}
        }
        client._socketInstances['vint-hill'][0][1]['synchronizationThrottler']._accountsBySynchronizationIds = \
            {'ABC2': {}}
        client._socketInstances['new-york'][0][0]['synchronizationThrottler']._accountsBySynchronizationIds = \
            {'ABC3': {}}
        client._socketInstances['vint-hill'][1][0]['synchronizationThrottler']._accountsBySynchronizationIds = \
            {'ABC4': {}}
        client._socketInstancesByAccounts[0]['accountId2'] = 1
        client._socketInstancesByAccounts[0]['accountId3'] = 0
        client._socketInstancesByAccounts[1]['accountId4'] = 0
        client.add_account_region('accountId2', 'vint-hill')
        client.add_account_region('accountId3', 'new-york')
        client.add_account_region('accountId4', 'vint-hill')
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'sequenceTimestamp': 1603124267178, 'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'synchronizationId'}, connections[2])
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId2',
                                           'sequenceTimestamp': 1603124267178, 'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'ABC2'}, connections[3])
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId3',
                                           'sequenceTimestamp': 1603124267178, 'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'ABC3'}, connections[0])
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId4',
                                           'sequenceTimestamp': 1603124267178, 'instanceIndex': 1, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'ABC4'}, connections[1])
        await sleep(0.1)
        assert 'synchronizationId' in client._synchronizationFlags
        assert 'ABC2' in client._synchronizationFlags
        assert 'ABC3' in client._synchronizationFlags
        assert 'ABC4' in client._synchronizationFlags
        await sio.disconnect(connections[2])
        await sleep(0.1)
        assert 'synchronizationId' not in client._synchronizationFlags
        assert 'ABC2' in client._synchronizationFlags
        assert 'ABC3' in client._synchronizationFlags
        assert 'ABC4' in client._synchronizationFlags


@pytest.mark.asyncio
async def test_remove_reconnect_listener():
    """Should remove reconnect listener"""
    with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 15)):
        trade = {
            'actionType': 'ORDER_TYPE_SELL',
            'symbol': 'AUDNZD',
            'volume': 0.07
        }
        response = {
            'numericCode': 10009,
            'stringCode': 'TRADE_RETCODE_DONE',
            'message': 'Request completed',
            'orderId': '46870472'
        }
        listener = MagicMock()
        listener.on_reconnected = AsyncMock()
        client.add_reconnect_listener(listener, 'accountId')
        client._subscriptionManager.on_reconnected = MagicMock()
        request_counter = 0

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'trade':
                nonlocal request_counter
                request_counter += 1
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'response': response})
            await sio.disconnect(sid)

        await client.trade('accountId', trade)
        await sleep(0.1)
        listener.on_reconnected.assert_called_once()
        client.remove_reconnect_listener(listener)
        await client.trade('accountId', trade)
        await sleep(0.1)
        listener.on_reconnected.assert_called_once()
        assert request_counter == 2


@pytest.mark.asyncio
async def test_process_packet_in_order():
    with patch('lib.clients.metaApi.metaApiWebsocket_client.asyncio.sleep', new=lambda x: sleep(x / 60)):
        orders_call_time = 0
        positions_call_time = 0
        disconnected_call_time = 0
        prices_call_time = 0

        async def on_disconnected(instance_index: str):
            await sleep(0.15)
            nonlocal disconnected_call_time
            disconnected_call_time = datetime.now().timestamp()

        async def on_pending_orders_replaced(instance_index: str, orders):
            await sleep(0.25)
            nonlocal orders_call_time
            orders_call_time = datetime.now().timestamp()

        async def on_positions_replaced(instance_index: str, positions):
            await sleep(0.05)
            nonlocal positions_call_time
            positions_call_time = datetime.now().timestamp()

        async def on_symbol_prices_updated(instance_index: str, prices, equity: float = None, margin: float = None,
                                           free_margin: float = None, margin_level: float = None,
                                           account_currency_exchange_rate: float = None):
            await sleep(0.05)
            nonlocal prices_call_time
            prices_call_time = datetime.now().timestamp()

        listener = MagicMock()
        listener.on_connected = AsyncMock()
        listener.on_disconnected = on_disconnected
        listener.on_pending_orders_replaced = on_pending_orders_replaced
        listener.on_pending_orders_synchronized = AsyncMock()
        listener.on_positions_replaced = on_positions_replaced
        listener.on_positions_synchronized = AsyncMock()
        listener.on_symbol_prices_updated = on_symbol_prices_updated
        listener.on_synchronization_started = AsyncMock()
        listener.on_stream_closed = AsyncMock()
        client.add_synchronization_listener('accountId', listener)
        client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)

        @sio.on('request')
        async def on_request(sid, data):
            if data['type'] == 'getPositions' and data['accountId'] == 'accountId' \
                    and data['application'] == 'RPC':
                await sio.emit('response', {'type': 'response', 'accountId': data['accountId'],
                                            'requestId': data['requestId'], 'positions': []})
            else:
                raise Exception('Wrong request')

        await client.get_positions('accountId')
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = \
            ['synchronizationId']
        await sio.emit('synchronization', {'type': 'authenticated', 'accountId': 'accountId', 'host': 'ps-mpa-1',
                                           'instanceIndex': 0, 'replicas': 2, 'sequenceNumber': 1})
        await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                           'sequenceTimestamp': 1603124267178,
                                           'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'synchronizationId'})
        await sleep(0.95)

        await sio.emit('synchronization', {'type': 'orders', 'accountId': 'accountId', 'orders': [],
                                           'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'synchronizationId', 'sequenceNumber': 2})
        await sio.emit('synchronization', {'type': 'prices', 'accountId': 'accountId',
                                           'prices': [{'symbol': 'EURUSD'}], 'instanceIndex': 0,
                                           'host': 'ps-mpa-1', 'synchronizationId': 'synchronizationId'})
        await sleep(0.1)
        await sio.emit('synchronization', {'type': 'positions', 'accountId': 'accountId', 'positions': [],
                                           'instanceIndex': 0, 'host': 'ps-mpa-1',
                                           'synchronizationId': 'synchronizationId', 'sequenceNumber': 3})
        await sleep(0.5)
        assert prices_call_time != 0
        assert prices_call_time < orders_call_time < disconnected_call_time < positions_call_time


@pytest.mark.asyncio
async def test_not_process_old_sync_packet_without_gaps_in_sn():
    """Should not process old synchronization packet without gaps in sequence numbers."""
    listener = MagicMock()
    listener.on_synchronization_started = AsyncMock()
    listener.on_pending_orders_replaced = AsyncMock()
    listener.on_pending_orders_synchronized = AsyncMock()

    client.add_synchronization_listener('accountId', listener)
    client._subscriptionManager.is_subscription_active = MagicMock(return_value=True)
    client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = MagicMock()
    client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = ['ABC']

    await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                       'sequenceNumber': 1, 'sequenceTimestamp': 1603124267178,
                                       'instanceIndex': 0, 'host': 'ps-mpa-1', 'synchronizationId': 'ABC'})
    await sio.emit('synchronization', {'type': 'orders', 'accountId': 'accountId', 'orders': [],
                                       'sequenceNumber': 2, 'sequenceTimestamp': 1603124267181,
                                       'instanceIndex': 0, 'host': 'ps-mpa-1', 'synchronizationId': 'ABC'})
    await asyncio.sleep(0.05)
    assert listener.on_synchronization_started.call_count == 1
    assert listener.on_pending_orders_replaced.call_count == 1

    client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'].active_synchronization_ids = ['DEF']
    await sio.emit('synchronization', {'type': 'synchronizationStarted', 'accountId': 'accountId',
                                       'sequenceNumber': 3, 'sequenceTimestamp': 1603124267190,
                                       'instanceIndex': 0, 'host': 'ps-mpa-1', 'synchronizationId': 'DEF'})
    await sio.emit('synchronization', {'type': 'orders', 'accountId': 'accountId', 'orders': [],
                                       'sequenceNumber': 4, 'sequenceTimestamp': 1603124267192,
                                       'instanceIndex': 0, 'host': 'ps-mpa-1', 'synchronizationId': 'ABC'})
    await sio.emit('synchronization', {'type': 'orders', 'accountId': 'accountId', 'orders': [],
                                       'sequenceNumber': 5, 'sequenceTimestamp': 1603124267195,
                                       'instanceIndex': 0, 'host': 'ps-mpa-1', 'synchronizationId': 'DEF'})
    await asyncio.sleep(0.05)
    assert listener.on_synchronization_started.call_count == 2
    assert listener.on_pending_orders_replaced.call_count == 2


@pytest.mark.asyncio
async def test_process_queued_events_sequentially():
    """Should process queued events sequentially."""
    async def event_1():
        await asyncio.sleep(0.1)
    event1 = AsyncMock(side_effect=event_1)

    async def event_2():
        await asyncio.sleep(0.03)
    event2 = AsyncMock(side_effect=event_2)

    client.queue_event('accountId', 'test', event1)
    client.queue_event('accountId', 'test', event2)

    await asyncio.sleep(0.08)
    assert event1.call_count == 1
    assert event2.call_count == 0

    await asyncio.sleep(0.05)
    assert event2.call_count == 1


@pytest.mark.asyncio
async def test_process_queued_events_among_synchronization_packets():
    """Should process queued events among synchronization packets."""
    listener = MagicMock()

    async def listener_event(arg1, specifications_updated=True, positions_updated=True, orders_updated=True,
                             synchronization_id=''):
        await asyncio.sleep(0.1)

    listener.on_synchronization_started = AsyncMock(side_effect=listener_event)

    async def event_():
        await asyncio.sleep(0.025)
    event = AsyncMock(side_effect=event_)

    client.add_synchronization_listener('accountId', listener)
    client.queue_packet({
        'type': 'synchronizationStarted', 'accountId': 'accountId', 'instanceIndex': 0, 'sequenceNumber': 1,
        'sequenceTimestamp': 1, 'synchronizationId': 'synchronizationId', 'host': 'ps-mpa-1'
    })

    client.queue_event('accountId', 'test', event)
    await asyncio.sleep(0.075)
    assert listener.on_synchronization_started.call_count == 1
    assert event.call_count == 0

    await asyncio.sleep(0.05)
    assert event.call_count == 1


@pytest.mark.asyncio
async def test_not_throw_errors_from_queued_events():
    """Should not throw errors from queued events."""
    event = AsyncMock(side_effect=Exception('test'))
    client.queue_event('accountId', 'test', event)
    await asyncio.sleep(0.05)
    assert event.call_count == 1
