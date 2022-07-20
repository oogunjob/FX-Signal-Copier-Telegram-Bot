from datetime import datetime
from copy import copy


class DomainClient:
    """Connection URL and request managing client"""

    def __init__(self, http_client, token: str, api_path: str, domain: str = None):
        """Inits domain client instance.

        Args:
            http_client: HTTP client.
            token: Authorization token.
            api_path: Api URL part.
            domain: Domain to connect to, default is agiliumtrade.agiliumtrade.ai.
        """
        self._httpClient = http_client
        self._apiPath = api_path
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

    async def request_api(self, opts: dict, is_extended_timeout: bool = False):
        """Sends an authorized json API request.

        Args:
            opts: Options request options.
            is_extended_timeout: Whether to run the request with an extended timeout.

        Returns:
            Request result.
        """
        await self._update_host()
        try:
            request_opts = copy(opts)
            request_opts['headers'] = opts['headers'] if 'headers' in opts else {'auth-token': self._token}
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
                    return await self.request_api(opts, is_extended_timeout)

    async def request(self, opts: dict):
        """Sends an http request.

        Args:
            opts: Request options.

        Returns:
            Request result.
        """
        return await self._httpClient.request(opts)

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
                'url': f'https://{self._apiPath}.{self._regionCache[self._regionIndex]}.{url_settings["domain"]}',
                'domain': url_settings['domain'],
                'lastUpdated': datetime.now().timestamp()
            }
        else:
            self._urlCache = {
                'url': f'https://{self._apiPath}.{self._regionCache[self._regionIndex]}.{self._urlCache["domain"]}',
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
