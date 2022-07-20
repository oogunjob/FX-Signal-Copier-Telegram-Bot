from .httpClient import HttpClient
from .domain_client import DomainClient
from mock import AsyncMock, ANY
import pytest
from freezegun import freeze_time
import respx
import json
from httpx import Response
from datetime import datetime
import asyncio

http_client = HttpClient()
domain_client = DomainClient(http_client, 'token')
request_mock = AsyncMock()

token = 'header.payload.sign'
expected = [{'_id': 'ABCD'}]
start_time = '2020-10-05 10:00:00.000'

request_call: respx.Route
regions_call: respx.Route
host_call: respx.Route
signal_vint_call: respx.Route
signal_us_west_call: respx.Route
get_account_call: respx.Route
strategies_url = 'https://copyfactory-api-v1.vint-hill.agiliumtrade.agiliumtrade.ai/users/current/' +\
                 'configuration/strategies'
regions_url = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/regions'
host_url = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/servers/mt-client-api'
opts = {
    'url': '/users/current/configuration/strategies',
    'method': 'GET',
    'headers': {
        'auth-token': token
    }
}
host = {
    'host': 'https://copyfactory-api-v1',
    'lastUpdated': datetime.now().timestamp(),
    'regions': ['vint-hill'],
    'domain': 'agiliumtrade.ai'
}
signal_opts = {
    'url': '/users/current/subscribers/accountId/signals',
    'method': 'GET',
}
expectedSignals = [{
    'strategy': {'id': '1234', 'name': 'Test strategy'},
    'positionId': '123456',
    'time': '2021-11-19T18:56:32.590Z',
    'symbol': 'GBPUSD',
    'type': 'limit',
    'side': 'buy',
}]
expected_account = {'_id': 'accountId2', 'region': 'germany', 'accountReplicas': []}


@pytest.fixture(autouse=True)
async def run_around_tests():
    global http_client
    http_client = HttpClient()
    global domain_client
    domain_client = DomainClient(http_client, token)

    global request_call
    request_call = respx.get(strategies_url).mock(return_value=Response(200, content=json.dumps(expected)))

    global regions_call
    regions_call = respx.get(regions_url)\
        .mock(return_value=Response(200, content=json.dumps(['vint-hill', 'us-west'])))

    global host_call
    host_call = respx.get(host_url)\
        .mock(return_value=Response(200, content=json.dumps({'domain': 'agiliumtrade.agiliumtrade.ai'})))

    global signal_vint_call
    signal_vint_call = respx.get('https://copyfactory-api-v1.vint-hill.agiliumtrade.ai/users/current/subscribers/'
                                 'accountId/signals')\
        .mock(return_value=Response(200, content=json.dumps(expectedSignals)))

    global signal_us_west_call
    signal_us_west_call = respx.get('https://copyfactory-api-v1.us-west.agiliumtrade.ai/users/current/subscribers/'
                                    'accountId/signals')\
        .mock(return_value=Response(500))

    global get_account_call
    get_account_call = respx.get('https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/'
                                 'accounts/accountId')\
        .mock(return_value=Response(200, content=json.dumps(expected_account)))

    global host
    host = {
        'host': 'https://copyfactory-api-v1',
        'lastUpdated': datetime.now().timestamp(),
        'regions': ['vint-hill'],
        'domain': 'agiliumtrade.ai'
    }
    yield


class TestDomainClient:

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_request(self):
        """Should execute request."""
        response = await domain_client.request_copyfactory(opts)
        assert response == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_use_cached_url(self):
        """Should use cached url on repeated request."""
        await domain_client.request_copyfactory(opts)
        response = await domain_client.request_copyfactory(opts)
        assert response == expected
        assert host_call.call_count == 1
        assert regions_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_url_again_if_expired(self):
        """Should request url again if expired."""
        with freeze_time(start_time) as frozen_datetime:
            await domain_client.request_copyfactory(opts)
            frozen_datetime.tick(610)
            response = await domain_client.request_copyfactory(opts)
            assert response == expected
            assert host_call.call_count == 2
            assert regions_call.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_request_error(self):
        """Should return request error."""
        request_call.mock(return_value=Response(400))
        try:
            await domain_client.request_copyfactory(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_failed_host(self):
        """Should return error if failed to get host."""
        host_call.mock(return_value=Response(400))
        try:
            await domain_client.request_copyfactory(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_failed_regions(self):
        """Should return error if failed to get regions."""
        regions_call.mock(return_value=Response(400))
        try:
            await domain_client.request_copyfactory(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_try_another_region_if_first_failed(self):
        """Should try another region if the first failed."""
        request_call.mock(return_value=Response(500))
        us_west_call = respx.get('https://copyfactory-api-v1.us-west.agiliumtrade.agiliumtrade.ai/users/current/' +
                                 'configuration/strategies')\
            .mock(return_value=Response(200, content=json.dumps(expected)))
        response = await domain_client.request_copyfactory(opts)
        assert response == expected
        assert us_west_call.call_count == 1
        assert host_call.call_count == 1
        assert regions_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_all_regions_failed(self):
        """Should return error if all regions failed."""
        request_call.mock(return_value=Response(500))
        respx.get('https://copyfactory-api-v1.us-west.agiliumtrade.agiliumtrade.ai/users/current/' +
                  'configuration/strategies') \
            .mock(return_value=Response(500))
        try:
            await domain_client.request_copyfactory(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'InternalException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_normal_request(self):
        """Should execute request."""
        opts = {
            'url':  'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/accountId',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        }

        request_stub = respx.get('https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/'
                                 'accounts/accountId') \
            .mock(return_value=Response(200, content=json.dumps(expected)))
        response = await domain_client.request(opts)
        assert response == expected
        assert request_stub.call_count == 1


class TestRequestSignal:
    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_request(self):
        """Should execute a request."""
        await domain_client.get_signal_client_host(['vint-hill'])
        response = await domain_client.request_signal(signal_opts, host, 'accountId')
        assert response == expectedSignals

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_with_multiple_regions(self):
        """Should execute a request with multiple regions."""
        host['regions'] = ['vint-hill', 'us-west']
        response = await domain_client.request_signal(signal_opts, host, 'accountId')
        assert response == expectedSignals
        assert signal_vint_call.call_count == 1
        assert signal_us_west_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_if_all_regions_failed(self):
        """Should return an error if all regions failed."""
        host['regions'] = ['vint-hill', 'us-west']
        http_client = HttpClient(10, 70, {'retries': 0})
        domain_client = DomainClient(http_client, token)
        signal_vint_call.mock(return_value=Response(500))
        try:
            await domain_client.request_signal(signal_opts, host, 'accountId')
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'InternalException'
        assert signal_vint_call.call_count == 1
        assert signal_us_west_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_host_if_expired(self):
        """Should execute a request and update host if expired."""
        with freeze_time(start_time) as frozen_datetime:
            host['lastUpdated'] = datetime.now().timestamp()
            signal_germany_call = respx.get('https://copyfactory-api-v1.germany.agiliumtrade.ai/users/current/'
                                            'subscribers/accountId/signals')\
                .mock(return_value=Response(200, content=json.dumps(expectedSignals)))

            signal_france_call = respx.get('https://copyfactory-api-v1.france.agiliumtrade.ai/users/current/'
                                           'subscribers/accountId/signals')\
                .mock(return_value=Response(200, content=json.dumps([])))

            get_account_call.mock(return_value=Response(200, content=json.dumps({
                '_id': 'accountId', 'region': 'germany',
                'accountReplicas': [{'_id': 'accountId2', 'region': 'france'}]})))

            await domain_client.request_signal(signal_opts, host, 'accountId')
            await asyncio.sleep(0.05)
            assert get_account_call.call_count == 0
            assert signal_germany_call.call_count == 0
            assert signal_france_call.call_count == 0
            frozen_datetime.tick(610)
            await domain_client.request_signal(signal_opts, host, 'accountId')
            await asyncio.sleep(0.05)
            assert get_account_call.call_count == 1
            assert signal_germany_call.call_count == 0
            assert signal_france_call.call_count == 0
            await domain_client.request_signal(signal_opts, host, 'accountId')
            assert get_account_call.call_count == 1
            assert signal_germany_call.call_count == 1
            assert signal_france_call.call_count == 1


class TestGetAccountInfo:
    @respx.mock
    @pytest.mark.asyncio
    async def test_get_account(self):
        """Should get account."""
        account = await domain_client.get_account_info('accountId')
        assert account == {'id': 'accountId2', 'regions': ['germany']}

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_account_with_replicas(self):
        """Should get account with replicas."""
        get_account_call.mock(return_value=Response(200, content=json.dumps({
            '_id': 'accountId',
            'region': 'vint-hill',
            'accountReplicas': [
                {
                    '_id': 'accountId2',
                    'region': 'us-west',
                }
            ]
        })))
        account = await domain_client.get_account_info('accountId')
        assert account == {'id': 'accountId', 'regions': ['vint-hill', 'us-west']}

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_primary_account_if_requested_is_replica(self):
        """Should get primary account if requested account is a replica."""
        get_account_call.mock(return_value=Response(200, content=json.dumps({
            '_id': 'accountId',
            'region': 'vint-hill',
            'primaryAccountId': 'accountId2'
        })))
        respx.get('https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/accountId2')\
            .mock(return_value=Response(200, content=json.dumps({
                '_id': 'accountId2', 'region': 'us-west', 'accountReplicas': [
                    {
                        '_id': 'accountId',
                        'region': 'vint-hill',
                    }
                ]
            })))
        account = await domain_client.get_account_info('accountId')
        assert account == {'id': 'accountId2', 'regions': ['us-west', 'vint-hill']}


class TestGetSignalClientHost:
    @respx.mock
    @pytest.mark.asyncio
    async def test_return_signal_client_host(self):
        """Should return signal client host."""
        response = await domain_client.get_signal_client_host(['vint-hill'])
        assert response == {
            'host': 'https://copyfactory-api-v1',
            'lastUpdated': ANY,
            'regions': ['vint-hill'],
            'domain': 'agiliumtrade.agiliumtrade.ai'
        }
