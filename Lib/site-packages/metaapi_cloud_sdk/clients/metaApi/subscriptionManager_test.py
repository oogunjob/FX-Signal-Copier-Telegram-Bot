from .subscriptionManager import SubscriptionManager
from .metaApiWebsocket_client import MetaApiWebsocketClient
from ..timeoutException import TimeoutException
from ..errorHandler import TooManyRequestsException
from mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from ...metaApi.models import format_date
import pytest
import asyncio
from asyncio import sleep


class MockClient(MetaApiWebsocketClient):
    def subscribe(self, account_id: str, instance_index: str = None):
        pass


client: MockClient = None
manager: SubscriptionManager = None


@pytest.fixture(autouse=True)
async def run_around_tests():
    with patch('lib.clients.metaApi.subscriptionManager.uniform', new=MagicMock(return_value=1)):
        global client
        client = MockClient(MagicMock(), 'token')
        client._socketInstances = {'vint-hill': {0: [{'socket': MagicMock()}, {'socket': MagicMock()}]}}
        client._socketInstances['vint-hill'][0][0]['socket'].connected = True
        client._socketInstances['vint-hill'][0][1]['socket'].connected = False
        client._socketInstancesByAccounts = {0: {'accountId': 0}}
        client.rpc_request = AsyncMock()
        global manager
        manager = SubscriptionManager(client)
        yield


class TestSubscriptionManager:

    @pytest.mark.asyncio
    async def test_subscribe_to_terminal(self):
        """Should subscribe to terminal."""
        client.subscribe = AsyncMock()

        async def delay_connect():
            await sleep(0.1)
            await manager.cancel_subscribe('accountId:0')

        asyncio.create_task(delay_connect())
        await manager.schedule_subscribe('accountId', 0)
        client.rpc_request.assert_called_with('accountId', {'type': 'subscribe', 'instanceIndex': 0})

    @pytest.mark.asyncio
    async def test_retry_subscribe(self):
        """Should retry subscribe if no response received."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            response = {'type': 'response', 'accountId': 'accountId', 'requestId': 'requestId'}
            client.rpc_request = AsyncMock(side_effect=[TimeoutException('timeout'), response, response])

            async def delay_connect():
                await sleep(0.36)
                await manager.cancel_subscribe('accountId:0')

            asyncio.create_task(delay_connect())
            await manager.schedule_subscribe('accountId', 0)
            client.rpc_request.assert_called_with('accountId', {'type': 'subscribe', 'instanceIndex': 0})
            assert client.rpc_request.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_on_too_many_requests_error(self):
        """Should wait for recommended time if too many requests error received."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            response = {'type': 'response', 'accountId': 'accountId', 'requestId': 'requestId'}
            client.rpc_request = AsyncMock(side_effect=[TooManyRequestsException('timeout', {
                'periodInMinutes': 60, 'maxRequestsForPeriod': 10000,
                "type": "LIMIT_REQUEST_RATE_PER_USER",
                'recommendedRetryTime': format_date(datetime.now() + timedelta(seconds=5))}), response, response])

            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            await sleep(0.36)
            assert client.rpc_request.call_count == 1
            await sleep(0.2)
            manager.cancel_subscribe('accountId:0')
            client.rpc_request.assert_called_with('accountId', {'type': 'subscribe', 'instanceIndex': 0})
            assert client.rpc_request.call_count == 2

    @pytest.mark.asyncio
    async def test_cancel_on_reconnect(self):
        """Should cancel all subscriptions on reconnect."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            client.connect = AsyncMock()
            client.rpc_request = AsyncMock()
            client._socketInstancesByAccounts[0] = {'accountId': 0, 'accountId2': 0, 'accountId3': 1}
            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            asyncio.create_task(manager.schedule_subscribe('accountId2', 0))
            asyncio.create_task(manager.schedule_subscribe('accountId3', 0))
            await sleep(0.1)
            manager.on_reconnected(0, 0, [])
            await sleep(0.5)
            assert client.rpc_request.call_count == 4

    @pytest.mark.asyncio
    async def test_restart_on_reconnect(self):
        """Should restart subscriptions on reconnect."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            client.connect = AsyncMock()
            client.rpc_request = AsyncMock()
            client._socketInstancesByAccounts[0] = {'accountId': 0, 'accountId2': 0, 'accountId3': 0}
            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            asyncio.create_task(manager.schedule_subscribe('accountId2', 0))
            asyncio.create_task(manager.schedule_subscribe('accountId3', 0))
            await sleep(0.1)
            manager.on_reconnected(0, 0, ['accountId', 'accountId2'])
            await sleep(0.2)
            assert client.rpc_request.call_count == 5

    @pytest.mark.asyncio
    async def test_wait_for_stop_on_reconnect(self):
        """Should wait until previous subscription ends on reconnect."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            async def delay_subscribe(account_id: str, instance_number: int = None):
                await sleep(0.2)

            client.connect = AsyncMock()
            client.rpc_request = AsyncMock(side_effect=delay_subscribe)
            client._socketInstancesByAccounts[0] = {'accountId': 0}
            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            await sleep(0.1)
            manager.on_reconnected(0, 0, ['accountId'])
            await sleep(0.3)
            assert client.rpc_request.call_count == 2

    @pytest.mark.asyncio
    async def test_no_multiple_subscribes(self):
        """Should not send multiple subscribe requests at the same time."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            client.rpc_request = AsyncMock()
            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            await sleep(0.1)
            manager.cancel_subscribe('accountId:0')
            await sleep(0.25)
            client.rpc_request.assert_called_with('accountId', {'type': 'subscribe', 'instanceIndex': 0})
            assert client.rpc_request.call_count == 1

    @pytest.mark.asyncio
    async def test_resubscribe_on_timeout(self):
        """Should resubscribe on timeout."""
        client.rpc_request = AsyncMock()
        client._socketInstances['vint-hill'][0][0]['socket'].connected = True
        client._socketInstancesByAccounts[0]['accountId2'] = 1
        client._regionsByAccounts = {
            'accountId': {'region': 'vint-hill'},
            'accountId2': {'region': 'vint-hill'}
        }

        async def delay_connect():
            await sleep(0.1)
            await manager.cancel_subscribe('accountId:0')
            await manager.cancel_subscribe('accountId2:0')

        asyncio.create_task(delay_connect())
        manager.on_timeout('accountId', 0)
        manager.on_timeout('accountId2', 0)
        await sleep(0.2)
        client.rpc_request.assert_called_with('accountId', {'type': 'subscribe', 'instanceIndex': 0})
        assert client.rpc_request.call_count == 1

    @pytest.mark.asyncio
    async def test_not_subscribe_if_disconnected(self):
        """Should not retry subscribe to terminal if connection is closed."""
        client.rpc_request = AsyncMock()
        client._socketInstances['vint-hill'][0][0]['socket'].connected = False

        async def delay_connect():
            await sleep(0.1)
            await manager.cancel_subscribe('accountId:0')

        asyncio.create_task(delay_connect())
        manager.on_timeout('accountId', 0)
        await sleep(0.05)
        client.rpc_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_account(self):
        """Should cancel all subscriptions for an account."""
        with patch('lib.clients.metaApi.subscriptionManager.asyncio.sleep', new=lambda x: sleep(x / 10)):
            client.rpc_request = AsyncMock()
            asyncio.create_task(manager.schedule_subscribe('accountId', 0))
            asyncio.create_task(manager.schedule_subscribe('accountId', 1))
            await sleep(0.1)
            manager.cancel_account('accountId')
            await sleep(0.5)
            assert client.rpc_request.call_count == 2

    @pytest.mark.asyncio
    async def test_should_destroy_subscribe_process_on_cancel(self):
        """Should destroy subscribe process on cancel."""
        subscribe = AsyncMock()

        async def delay_subscribe(account_id, instance_index):
            await subscribe()
            await asyncio.sleep(0.4)
            return

        client.rpc_request = delay_subscribe
        asyncio.create_task(manager.schedule_subscribe('accountId', 0))
        await asyncio.sleep(0.05)
        manager.cancel_subscribe('accountId:0')
        await asyncio.sleep(0.05)
        asyncio.create_task(manager.schedule_subscribe('accountId', 0))
        await asyncio.sleep(0.05)
        assert subscribe.call_count == 2

    @pytest.mark.asyncio
    async def test_is_subscribing(self):
        """Should check if account is subscribing."""
        asyncio.create_task(manager.schedule_subscribe('accountId', 1))
        await asyncio.sleep(0.05)
        assert manager.is_account_subscribing('accountId')
        assert not manager.is_account_subscribing('accountId', 0)
        assert manager.is_account_subscribing('accountId', 1)
