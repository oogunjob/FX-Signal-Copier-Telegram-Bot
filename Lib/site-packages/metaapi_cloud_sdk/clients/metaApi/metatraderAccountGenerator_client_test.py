import pytest
import respx
from httpx import Response
from ..httpClient import HttpClient
from .metatraderAccountGenerator_client import MetatraderAccountGeneratorClient
PROVISIONING_API_URL = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai'
http_client = HttpClient()
demo_account_client = MetatraderAccountGeneratorClient(http_client, 'header.payload.sign')


class TestMetatraderDemoAccountClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_create_demo_mt4(self):
        """Should create new MetaTrader 4 demo account."""
        expected = {
            'login': '12345',
            'password': 'qwerty',
            'serverName': 'HugosWay-Demo3',
            'investorPassword': 'qwerty'
        }
        account = {
            'accountType': 'type',
            'balance': 10,
            'email': 'test@test.com',
            'leverage': 15,
            'serverName': 'HugosWay-Demo3'
        }
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/profileId1/mt4-demo-accounts') \
            .mock(return_value=Response(200, json=expected))
        accounts = await demo_account_client.create_mt4_demo_account(account, 'profileId1')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/' + \
            'profileId1/mt4-demo-accounts'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_create_mt4_demo_with_account_token(self):
        """Should not create MetaTrader 4 demo account via API with account token."""
        account_client = MetatraderAccountGeneratorClient(http_client, 'token')
        try:
            await account_client.create_mt4_demo_account({}, '')
        except Exception as err:
            assert err.__str__() == 'You can not invoke create_mt4_demo_account method, because you have ' + \
                                    'connected with account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_live_mt4(self):
        """Should create new MetaTrader 4 live account."""
        expected = {
            'login': '12345',
            'password': 'qwerty',
            'serverName': 'HugosWay-Live3',
            'investorPassword': 'qwerty'
        }
        account = {
            'accountType': 'type',
            'balance': 10,
            'email': 'test@test.com',
            'leverage': 15,
            'serverName': 'HugosWay-Live3'
        }
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/profileId1/mt4-live-accounts') \
            .mock(return_value=Response(200, json=expected))
        accounts = await demo_account_client.create_mt4_live_account(account, 'profileId1')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/' + \
            'profileId1/mt4-live-accounts'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_create_mt4_live_with_account_token(self):
        """Should not create MetaTrader 4 live account via API with account token."""
        account_client = MetatraderAccountGeneratorClient(http_client, 'token')
        try:
            await account_client.create_mt4_live_account({}, '')
        except Exception as err:
            assert err.__str__() == 'You can not invoke create_mt4_live_account method, because you have ' + \
                                    'connected with account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_demo_mt5(self):
        """Should create new MetaTrader 5 demo account."""
        expected = {
            'login': '12345',
            'password': 'qwerty',
            'serverName': 'HugosWay-Demo3',
            'investorPassword': 'qwerty'
        }
        account = {
            'accountType': 'type',
            'balance': 10,
            'email': 'test@test.com',
            'leverage': 15,
            'serverName': 'server'
        }
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/profileId2/mt5-demo-accounts') \
            .mock(return_value=Response(200, json=expected))
        accounts = await demo_account_client.create_mt5_demo_account(account, 'profileId2')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/' + \
               'profileId2/mt5-demo-accounts'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_create_mt5_demo_with_account_token(self):
        """Should not create MetaTrader 5 demo account via API with account token."""
        account_client = MetatraderAccountGeneratorClient(http_client, 'token')
        try:
            await account_client.create_mt5_demo_account({}, '')
        except Exception as err:
            assert err.__str__() == 'You can not invoke create_mt5_demo_account method, because you have ' + \
                                    'connected with account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_create_live_mt5(self):
        """Should create new MetaTrader 5 live account."""
        expected = {
            'login': '12345',
            'password': 'qwerty',
            'serverName': 'HugosWay-Demo3',
            'investorPassword': 'qwerty'
        }
        account = {
            'accountType': 'type',
            'balance': 10,
            'email': 'test@test.com',
            'leverage': 15,
            'serverName': 'server'
        }
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/profileId2/mt5-live-accounts') \
            .mock(return_value=Response(200, json=expected))
        accounts = await demo_account_client.create_mt5_live_account(account, 'profileId2')
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/' + \
               'profileId2/mt5-live-accounts'
        assert rsps.calls[0].request.method == 'POST'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert accounts == expected

    @pytest.mark.asyncio
    async def test_not_create_mt5_live_with_account_token(self):
        """Should not create MetaTrader 5 live account via API with account token."""
        account_client = MetatraderAccountGeneratorClient(http_client, 'token')
        try:
            await account_client.create_mt5_live_account({}, '')
        except Exception as err:
            assert err.__str__() == 'You can not invoke create_mt5_live_account method, because you have ' + \
                                    'connected with account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'
