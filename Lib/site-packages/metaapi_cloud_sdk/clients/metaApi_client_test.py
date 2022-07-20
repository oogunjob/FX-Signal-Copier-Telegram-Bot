from .httpClient import HttpClient
from .metaApi_client import MetaApiClient
import pytest
http_client = HttpClient()
api_client = MetaApiClient(http_client, 'token')


@pytest.fixture(autouse=True)
async def run_around_tests():
    global http_client
    http_client = HttpClient()
    global api_client
    api_client = MetaApiClient(http_client, 'token')
    yield


class TestMetaApiClient:
    @pytest.mark.asyncio
    async def test_return_account_token_type(self):
        """Should return account token type."""
        assert api_client._token_type == 'account'

    @pytest.mark.asyncio
    async def test_return_api_token_type(self):
        """Should return api token type."""
        api_client = MetaApiClient(http_client, 'header.payload.sign')
        assert api_client._token_type == 'api'

    @pytest.mark.asyncio
    async def test_check_token_not_jwt(self):
        """Should check that current token is not JWT."""
        assert api_client._is_not_jwt_token()

    @pytest.mark.asyncio
    async def test_check_token_not_account(self):
        """Should check that current token is not account token."""
        api_client = MetaApiClient(http_client, 'header.payload.sign')
        assert api_client._is_not_account_token()

    @pytest.mark.asyncio
    async def test_handle_no_access_exception_with_account_token(self):
        """Should handle no access exception with account token."""
        try:
            api_client._handle_no_access_exception('methodName')
        except Exception as err:
            assert err.__str__() == 'You can not invoke methodName method, because you have connected with account ' + \
                   'access token. Please use API access token from https://app.metaapi.cloud/token page to invoke ' + \
                   'this method.'

    @pytest.mark.asyncio
    async def test_handle_no_access_exception_with_api_token(self):
        """Should handle no access exception with api token."""
        api_client = MetaApiClient(http_client, 'header.payload.sign')
        try:
            api_client._handle_no_access_exception('methodName')
        except Exception as err:
            assert err.__str__() == 'You can not invoke methodName method, because you have connected with API ' + \
                'access token. Please use account access token to invoke this method.'
