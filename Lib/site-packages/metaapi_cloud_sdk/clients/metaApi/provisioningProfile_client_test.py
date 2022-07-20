import json
import mock as mock
import pytest
import respx
from httpx import Response
from ..httpClient import HttpClient
from .provisioningProfile_client import ProvisioningProfileClient

PROVISIONING_API_URL = 'https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai'
httpClient = HttpClient()
provisioning_client = ProvisioningProfileClient(httpClient, 'header.payload.sign')


class TestProvisioningProfileClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_many(self):
        """Should retrieve provisioning profiles from API."""
        expected = [{
            '_id': 'id',
            'name': 'name',
            'version': 4,
            'status': 'active'
        }]
        rsps = respx.get(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles') \
            .mock(return_value=Response(200, json=expected))
        profiles = await provisioning_client.get_provisioning_profiles(5, 'active')
        assert rsps.calls[0].request.url == \
            f'{PROVISIONING_API_URL}/users/current/provisioning-profiles?version=5&status=active'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert profiles == expected

    @pytest.mark.asyncio
    async def test_not_retrieve_profiles_with_account_token(self):
        """Should not retrieve provisioning profiles from API with account token."""
        provisioning_client = ProvisioningProfileClient(httpClient, 'token')
        try:
            await provisioning_client.get_provisioning_profiles(5, 'active')
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_provisioning_profiles method, because you ' + \
                'have connected with account access token. Please use API access token from ' + \
                'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_one(self):
        """Should retrieve provisioning profile from API."""
        expected = {
            '_id': 'id',
            'name': 'name',
            'version': 4,
            'status': 'active'
        }
        rsps = respx.get(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id') \
            .mock(return_value=Response(200, json=expected))
        profile = await provisioning_client.get_provisioning_profile('id')
        assert rsps.calls[0].request.url == \
            f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert profile == expected

    @pytest.mark.asyncio
    async def test_not_retrieve_profile_with_account_token(self):
        """Should not retrieve provisioning profile from API with account token."""
        provisioning_client = ProvisioningProfileClient(httpClient, 'token')
        try:
            await provisioning_client.get_provisioning_profile('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_provisioning_profile method, because you ' + \
                   'have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_create(self):
        """Should create provisioning profile via API."""
        expected = {
            'id': 'id'
        }
        profile = {
            'name': 'name',
            'version': 4,
        }
        rsps = respx.post(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles') \
            .mock(return_value=Response(200, json=expected))
        id = await provisioning_client.create_provisioning_profile(profile)
        assert rsps.calls[0].request.url == f'{PROVISIONING_API_URL}/users/current/provisioning-profiles'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert rsps.calls[0].request.content == json.dumps(profile).encode('utf-8')
        assert id == expected

    @pytest.mark.asyncio
    async def test_not_create_profile_with_account_token(self):
        """Should not create provisioning profile from API with account token."""
        provisioning_client = ProvisioningProfileClient(httpClient, 'token')
        try:
            await provisioning_client.create_provisioning_profile({})
        except Exception as err:
            assert err.__str__() == 'You can not invoke create_provisioning_profile method, because you ' + \
                   'have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_upload_file(self):
        """Should upload file to a provisioning profile via API."""
        rsps = respx.put(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id/servers.dat') \
            .mock(return_value=Response(204))
        with mock.patch('__main__.open', new=mock.mock_open(read_data='test')) as file:
            file.return_value = json.dumps('test').encode()
            await provisioning_client.upload_provisioning_profile_file('id', 'servers.dat', file())
            assert rsps.calls[0].request.url == \
                f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id/servers.dat'
            assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_upload_file_with_account_token(self):
        """Should not upload provisioning profile file via API with account token."""
        provisioning_client = ProvisioningProfileClient(httpClient, 'token')
        try:
            await provisioning_client.upload_provisioning_profile_file('id', 'servers.dat', {})
        except Exception as err:
            assert err.__str__() == 'You can not invoke upload_provisioning_profile_file method, because you ' + \
                   'have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete(self):
        """Should delete provisioning profile via API."""
        rsps = respx.delete(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id') \
            .mock(return_value=Response(200))
        await provisioning_client.delete_provisioning_profile('id')
        assert rsps.calls[0].request.url == \
            f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'

    @pytest.mark.asyncio
    async def test_not_delete_with_account_token(self):
        """Should not delete provisioning profile via API with account token."""
        provisioning_client = ProvisioningProfileClient(httpClient, 'token')
        try:
            await provisioning_client.delete_provisioning_profile('id')
        except Exception as err:
            assert err.__str__() == 'You can not invoke delete_provisioning_profile method, because you ' + \
                   'have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_update(self):
        """Should update provisioning profile via API."""
        rsps = respx.put(f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id') \
            .mock(return_value=Response(200))
        await provisioning_client.update_provisioning_profile('id', {'name': 'new name'})
        assert rsps.calls[0].request.url == \
               f'{PROVISIONING_API_URL}/users/current/provisioning-profiles/id'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert rsps.calls[0].request.content == json.dumps({'name': 'new name'}).encode('utf-8')

    @pytest.mark.asyncio
    async def test_not_update_with_account_token(self):
        """Should not update provisioning profile via API with account token."""
        provisioning_client = ProvisioningProfileClient(httpClient, 'token')
        try:
            await provisioning_client.update_provisioning_profile('id', {'name': 'new name'})
        except Exception as err:
            assert err.__str__() == 'You can not invoke update_provisioning_profile method, because you ' + \
                   'have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'
