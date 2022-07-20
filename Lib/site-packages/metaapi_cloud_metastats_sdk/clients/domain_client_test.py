from .httpClient import HttpClient
from .domain_client import DomainClient
from mock import AsyncMock, ANY
import pytest
from freezegun import freeze_time
import respx
import json
from httpx import Response
import asyncio

http_client = HttpClient()
domain_client = DomainClient(http_client, 'token')
request_mock = AsyncMock()

token = 'header.payload.sign'
expected = {'trades': 10, 'equity': 10102.5, 'balance': 10105, 'profit': 104, 'deposits': 10001}
start_time = '2020-10-05 10:00:00.000'

request_call: respx.Route
host_call: respx.Route
get_account_call: respx.Route


def get_opts(host, id):
    return {
        'url': host + f'/users/current/accounts/{id}/open-trades',
        'method': 'GET',
        'headers': {
          'auth-token': token
        },
    }


@pytest.fixture(autouse=True)
async def run_around_tests():
    global http_client
    http_client = HttpClient()
    global domain_client
    domain_client = DomainClient(http_client, token)

    global get_account_call
    get_account_call = respx.get('https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/'
                                 'accounts/accountId')\
        .mock(return_value=Response(200, content=json.dumps({
            '_id': 'accountId', 'region': 'vint-hill', 'state': 'DEPLOYED', 'accountReplicas': [
                {'_id': 'accountId2', 'region': 'us-west', 'state': 'DEPLOYED'}]})))

    global request_call
    request_call = respx.get('https://metastats-api-v1.vint-hill.agiliumtrade.ai/users/current/accounts/accountId/'
                             'open-trades').mock(return_value=Response(200, content=json.dumps(expected)))

    global host_call
    host_call = respx.get(
        'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/servers/mt-client-api')\
        .mock(return_value=Response(200, content=json.dumps({'domain': 'agiliumtrade.ai'})))
    yield


class TestDomainClient:

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_request(self):
        """Should execute request."""
        response = await domain_client.request_metastats(get_opts, 'accountId')
        assert response == expected
        assert request_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_url_again_if_expired(self):
        """Should request url again if expired."""
        with freeze_time(start_time) as frozen_datetime:
            await domain_client.request_metastats(get_opts, 'accountId')
            frozen_datetime.tick(610)
            response = await domain_client.request_metastats(get_opts, 'accountId')
            assert response == expected
            assert host_call.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_use_cached_url(self):
        """Should use cached url on repeated request."""
        await domain_client.request_metastats(get_opts, 'accountId')
        response = await domain_client.request_metastats(get_opts, 'accountId')
        assert response == expected
        assert host_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_failed_host(self):
        """Should return error if failed to get host."""
        host_call.mock(return_value=Response(400))
        try:
            await domain_client.request_metastats(get_opts, 'accountId')
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_failed_get_account_data(self):
        """Should return error if failed to get account data."""
        get_account_call.mock(return_value=Response(400))
        try:
            await domain_client.request_metastats(get_opts, 'accountId')
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_request_main_account_if_using_replica(self):
        """Should request main account if using replica."""
        respx.get(
            'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/accountId2') \
            .mock(return_value=Response(200, content=json.dumps({
                '_id': 'accountId2', 'region': 'us-west', 'primaryAccountId': 'accountId', 'state': 'DEPLOYED'})))

        response = await domain_client.request_metastats(get_opts, 'accountId2')
        assert response == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_try_another_region_if_first_failed(self):
        """Should try another region if the first failed."""
        request_call.mock(return_value=Response(500))
        respx.get(
            'https://metastats-api-v1.us-west.agiliumtrade.ai/users/current/accounts/accountId2/open-trades') \
            .mock(return_value=Response(200, content=json.dumps(expected)))
        response = await domain_client.request_metastats(get_opts, 'accountId')
        assert response == expected
        assert host_call.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_all_regions_failed(self):
        """Should return error if all regions failed."""
        request_call.mock(return_value=Response(500))
        respx.get(
            'https://metastats-api-v1.us-west.agiliumtrade.ai/users/current/accounts/accountId2/open-trades') \
            .mock(return_value=Response(500))
        try:
            await domain_client.request_metastats(get_opts, 'accountId')
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'InternalException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_update_host_if_expired(self):
        """Should execute a request and update host if expired."""
        with freeze_time(start_time) as frozen_datetime:
            other_region_call = respx.get('https://metastats-api-v1.us-west.agiliumtrade.ai/' +
                                          'users/current/accounts/accountId2/open-trades')\
                .mock(return_value=Response(200, content=json.dumps(expected)))
            get_account_call.mock(return_value=Response(200, content=json.dumps({
                '_id': 'accountId', 'region': 'vint-hill', 'state': 'DEPLOYED'})))

            await domain_client.request_metastats(get_opts, 'accountId')
            await asyncio.sleep(0.05)
            assert get_account_call.call_count == 1
            assert other_region_call.call_count == 0
            get_account_call.mock(return_value=Response(200, content=json.dumps({
                '_id': 'accountId2', 'region': 'us-west', 'state': 'DEPLOYED'})))
            frozen_datetime.tick(610)
            result = await domain_client.request_metastats(get_opts, 'accountId')
            assert result == expected
            await asyncio.sleep(0.05)
            assert get_account_call.call_count == 2
            assert other_region_call.call_count == 1
            await domain_client.request_metastats(get_opts, 'accountId')
            await asyncio.sleep(0.05)
            assert get_account_call.call_count == 2
            assert other_region_call.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_no_replicas_deployed(self):
        """Should return error if no replicas are deployed."""
        get_account_call.mock(return_value=Response(200, content=json.dumps({
            '_id': 'accountId', 'region': 'vint-hill', 'state': 'UNDEPLOYED'})))
        try:
            await domain_client.request_metastats(get_opts, 'accountId')
            pytest.fail()
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'

    @respx.mock
    @pytest.mark.asyncio
    async def test_filter_out_undeployed_replicas(self):
        """Should filter out undeployed replicas."""
        get_account_call.mock(return_value=Response(200, content=json.dumps({
            '_id': 'accountId', 'region': 'vint-hill', 'state': 'UNDEPLOYED', 'accountReplicas': [
                {'_id': 'accountId2', 'region': 'us-west', 'state': 'UNDEPLOYED'},
                {'_id': 'accountId3', 'region': 'germany', 'state': 'DEPLOYED'}
            ]})))
        other_region_call = respx\
            .get('https://metastats-api-v1.germany.agiliumtrade.ai/users/current/accounts/accountId3/open-trades')\
            .mock(return_value=Response(200, content=json.dumps(expected)))
        response = await domain_client.request_metastats(get_opts, 'accountId')
        assert response == expected
        assert other_region_call.call_count == 1
