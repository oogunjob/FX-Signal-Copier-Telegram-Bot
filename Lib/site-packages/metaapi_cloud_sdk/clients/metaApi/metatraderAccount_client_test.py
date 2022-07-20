import pytest
from ..httpClient import HttpClient
from .metatraderAccount_client import MetatraderAccountClient
import json
import respx
from httpx import Response


PROVISIONING_API_URL = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai'
http_client = HttpClient()
account_client = MetatraderAccountClient(http_client, 'header.payload.sign')


class TestMetatraderAccountClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_many(self):
        """Should retrieve MetaTrader accounts from API."""
        expected = [{
            '_id': '1eda642a-a9a3-457c-99af-3bc5e8d5c4c9',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud',
            'tags': ['tag1', 'tag2']
        }]
        rsps = respx.get(f'{PROVISIONING_API_URL}/users/current/accounts')\
            .mock(return_value=Response(200, json=expected))
        accounts = await account_client.get_accounts({'provisioningProfileId':
                                                      'f9ce1f12-e720-4b9a-9477-c2d4cb25f076'})
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts' + \
            '?provisioningProfileId=f9ce1f12-e720-4b9a-9477-c2d4cb25f076'
        assert rsps.calls[0].request.method == 'GET'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_retrieve_mt_accounts_with_account_token(self):
        """Should not retrieve MetaTrader accounts from API with account token."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.get_accounts({'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076'})
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_accounts method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_one(self):
        """Should retrieve MetaTrader account from API."""
        expected = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud',
            'tags': ['tag1', 'tag2']
        }
        rsps = respx.get(f'{PROVISIONING_API_URL}/users/current/accounts/id') \
            .mock(return_value=Response(200, json=expected))
        accounts = await account_client.get_account('id')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id'
        assert rsps.calls[0].request.method == 'GET'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_by_token(self):
        """Should retrieve MetaTrader account by token from API."""
        expected = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
        }
        rsps = respx.get(f'{PROVISIONING_API_URL}/users/current/accounts/accessToken/token') \
            .mock(return_value=Response(200, json=expected))
        account_client = MetatraderAccountClient(http_client, 'token')
        accounts = await account_client.get_account_by_token()
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/accessToken/token'
        assert rsps.calls[0].request.method == 'GET'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_retrieve_account_by_token_with_api_token(self):
        """Should not retrieve MetaTrader account by token via API with api token."""
        account_client = MetatraderAccountClient(http_client, 'header.payload.sign')
        try:
            await account_client.get_account_by_token()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_account_by_token method, because you have connected ' + \
                   'with API access token. Please use account access token to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_create(self):
        """Should create MetaTrader account via API."""
        expected = {
            'id': 'id'
        }
        account = {
            'login': '50194988',
            'password': 'Test1234',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'type': 'cloud',
            'tags': ['tag1']
        }
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/accounts') \
            .mock(return_value=Response(201, json=expected))
        accounts = await account_client.create_account(account)
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_create_mt_account_with_account_token(self):
        """Should not create MetaTrader account via API with account token'."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.create_account({})
        except Exception as err:
            assert err.__str__() == 'You can not invoke create_account method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_deploy(self):
        """Should deploy MetaTrader account via API."""
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/accounts/id/deploy') \
            .mock(return_value=Response(204))
        await account_client.deploy_account('id')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id/deploy'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_deploy_mt_account_with_account_token(self):
        """Should not deploy MetaTrader account via API with account token'."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.deploy_account('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke deploy_account method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_undeploy(self):
        """Should undeploy MetaTrader account via API."""
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/accounts/id/undeploy') \
            .mock(return_value=Response(204))
        await account_client.undeploy_account('id')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id/undeploy'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_undeploy_mt_account_with_account_token(self):
        """Should not undeploy MetaTrader account via API with account token'."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.undeploy_account('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke undeploy_account method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_redeploy(self):
        """Should redeploy MetaTrader account via API."""
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/accounts/id/redeploy') \
            .mock(return_value=Response(204))
        await account_client.redeploy_account('id')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id/redeploy'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_redeploy_mt_account_with_account_token(self):
        """Should not redeploy MetaTrader account via API with account token'."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.redeploy_account('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke redeploy_account method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete(self):
        """Should delete MetaTrader account via API."""
        rsps = respx.delete(f'{PROVISIONING_API_URL}/users/current/accounts/id') \
            .mock(return_value=Response(204))
        await account_client.delete_account('id')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id'
        assert rsps.calls[0].request.method == 'DELETE'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_delete_mt_account_with_account_token(self):
        """Should not delete MetaTrader account via API with account token'."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.delete_account('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke delete_account method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_update(self):
        """Should update MetaTrader account via API."""
        update_account = {
              'name': 'new account name',
              'password': 'new_password007',
              'server': 'ICMarketsSC2-Demo',
              'tags': ['tag1']
            }
        rsps = respx.put(f'{PROVISIONING_API_URL}/users/current/accounts/id', json=update_account) \
            .mock(return_value=Response(204))
        await account_client.update_account('id', update_account)
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id'
        assert rsps.calls[0].request.method == 'PUT'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert rsps.calls[0].request.content == json.dumps(update_account).encode('utf-8')

    @pytest.mark.asyncio
    async def test_not_update_mt_account_with_account_token(self):
        """Should not update MetaTrader account via API with account token'."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.update_account('id', {})
        except Exception as err:
            assert err.__str__() == 'You can not invoke update_account method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_increase_reliability(self):
        """Should increase MetaTrader account reliability via API."""
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/accounts/id/increase-reliability') \
            .mock(return_value=Response(204))
        await account_client.increase_reliability('id')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/accounts/id/increase-reliability'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_increase_reliability_with_account_token(self):
        """Should not increase MetaTrader account reliability via API with account token."""
        account_client = MetatraderAccountClient(http_client, 'token')
        try:
            await account_client.increase_reliability('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke increase_reliability method, because you have connected ' + \
                    'with account access token. Please use API access token from ' + \
                    'https://app.metaapi.cloud/token page to invoke this method.'
