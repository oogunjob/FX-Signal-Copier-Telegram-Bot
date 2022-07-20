from ...models import date
from .stopout_listener_manager import StopoutListenerManager
from .stopout_listener import StopoutListener
from ..domain_client import DomainClient
from mock import MagicMock, patch, AsyncMock
from asyncio import sleep
import pytest

token = 'header.payload.sign'
expected = [
    {
        'subscriberId': 'accountId',
        'reason': 'monthly-balance',
        'stoppedAt': date('2020-08-08T07:57:30.328Z'),
        'strategy': {
            'id': 'ABCD',
            'name': 'Strategy'
        },
        'reasonDescription': 'total strategy equity drawdown exceeded limit',
        'sequenceNumber': 2
    },
    {
        'subscriberId': 'accountId',
        'reason': 'monthly-balance',
        'stoppedAt': date('2020-08-08T07:57:31.328Z'),
        'strategy': {
            'id': 'ABCD',
            'name': 'Strategy'
        },
        'reasonDescription': 'total strategy equity drawdown exceeded limit',
        'sequenceNumber': 3
    }]

expected2 = [
    {
        'subscriberId': 'accountId',
        'reason': 'monthly-balance',
        'stoppedAt': date('2020-08-08T07:57:32.328Z'),
        'strategy': {
            'id': 'ABCD',
            'name': 'Strategy'
        },
        'reasonDescription': 'total strategy equity drawdown exceeded limit',
        'sequenceNumber': 4
    },
    {
        'subscriberId': 'accountId',
        'reason': 'monthly-balance',
        'stoppedAt': date('2020-08-08T07:57:33.328Z'),
        'strategy': {
            'id': 'ABCD',
            'name': 'Strategy'
        },
        'reasonDescription': 'total strategy equity drawdown exceeded limit',
        'sequenceNumber': 5
    }]
domain_client = DomainClient(MagicMock(), token)
stopout_listener_manager = StopoutListenerManager(domain_client)
call_stub = MagicMock()
listener = StopoutListener()


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    domain_client = DomainClient(MagicMock(), token)
    global stopout_listener_manager
    stopout_listener_manager = StopoutListenerManager(domain_client)
    global call_stub
    call_stub = MagicMock()

    class Listener(StopoutListener):
        async def on_stopout(self, strategy_stopout_event):
            call_stub(strategy_stopout_event)

    global listener
    listener = Listener()

    async def get_stopout_func(arg, arg2):
        if arg == {
            'url': '/users/current/stopouts/stream',
            'method': 'GET',
            'qs': {
                'previousSequenceNumber': 1,
                'subscriberId': 'accountId',
                'strategyId': 'ABCD',
                'limit': 1000
            },
            'headers': {
                'auth-token': token
            },
        }:
            await sleep(0.1)
            return expected
        elif arg == {
            'url': '/users/current/stopouts/stream',
            'method': 'GET',
            'qs': {
                'previousSequenceNumber': 3,
                'subscriberId': 'accountId',
                'strategyId': 'ABCD',
                'limit': 1000
            },
            'headers': {
                'auth-token': token
            },
        }:
            await sleep(0.1)
            return expected2
        else:
            await sleep(0.1)
            return []

    get_stopout_mock = AsyncMock(side_effect=get_stopout_func)
    domain_client.request_copyfactory = get_stopout_mock


class TestTradingClient:
    @pytest.mark.asyncio
    async def test_add_stopout_listener(self):
        """Should add stopout listener."""
        with patch('lib.clients.copyFactory.stopout_listener_manager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            id = stopout_listener_manager.add_stopout_listener(listener, 'accountId', 'ABCD', 1)
            await sleep(0.22)
            call_stub.assert_any_call(expected)
            call_stub.assert_any_call(expected2)
            stopout_listener_manager.remove_stopout_listener(id)

    @pytest.mark.asyncio
    async def test_remove_stopout_listener(self):
        """Should remove stopout listener."""
        with patch('lib.clients.copyFactory.stopout_listener_manager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            id = stopout_listener_manager.add_stopout_listener(listener, 'accountId', 'ABCD', 1)
            await sleep(0.08)
            stopout_listener_manager.remove_stopout_listener(id)
            await sleep(0.22)
            call_stub.assert_any_call(expected)
            assert call_stub.call_count == 1

    @pytest.mark.asyncio
    async def test_wait_if_error_returned(self):
        """Should wait if error returned."""
        call_count = 0

        async def get_stopout_func(arg, arg2):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception('test')

            if arg == {
                'url': '/users/current/stopouts/stream',
                'method': 'GET',
                'qs': {
                    'previousSequenceNumber': 1,
                    'subscriberId': 'accountId',
                    'strategyId': 'ABCD',
                    'limit': 1000
                },
                'headers': {
                    'auth-token': token
                },
            }:
                await sleep(0.05)
                return expected
            else:
                await sleep(0.5)
                return []

        get_stopout_mock = AsyncMock(side_effect=get_stopout_func)
        domain_client.request_copyfactory = get_stopout_mock
        with patch('lib.clients.copyFactory.stopout_listener_manager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            id = stopout_listener_manager.add_stopout_listener(listener, 'accountId', 'ABCD', 1)
            await sleep(0.06)
            assert domain_client.request_copyfactory.call_count == 1
            assert call_stub.call_count == 0
            await sleep(0.06)
            assert domain_client.request_copyfactory.call_count == 2
            assert call_stub.call_count == 0
            await sleep(0.2)
            assert domain_client.request_copyfactory.call_count == 3
            assert call_stub.call_count == 0
            await sleep(0.08)
            assert call_stub.call_count == 1
            stopout_listener_manager.remove_stopout_listener(id)
