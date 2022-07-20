from .connectionHealthMonitor import ConnectionHealthMonitor
from mock import MagicMock, patch
from .streamingMetaApiConnection import StreamingMetaApiConnection
from .metatraderAccount import MetatraderAccount
from .terminalState import TerminalState
from freezegun import freeze_time
from typing import List
from datetime import datetime
from asyncio import sleep
import pytest


class MockAccount(MetatraderAccount):

    def __init__(self, id):
        super().__init__(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), 'MetaApi')
        self._id = id

    @property
    def id(self):
        return self._id


class MockTerminalState(TerminalState):

    def __init__(self):
        self._connected = True
        self._connected_to_broker = True

    def specification(self, symbol: str):
        return {'quoteSessions': {'MONDAY': [{'from': '08:00:00.000', 'to': '17:00:00.000'}]}}

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def connected_to_broker(self) -> bool:
        return self._connected_to_broker


class MockConnection(StreamingMetaApiConnection):

    def __init__(self):
        self._terminalState = MockTerminalState()
        self._account = MockAccount('id')
        self._synchronized = True
        self._subscribed_symbols = ['EURUSD']

    @property
    def account(self):
        return self._account

    @property
    def subscribed_symbols(self) -> List[str]:
        return self._subscribed_symbols

    @property
    def terminal_state(self):
        return self._terminalState

    @property
    def synchronized(self) -> bool:
        return self._synchronized


start_time = '2020-10-05 10:00:00.000'
broker_times = ['2020-10-05 09:00:00.000', '2020-10-10 10:00:00.000']
connection: StreamingMetaApiConnection = None
health_monitor: ConnectionHealthMonitor = None
prices = []


@pytest.fixture(autouse=True)
async def run_around_tests():
    with patch('lib.metaApi.connectionHealthMonitor.asyncio.sleep', new=lambda x: sleep(x / 300)):
        with patch('lib.metaApi.connectionHealthMonitor.uniform', new=MagicMock(return_value=30)):
            global connection
            connection = MockConnection()
            global health_monitor
            health_monitor = ConnectionHealthMonitor(connection)
            health_monitor._quotesHealthy = True
            global prices
            prices = [{
              'symbol': 'EURUSD',
              'brokerTime': broker_times[0],
            }, {
              'symbol': 'EURUSD',
              'brokerTime': broker_times[1],
            }]
            yield


class TestConnectionHealthMonitor:
    @pytest.mark.asyncio
    async def test_return_100_uptime(self):
        """Should return 100 uptime."""
        await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[0])
        await sleep(0.2)
        assert health_monitor.uptime == {'5m': 100, '1h': 100, '1d': 100, '1w': 100}

    @pytest.mark.asyncio
    async def test_return_average_uptime(self):
        """Should return average uptime."""
        with freeze_time(start_time) as frozen_datetime:
            await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[0])
            await sleep(0.6)
            frozen_datetime.tick(60)
            await sleep(0.4)
            assert health_monitor.uptime == {'5m': 60, '1h': 60, '1d': 60, '1w': 60}

    @pytest.mark.asyncio
    async def test_check_downtime(self):
        """Should check connection for downtime."""
        await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[0])
        await sleep(0.22)
        assert health_monitor.uptime == {'5m': 100, '1h': 100, '1d': 100, '1w': 100}
        connection.terminal_state._connected = False
        await sleep(0.22)
        assert health_monitor.uptime == {'5m': 50, '1h': 50, '1d': 50, '1w': 50}
        connection.terminal_state._connected = True
        connection.terminal_state._connected_to_broker = False
        await sleep(0.42)
        assert health_monitor.uptime == {'5m': 25, '1h': 25, '1d': 25, '1w': 25}
        connection.terminal_state._connected_to_broker = True
        connection._synchronized = False
        await sleep(0.22)
        assert health_monitor.uptime == {'5m': 20, '1h': 20, '1d': 20, '1w': 20}
        connection._synchronized = True
        await sleep(0.61)
        assert health_monitor.uptime == {'5m': 50, '1h': 50, '1d': 50, '1w': 50}

    @pytest.mark.asyncio
    async def test_return_ok(self):
        """Should return ok status."""
        assert health_monitor.health_status == {
            'connected': True,
            'connectedToBroker': True,
            'healthy': True,
            'message': 'Connection to broker is stable. No health issues detected.',
            'quoteStreamingHealthy': True,
            'synchronized': True
        }

    @pytest.mark.asyncio
    async def test_return_one_error_message(self):
        """Should return error status with one message."""
        connection.terminal_state._connected_to_broker = False
        assert health_monitor.health_status == {
            'connected': True,
            'connectedToBroker': False,
            'healthy': False,
            'message': 'Connection is not healthy because connection to broker is not established or lost.',
            'quoteStreamingHealthy': True,
            'synchronized': True
        }

    @pytest.mark.asyncio
    async def test_return_multiple_error_messages(self):
        """Should return error status with multiple messages."""
        connection.terminal_state._connected = False
        connection.terminal_state._connected_to_broker = False
        connection._synchronized = False
        assert health_monitor.health_status == {
            'connected': False,
            'connectedToBroker': False,
            'healthy': False,
            'message': 'Connection is not healthy because connection to API server is not established or lost and ' +
                       'connection to broker is not established or lost ' +
                       'and local terminal state is not synchronized to broker.',
            'quoteStreamingHealthy': True,
            'synchronized': False
        }

    @pytest.mark.asyncio
    async def test_show_as_healthy(self):
        """Should show as healthy if recently updated and in session."""
        await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[0])
        await sleep(0.2)
        assert health_monitor.health_status['quoteStreamingHealthy']

    @pytest.mark.asyncio
    async def test_show_as_not_healthy(self):
        """Should show as not healthy if old update and in session."""
        with freeze_time(start_time) as frozen_datetime:
            await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[0])
            frozen_datetime.tick(60)
            await sleep(0.2)
            assert not health_monitor.health_status['quoteStreamingHealthy']

    @pytest.mark.asyncio
    async def test_show_as_healthy_if_not_in_session(self):
        """Should show as healthy if not in session."""
        with freeze_time(start_time) as frozen_datetime:
            await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[1])
            frozen_datetime.tick(60)
            await sleep(0.2)
            assert health_monitor.health_status['quoteStreamingHealthy']

    @pytest.mark.asyncio
    async def test_show_as_healthy_if_no_symbols(self):
        """Should show as healthy if no symbols."""
        with freeze_time(start_time) as frozen_datetime:
            connection._subscribed_symbols = []
            await health_monitor.on_symbol_price_updated('1:ps-mpa-1', prices[0])
            frozen_datetime.tick(60)
            await sleep(0.2)
            assert health_monitor.health_status['quoteStreamingHealthy']
