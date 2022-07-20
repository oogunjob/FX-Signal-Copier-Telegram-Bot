from .drawdownListener import DrawdownListener
from .drawdownListenerManager import DrawdownListenerManager
from ..domain_client import DomainClient
from mock import MagicMock, patch, AsyncMock
from asyncio import sleep
import pytest

token = 'header.payload.sign'
expected = [{
    'sequenceNumber': 2,
    'accountId': 'accountId',
    'trackerId': 'trackerId',
    'period': 'day',
    'startBrokerTime': '2022-04-08 00:00:00.000',
    'endBrokerTime': '2022-04-08 23:59:59.999',
    'brokerTime': '2022-04-08 09:36:00.000',
    'absoluteDrawdown': 250,
    'relativeDrawdown': 0.25
}, {
    'sequenceNumber': 3,
    'accountId': 'accountId',
    'trackerId': 'trackerId',
    'period': 'day',
    'startBrokerTime': '2022-04-08 00:00:00.000',
    'endBrokerTime': '2022-04-08 23:59:59.999',
    'brokerTime': '2022-04-08 09:36:00.000',
    'absoluteDrawdown': 250,
    'relativeDrawdown': 0.25
}]

expected2 = [{
    'sequenceNumber': 4,
    'accountId': 'accountId',
    'trackerId': 'trackerId',
    'period': 'day',
    'startBrokerTime': '2022-04-08 00:00:00.000',
    'endBrokerTime': '2022-04-08 23:59:59.999',
    'brokerTime': '2022-04-08 09:36:00.000',
    'absoluteDrawdown': 250,
    'relativeDrawdown': 0.25
}, {
    'sequenceNumber': 5,
    'accountId': 'accountId',
    'trackerId': 'trackerId',
    'period': 'day',
    'startBrokerTime': '2022-04-08 00:00:00.000',
    'endBrokerTime': '2022-04-08 23:59:59.999',
    'brokerTime': '2022-04-08 09:36:00.000',
    'absoluteDrawdown': 250,
    'relativeDrawdown': 0.25
}]
domain_client = DomainClient(MagicMock(), token, 'risk-management-api-v1')
drawdown_listener_manager = DrawdownListenerManager(domain_client)
call_stub = MagicMock()
listener = DrawdownListener()


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    domain_client = DomainClient(MagicMock(), token, 'risk-management-api-v1')
    global drawdown_listener_manager
    drawdown_listener_manager = DrawdownListenerManager(domain_client)
    global call_stub
    call_stub = MagicMock()

    class Listener(DrawdownListener):
        async def on_drawdown(self, drawdown_event):
            call_stub(drawdown_event)

    global listener
    listener = Listener()

    async def get_drawdown_func(arg, arg2):
        if arg == {
            'url': '/users/current/drawdown-events/stream',
            'method': 'GET',
            'qs': {
                'previousSequenceNumber': 1,
                'accountId': 'accountId',
                'trackerId': 'trackerId',
                'limit': 1000
            }
        }:
            await sleep(0.1)
            return expected
        elif arg == {
            'url': '/users/current/drawdown-events/stream',
            'method': 'GET',
            'qs': {
                'previousSequenceNumber': 3,
                'accountId': 'accountId',
                'trackerId': 'trackerId',
                'limit': 1000
            }
        }:
            await sleep(0.1)
            return expected2
        else:
            await sleep(0.1)
            return []

    get_drawdown_mock = AsyncMock(side_effect=get_drawdown_func)
    domain_client.request_api = get_drawdown_mock


class TestTradingClient:

    @pytest.mark.asyncio
    async def test_add_drawdown_listener(self):
        """Should add drawdown listener."""
        with patch('lib.clients.equityTracking.drawdownListenerManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            id = drawdown_listener_manager.add_drawdown_listener(listener, 'accountId', 'trackerId', 1)
            await sleep(0.22)
            assert call_stub.call_args_list[0][0][0] == expected[0]
            assert call_stub.call_args_list[1][0][0] == expected[1]
            assert call_stub.call_args_list[2][0][0] == expected2[0]
            assert call_stub.call_args_list[3][0][0] == expected2[1]
            drawdown_listener_manager.remove_drawdown_listener(id)

    @pytest.mark.asyncio
    async def test_remove_drawdown_listener(self):
        """Should remove drawdown listener."""
        with patch('lib.clients.equityTracking.drawdownListenerManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            id = drawdown_listener_manager.add_drawdown_listener(listener, 'accountId', 'trackerId', 1)
            await sleep(0.08)
            drawdown_listener_manager.remove_drawdown_listener(id)
            await sleep(0.22)
            assert call_stub.call_args_list[0][0][0] == expected[0]
            assert call_stub.call_args_list[1][0][0] == expected[1]
            assert call_stub.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_if_error_returned(self):
        """Should wait if error returned."""
        call_count = 0

        async def get_drawdown_func(arg, arg2):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception('test')

            if arg == {
                'url': '/users/current/drawdown-events/stream',
                'method': 'GET',
                'qs': {
                    'previousSequenceNumber': 1,
                    'accountId': 'accountId',
                    'trackerId': 'ABCD',
                    'limit': 1000
                }
            }:
                await sleep(0.05)
                return expected
            else:
                await sleep(0.5)
                return []

        get_drawdown_mock = AsyncMock(side_effect=get_drawdown_func)
        domain_client.request_api = get_drawdown_mock
        with patch('lib.clients.equityTracking.drawdownListenerManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            id = drawdown_listener_manager.add_drawdown_listener(listener, 'accountId', 'ABCD', 1)
            await sleep(0.06)
            assert domain_client.request_api.call_count == 1
            assert call_stub.call_count == 0
            await sleep(0.06)
            assert domain_client.request_api.call_count == 2
            assert call_stub.call_count == 0
            await sleep(0.2)
            assert domain_client.request_api.call_count == 3
            assert call_stub.call_count == 0
            await sleep(0.08)
            assert call_stub.call_count == 2
            call_stub.assert_any_call(expected[0])
            call_stub.assert_any_call(expected[1])
            drawdown_listener_manager.remove_drawdown_listener(id)
