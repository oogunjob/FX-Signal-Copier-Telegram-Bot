import pytest
import respx
from httpx import Response
from ..httpClient import HttpClient
from .clientApi_client import ClientApiClient

CLIENT_API_URL = 'https://mt-client-api-v1.agiliumtrade.agiliumtrade.ai'
httpClient = HttpClient()
client_api_client = ClientApiClient(httpClient, 'header.payload.sign')


class TestClientApiClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve(self):
        """Should retrieve hashing ignored field lists."""
        expected = {
            'g1': {
                'specification': ['description'],
                'position': ['time'],
                'order': ['expirationTime']
            },
            'g2': {
                'specification': ['pipSize'],
                'position': ['comment'],
                'order': ['brokerComment']
            }
        }
        rsps = respx.get(f'{CLIENT_API_URL}/hashing-ignored-field-lists') \
            .mock(return_value=Response(200, json=expected))
        ignored_fields = await client_api_client.get_hashing_ignored_field_lists()
        assert rsps.calls[0].request.url == \
            f'{CLIENT_API_URL}/hashing-ignored-field-lists'
        assert ignored_fields == expected
