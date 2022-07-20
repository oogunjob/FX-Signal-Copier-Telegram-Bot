from datetime import datetime
from typing import List
from typing_extensions import TypedDict
from .errorHandler import ValidationException


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
        self._accountCache = {}

    @property
    def token(self) -> str:
        """Returns domain client token.

        Returns:
            Client token.
        """
        return self._token

    async def request_metastats(self, get_opts, account_id: str):
        """Sends a MetaStats API request.

        Args:
            get_opts: Function to get request options.
            account_id: Account id..

        Returns:
            Request result.
        """
        await self._update_host()
        await self._update_account_host(account_id)
        account_cache = self._accountCache[account_id]
        try:
            region_settings = account_cache['regions'][account_cache['regionIndex']]
            opts = get_opts(f'https://metastats-api-v1.{region_settings["region"]}.{self._urlCache["domain"]}',
                            region_settings['id'])

            return await self._httpClient.request(opts)
        except Exception as err:
            if err.__class__.__name__ not in ['ConflictException', 'InternalException', 'ApiException',
                                              'ConnectTimeout']:
                raise err
            else:
                if len(account_cache['regions']) == account_cache['regionIndex'] + 1:
                    raise err
                else:
                    account_cache['regionIndex'] += 1
                    return await self.request_metastats(get_opts, account_id)

    async def _update_host(self):
        if not self._urlCache or self._urlCache['lastUpdated'] < datetime.now().timestamp() - 60 * 10:
            url_settings = await self._httpClient.request_with_failover({
                'url': f'https://mt-provisioning-api-v1.{self._domain}/users/current/servers/mt-client-api',
                'method': 'GET',
                'headers': {
                    'auth-token': self._token
                }
            })
            self._urlCache = {
                'domain': url_settings['domain'],
                'lastUpdated': datetime.now().timestamp()
            }

    async def _update_account_host(self, account_id: str):
        if account_id not in self._accountCache or self._accountCache[account_id]['lastUpdated'] < \
                datetime.now().timestamp() - 60 * 10:

            async def get_account(id: str):
                account_opts = {
                    'url': f'https://mt-provisioning-api-v1.{self._domain}/users/current/accounts/{id}',
                    'method': 'GET',
                    'headers': {
                        'auth-token': self._token
                    },
                }

                return await self._httpClient.request_with_failover(account_opts)

            account_data = await get_account(account_id)
            if 'primaryAccountId' in account_data:
                account_data = await get_account(account_data['primaryAccountId'])

            accounts = [{'_id': account_data['_id'], 'region': account_data['region'],
                         'state': account_data['state']}] + (
                account_data['accountReplicas'] if 'accountReplicas' in account_data else [])
            accounts = list(filter(lambda account: account['state'] == 'DEPLOYED', accounts))

            if not len(accounts):
                raise ValidationException('There are no replicas deployed yet. Please make sure at least ' +
                                          'one of the replicas is deployed.')

            regions = list(map(lambda account: {'region': account['region'], 'id': account['_id']}, accounts))

            self._accountCache[account_id] = {
                'regions': regions,
                'regionIndex': 0,
                'lastUpdated': datetime.now().timestamp()
            }
