from datetime import datetime
from typing import List
from copy import copy
from ..models import promise_any
from typing_extensions import TypedDict
import asyncio


class AccountInfo(TypedDict):
    """Account request info."""
    id: str
    """Primary account id."""
    regions: List[str]
    """Account available regions."""


class DomainClient:
    """Connection URL and request managing client"""

    def __init__(self, http_client, token: str, domain: str = None):
        """Inits domain client instance.

        Args:
            http_client: HTTP client.
            token: Authorization token.
            domain: Domain to connect to, default is agiliumtrade.agiliumtrade.ai.
        """
        self._httpClient = http_client
        self._domain = domain or 'agiliumtrade.agiliumtrade.ai'
        self._token = token
        self._urlCache = None
        self._regionCache = []
        self._regionIndex = 0

    @property
    def domain(self) -> str:
        """Returns domain client domain.

        Returns:
            Client domain.
        """
        return self._domain

    @property
    def token(self) -> str:
        """Returns domain client token.

        Returns:
            Client token.
        """
        return self._token

    async def request_copyfactory(self, opts: dict, is_extended_timeout: bool = False):
        """Sends a CopyFactory API request.

        Args:
            opts: Options request options.
            is_extended_timeout: Whether to run the request with an extended timeout.

        Returns:
            Request result.
        """
        await self._update_host()
        try:
            request_opts = copy(opts)
            request_opts['url'] = self._urlCache['url'] + request_opts['url']
            return await self._httpClient.request(request_opts, is_extended_timeout)
        except Exception as err:
            if err.__class__.__name__ not in ['ConflictException', 'InternalException', 'ApiException',
                                              'ConnectTimeout']:
                raise err
            else:
                if len(self._regionCache) == self._regionIndex + 1:
                    raise err
                else:
                    self._regionIndex += 1
                    return await self.request_copyfactory(opts, is_extended_timeout)

    async def request(self, opts: dict):
        """Sends an http request.

        Args:
            opts: Request options.

        Returns:
            Request result.
        """
        return await self._httpClient.request(opts)

    async def request_signal(self, opts: dict, host: dict, account_id: str):
        """Sends a signal client request.

        Args:
            opts: Request options.
            host: Signal client host data.
            account_id: Account id.

        Returns:
            Request result.
        """
        asyncio.create_task(self._update_account_regions(host, account_id))
        tasks = []
        for region in host['regions']:
            request_opts = copy(opts)
            request_opts['url'] = f'{host["host"]}.{region}.{host["domain"]}' + opts["url"]
            request_opts['headers'] = {'auth-token': self._token}
            tasks.append(asyncio.create_task(self._httpClient.request_with_failover(request_opts)))
        return await promise_any(tasks)

    async def get_signal_client_host(self, regions: List[str]) -> dict:
        """Returns CopyFactory host for signal client requests.

        Args:
            regions: Subscriber regions.

        Returns:
            Signal client CopyFactory host.
        """
        await self._update_host()
        return {
            'host': 'https://copyfactory-api-v1',
            'regions': regions,
            'lastUpdated': datetime.now().timestamp(),
            'domain': self._urlCache['domain']
        }

    async def get_account_info(self, account_id: str) -> AccountInfo:
        """Returns account data by id.

        Args:
            account_id: Account id.

        Returns:
            Account data.
        """
        async def get_account(id: str):
            account_opts = {
                'url': f'https://mt-provisioning-api-v1.{self.domain}/users/current/accounts/{id}',
                'method': 'GET',
                'headers': {
                  'auth-token': self.token
                },
            }
            return await self._httpClient.request_with_failover(account_opts)

        account_data = await get_account(account_id)
        if 'primaryAccountId' in account_data:
            primary_account_id = account_data['primaryAccountId']
            account_data = await get_account(primary_account_id)
        else:
            primary_account_id = account_data['_id']

        regions = [account_data['region']] + \
            (list(map(lambda replica: replica['region'], account_data['accountReplicas'])) if
             'accountReplicas' in account_data else [])

        return {
            'id': primary_account_id,
            'regions': regions
        }

    async def _update_host(self):
        if not self._urlCache or self._urlCache['lastUpdated'] < datetime.now().timestamp() - 60 * 10:
            await self._update_regions()
            url_settings = await self._httpClient.request({
                'url': f'https://mt-provisioning-api-v1.{self._domain}/users/current/servers/mt-client-api',
                'method': 'GET',
                'headers': {
                    'auth-token': self._token
                }
            })
            self._urlCache = {
                'url': f'https://copyfactory-api-v1.{self._regionCache[self._regionIndex]}.{url_settings["domain"]}',
                'domain': url_settings['domain'],
                'lastUpdated': datetime.now().timestamp()
            }
        else:
            self._urlCache = {
                'url': f'https://copyfactory-api-v1.{self._regionCache[self._regionIndex]}.{self._urlCache["domain"]}',
                'domain': self._urlCache['domain'],
                'lastUpdated': datetime.now().timestamp()
            }

    async def _update_regions(self):
        self._regionIndex = 0
        self._regionCache = await self._httpClient.request({
            'url': f'https://mt-provisioning-api-v1.{self._domain}/users/current/regions',
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            },
        })

    async def _update_account_regions(self, host: dict, account_id: str):
        if host['lastUpdated'] < datetime.now().timestamp() - 60 * 10:
            account_data = await self.get_account_info(account_id)
            host['lastUpdated'] = datetime.now().timestamp()
            host['regions'] = account_data['regions']
