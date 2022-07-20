from ..metaApi_client import MetaApiClient
from typing_extensions import TypedDict
from typing import List


class TypeHashingIgnoredFieldLists(TypedDict):
    """Type hashing ignored field lists"""
    specification: List[str]
    """Specification ignored fields."""
    position: List[str]
    """Position ignored fields."""
    order: List[str]
    """Order ignored fields."""


class HashingIgnoredFieldLists(TypedDict):
    """Hashing ignored field lists."""
    g1: TypeHashingIgnoredFieldLists
    """G1 hashing ignored field lists."""
    g2: TypeHashingIgnoredFieldLists
    """G2 hashing ignored field lists."""


class ClientApiClient(MetaApiClient):
    """metaapi.cloud client API client (see https://metaapi.cloud/docs/client/)"""

    def __init__(self, http_client, token: str, domain: str = 'agiliumtrade.agiliumtrade.ai'):
        """Inits client API client instance.

        Args:
            http_client: HTTP client.
            token: Authorization token.
            domain: Domain to connect to, default is agiliumtrade.agiliumtrade.ai.
        """
        super().__init__(http_client, token, domain)
        self._host = f'https://mt-client-api-v1.{domain}'

    async def get_hashing_ignored_field_lists(self) -> HashingIgnoredFieldLists:
        """Retrieves hashing ignored field lists.

        Returns:
            A coroutine resolving with hashing ignored field lists
        """
        opts = {
            'url': f'{self._host}/hashing-ignored-field-lists',
            'method': 'GET',
        }
        return await self._httpClient.request(opts)
