from .httpClient import HttpClient
from .domain_client import DomainClient
from mock import AsyncMock, ANY
import pytest
from freezegun import freeze_time
import respx
import json
from httpx import Response
from datetime import datetime

http_client = HttpClient()
token = 'header.payload.sign'
domain_client = DomainClient(http_client, token, 'risk-management-api-v1')
request_mock = AsyncMock()
expected = [{'_id': 'ABCD'}]
start_time = '2020-10-05 10:00:00.000'

request_call: respx.Route
regions_call: respx.Route
host_call: respx.Route
request_url = 'https://risk-management-api-v1.vint-hill.agiliumtrade.agiliumtrade.ai/some/rest/api'
regions_url = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/regions'
host_url = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/servers/mt-client-api'
opts = {
    'url': '/some/rest/api',
    'method': 'GET'
}
host = {
    'host': 'https://copyfactory-api-v1',
    'lastUpdated': datetime.now().timestamp(),
    'regions': ['vint-hill'],
    'domain': 'agiliumtrade.ai'
}


@pytest.fixture(autouse=True)
async def run_around_tests():
    global http_client
    http_client = HttpClient()
    global domain_client
    domain_client = DomainClient(http_client, token, 'risk-management-api-v1')

    global request_call
    request_call = respx.get(request_url).mock(return_value=Response(200, content=json.dumps(expected)))

    global regions_call
    regions_call = respx.get(regions_url)\
        .mock(return_value=Response(200, content=json.dumps(['vint-hill', 'us-west'])))

    global host_call
    host_call = respx.get(host_url)\
        .mock(return_value=Response(200, content=json.dumps({'domain': 'agiliumtrade.agiliumtrade.ai'})))

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
        response = await domain_client.request_api(opts)
        assert response == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_use_cached_url(self):
        """Should use cached url on repeated request."""
        await domain_client.request_api(opts)
        response = await domain_client.request_api(opts)
        assert response == expected
        assert host_call.call_count == 1
        assert regions_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_url_again_if_expired(self):
        """Should request url again if expired."""
        with freeze_time(start_time) as frozen_datetime:
            await domain_client.request_api(opts)
            frozen_datetime.tick(610)
            response = await domain_client.request_api(opts)
            assert response == expected
            assert host_call.call_count == 2
            assert regions_call.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_request_error(self):
        """Should return request error."""
        request_call.mock(return_value=Response(400))
        try:
            await domain_client.request_api(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_failed_host(self):
        """Should return error if failed to get host."""
        host_call.mock(return_value=Response(400))
        try:
            await domain_client.request_api(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_failed_regions(self):
        """Should return error if failed to get regions."""
        regions_call.mock(return_value=Response(400))
        try:
            await domain_client.request_api(opts)
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_try_another_region_if_first_failed(self):
        """Should try another region if the first failed."""
        request_call.mock(return_value=Response(500))
        us_west_call = respx.get('https://risk-management-api-v1.us-west.agiliumtrade.agiliumtrade.ai/some/rest/api')\
            .mock(return_value=Response(200, content=json.dumps(expected)))
        response = await domain_client.request_api(opts)
        assert response == expected
        assert us_west_call.call_count == 1
        assert host_call.call_count == 1
        assert regions_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_all_regions_failed(self):
        """Should return error if all regions failed."""
        request_call.mock(return_value=Response(500))
        respx.get('https://risk-management-api-v1.us-west.agiliumtrade.agiliumtrade.ai/some/rest/api') \
            .mock(return_value=Response(500))
        try:
            await domain_client.request_api(opts)
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
