from mock import AsyncMock, patch, MagicMock
import pytest
from asyncio import sleep
import asyncio
from freezegun import freeze_time
from datetime import datetime
from .metaApiWebsocket_client import MetaApiWebsocketClient
from .synchronizationThrottler import SynchronizationThrottler


class MockClient(MetaApiWebsocketClient):
    def __init__(self, token):
        super().__init__(MagicMock(), token)
        self._subscribed_account_ids = ['accountId1'] * 11

    async def rpc_request(self, account_id: str, request: dict, timeout_in_seconds: float = None):
        await sleep(0.1)
        pass

    def subscribed_account_ids(self, instance_number: int = None, socket_instance_index: int = None,
                               region: str = None):
        return self._subscribed_account_ids


start_time = '2020-10-05 10:00:00.000'
throttler: SynchronizationThrottler = None
client = None


async def get_hashes():
    return {
        'positionsMd5': '1111',
        'ordersMd5': '2222',
        'specificationsMd5': '3333'
    }


@pytest.fixture(autouse=True)
async def run_around_tests():
    with patch('lib.clients.metaApi.synchronizationThrottler.asyncio.sleep', new=lambda x: sleep(x / 20)):
        global client
        client = MockClient('token')
        client.rpc_request = AsyncMock()
        client._socketInstances = {'vint-hill': {0: [{'synchronizationThrottler': {'synchronizingAccounts': []}}]}}
        global throttler
        throttler = SynchronizationThrottler(client, 0, 0, 'vint-hill')
        client._socketInstances['vint-hill'][0][0]['synchronizationThrottler'] = throttler
        throttler.start()
        yield
        throttler.stop()


class TestSynchronizationThrottler:
    @pytest.mark.asyncio
    async def test_sync_without_queue(self):
        """Should immediately send request if free slots exist."""
        with freeze_time() as frozen_datetime:
            frozen_datetime.move_to('2020-10-10 01:00:01.000')
            await throttler.schedule_synchronize('accountId', {'requestId': 'test'}, get_hashes)
            assert throttler._synchronizationIds == {'test': 1602291601.0}
            throttler.remove_synchronization_id('test')
            client.rpc_request.assert_called_with('accountId', {
                'requestId': 'test',
                'positionsMd5': '1111',
                'ordersMd5': '2222',
                'specificationsMd5': '3333'
            })
            assert throttler._synchronizationIds == {}

    @pytest.mark.asyncio
    async def test_not_remove_if_different_instance_index(self):
        """Should not remove sync if different instance index."""
        with freeze_time() as frozen_datetime:
            frozen_datetime.move_to('2020-10-10 01:00:01.000')
            await throttler.schedule_synchronize('accountId', {'requestId': 'test', 'instanceIndex': 0}, get_hashes)
            await throttler.schedule_synchronize('accountId', {'requestId': 'test1', 'instanceIndex': 1}, get_hashes)
            assert throttler._synchronizationIds == {'test': 1602291601.0, 'test1': 1602291601.0}
            throttler.remove_synchronization_id('test')
            assert throttler._synchronizationIds == {'test1': 1602291601.0}
            client.rpc_request.assert_any_call('accountId', {'requestId': 'test',
                                                             'positionsMd5': '1111',
                                                             'ordersMd5': '2222',
                                                             'specificationsMd5': '3333',
                                                             'instanceIndex': 0})
            client.rpc_request.assert_any_call('accountId', {'requestId': 'test1',
                                                             'positionsMd5': '1111',
                                                             'ordersMd5': '2222',
                                                             'specificationsMd5': '3333',
                                                             'instanceIndex': 1})

    @pytest.mark.asyncio
    async def test_sync_with_queue(self):
        """Should wait for other sync requests to finish if slots are full."""
        await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
        await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
        client.rpc_request.assert_any_call('accountId1', {'requestId': 'test1',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})
        client.rpc_request.assert_any_call('accountId2', {'requestId': 'test2',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})
        asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
        await sleep(0.1)
        assert client.rpc_request.call_count == 2
        throttler.remove_synchronization_id('test1')
        await sleep(0.1)
        assert client.rpc_request.call_count == 3

    @pytest.mark.asyncio
    async def test_increase_slots_with_more_accounts(self):
        """Should increase slot amount with more subscribed accounts."""
        client._subscribed_account_ids = ['accountId1'] * 21
        await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
        await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
        await throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes)
        client.rpc_request.assert_any_call('accountId1', {'requestId': 'test1',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})
        client.rpc_request.assert_any_call('accountId2', {'requestId': 'test2',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})
        client.rpc_request.assert_any_call('accountId3', {'requestId': 'test3',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})
        assert client.rpc_request.call_count == 3

    @pytest.mark.asyncio
    async def test_limit_slots_in_options(self):
        """Should set hard limit for concurrent synchronizations across throttlers via options."""
        client._subscribed_account_ids = ['accountId1'] * 21
        throttler = SynchronizationThrottler(client, 0, 0, 'vint-hill', {'maxConcurrentSynchronizations': 3})
        client._socketInstances = {'vint-hill': {0: [
            {'synchronizationThrottler': throttler},
            {'synchronizationThrottler': MagicMock()}]}}
        client._socketInstances['vint-hill'][0][1]['synchronizationThrottler'].synchronizing_accounts = ['accountId4']
        await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
        await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
        asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test4'}, get_hashes))
        await sleep(0.1)
        assert client.rpc_request.call_count == 2
        throttler.remove_synchronization_id('test1')
        await sleep(0.1)
        assert client.rpc_request.call_count == 3

    @pytest.mark.asyncio
    async def test_not_take_slots_if_same_account(self):
        """Should not take extra slots if sync ids belong to the same account."""
        asyncio.create_task(throttler.schedule_synchronize('accountId', {'requestId': 'test', 'instanceIndex': 0},
                                                           get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId', {'requestId': 'test1', 'instanceIndex': 1},
                                                           get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
        await sleep(0.2)
        assert client.rpc_request.call_count == 3
        client.rpc_request.assert_any_call('accountId', {'requestId': 'test',
                                                         'positionsMd5': '1111',
                                                         'ordersMd5': '2222',
                                                         'specificationsMd5': '3333',
                                                         'instanceIndex': 0})
        client.rpc_request.assert_any_call('accountId', {'requestId': 'test1',
                                                         'positionsMd5': '1111',
                                                         'ordersMd5': '2222',
                                                         'specificationsMd5': '3333',
                                                         'instanceIndex': 1})
        client.rpc_request.assert_any_call('accountId2', {'requestId': 'test2',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})

    @pytest.mark.asyncio
    async def test_clear_expired_slots(self):
        """Should clear expired synchronization slots if no packets for 10 seconds."""
        with freeze_time(start_time) as frozen_datetime:
            await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
            await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
            await sleep(0.2)
            assert client.rpc_request.call_count == 2
            frozen_datetime.tick(20)
            await sleep(0.2)
            assert client.rpc_request.call_count == 3

    @pytest.mark.asyncio
    async def test_renew_sync(self):
        """Should renew sync on update."""
        with freeze_time(start_time) as frozen_datetime:
            await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
            await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
            await sleep(0.2)
            assert client.rpc_request.call_count == 2
            frozen_datetime.tick(11)
            await sleep(0.2)
            assert client.rpc_request.call_count == 3
            frozen_datetime.tick(11)
            throttler.update_synchronization_id('test1')
            asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test4'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId5', {'requestId': 'test5'}, get_hashes))
            await sleep(0.2)
            assert client.rpc_request.call_count == 4

    @pytest.mark.asyncio
    async def test_replace_previous_syncs(self):
        """Should replace previous syncs."""
        asyncio.create_task(throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId1', {'requestId': 'test2'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId1', {'requestId': 'test3'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test4'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test5'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId1', {'requestId': 'test6', 'instanceIndex': 0},
                                                           get_hashes))
        await sleep(0.2)
        assert client.rpc_request.call_count == 4

    @pytest.mark.asyncio
    async def test_clear_on_disconnect(self):
        """Should clear existing sync ids on disconnect."""
        await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
        await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
        await sleep(0.2)
        assert client.rpc_request.call_count == 2
        throttler.on_disconnect()
        await throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes)
        await sleep(0.2)
        assert client.rpc_request.call_count == 3

    @pytest.mark.asyncio
    async def test_remove_from_queue(self):
        """Should remove synchronizations from queue."""
        with freeze_time(start_time) as frozen_datetime:
            await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
            await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test4',
                                                                              'instanceIndex': 0}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test5'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test6'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test7'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test8'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId5', {'requestId': 'test9'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test10',
                                                                              'instanceIndex': 0}, get_hashes))
            await sleep(0.2)
            frozen_datetime.tick(21)
            await sleep(0.2)
            frozen_datetime.tick(21)
            await sleep(0.2)
            frozen_datetime.tick(21)
            await sleep(0.2)
            frozen_datetime.tick(21)
            await sleep(0.2)
            assert client.rpc_request.call_count == 6
            client.rpc_request.assert_any_call('accountId1', {'requestId': 'test1',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId2', {'requestId': 'test2',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId3', {'requestId': 'test8',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId3', {'requestId': 'test10', 'instanceIndex': 0,
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId4', {'requestId': 'test7',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId5', {'requestId': 'test9',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})

    @pytest.mark.asyncio
    async def test_remove_expired_from_queue(self):
        """Should remove expired synchronizations from queue."""
        with freeze_time(start_time) as frozen_datetime:
            await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
            await throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes)
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test4'}, get_hashes))
            await sleep(0.1)
            frozen_datetime.tick(160)
            asyncio.create_task(throttler.schedule_synchronize('accountId5', {'requestId': 'test5'}, get_hashes))
            frozen_datetime.tick(160)
            throttler.update_synchronization_id('test1')
            throttler.update_synchronization_id('test2')
            await sleep(0.1)
            frozen_datetime.tick(21)
            await sleep(0.1)
            frozen_datetime.tick(21)
            await sleep(0.1)
            assert client.rpc_request.call_count == 3
            client.rpc_request.assert_any_call('accountId1', {'requestId': 'test1',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId2', {'requestId': 'test2',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})
            client.rpc_request.assert_any_call('accountId5', {'requestId': 'test5',
                                                              'positionsMd5': '1111',
                                                              'ordersMd5': '2222',
                                                              'specificationsMd5': '3333'})

    @pytest.mark.asyncio
    async def test_should_not_get_stuck_due_to_app_limit(self):
        """Should not get queue stuck due to app synchronizations limit."""
        with patch('lib.clients.metaApi.synchronizationThrottler.asyncio.sleep', new=lambda x: sleep(x / 50)):
            throttler._client._socketInstances = {'vint-hill': {0: [{'synchronizationThrottler': MagicMock()},
                                                  {'synchronizationThrottler': throttler}]}}
            throttler._client.socket_instances['vint-hill'][0][0]['synchronizationThrottler'].synchronizing_accounts =\
                ['accountId21', 'accountId22', 'accountId23', 'accountId24', 'accountId25', 'accountId26',
                 'accountId27', 'accountId28', 'accountId29', 'accountId210', 'accountId211', 'accountId212',
                 'accountId213', 'accountId214', 'accountId215']
            asyncio.create_task(throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
            await sleep(0.11)
            client.rpc_request.assert_not_called()
            throttler._client.socket_instances['vint-hill'][0][0]['synchronizationThrottler'].synchronizing_accounts =\
                throttler._client.socket_instances['vint-hill'][0][0][
                    'synchronizationThrottler'].synchronizing_accounts[1:]
            await sleep(0.11)
            assert client.rpc_request.call_count == 1
            throttler._client.socket_instances['vint-hill'][0][0]['synchronizationThrottler'].synchronizing_accounts = \
                throttler._client.socket_instances['vint-hill'][0][0][
                    'synchronizationThrottler'].synchronizing_accounts[1:]
            await sleep(0.11)
            assert client.rpc_request.call_count == 2

    @pytest.mark.asyncio
    async def test_should_not_skip_queue_items(self):
        """Should not skip queue items when synchronization id is removed."""
        with patch('lib.clients.metaApi.synchronizationThrottler.asyncio.sleep', new=lambda x: sleep(x / 20)):
            asyncio.create_task(throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test2'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test4'}, get_hashes))
            asyncio.create_task(throttler.schedule_synchronize('accountId5', {'requestId': 'test5'}, get_hashes))
            await sleep(0.1)
            throttler.remove_synchronization_id('test3')
            await sleep(0.1)
            throttler.remove_synchronization_id('test1')
            throttler.remove_synchronization_id('test2')
            await sleep(0.1)
            assert client.rpc_request.call_count == 4

    @pytest.mark.asyncio
    async def test_should_remove_id_by_parameters(self):
        """Should remove id by parameters."""
        await throttler.schedule_synchronize('accountId1', {'requestId': 'test1'}, get_hashes)
        await throttler.schedule_synchronize('accountId2', {'requestId': 'test2', 'instanceIndex': 0,
                                                            'host': 'ps-mpa-0'}, get_hashes)
        asyncio.create_task(throttler.schedule_synchronize('accountId3', {'requestId': 'test3'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test4', 'instanceIndex': 1,
                                                           'host': 'ps-mpa-1'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test5', 'instanceIndex': 0,
                                                           'host': 'ps-mpa-2'}, get_hashes))
        asyncio.create_task(throttler.schedule_synchronize('accountId4', {'requestId': 'test6'}, get_hashes))
        await sleep(0.05)
        asyncio.create_task(throttler.schedule_synchronize('accountId2', {'requestId': 'test7', 'instanceIndex': 0,
                                                           'host': 'ps-mpa-3'}, get_hashes))
        await sleep(0.05)
        throttler.remove_id_by_parameters('accountId2', 0, 'ps-mpa-0')
        throttler.remove_id_by_parameters('accountId2', 0, 'ps-mpa-3')
        throttler.remove_id_by_parameters('accountId2', 1, 'ps-mpa-1')
        throttler.remove_synchronization_id('test1')
        await sleep(0.1)
        client.rpc_request.assert_any_call('accountId3', {'requestId': 'test3',
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333'})
        client.rpc_request.assert_any_call('accountId2', {'requestId': 'test5', 'instanceIndex': 0,
                                                          'positionsMd5': '1111',
                                                          'ordersMd5': '2222',
                                                          'specificationsMd5': '3333',
                                                          'host': 'ps-mpa-2'})
        assert client.rpc_request.call_count == 4
