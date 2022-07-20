from .metaStats_models import Metrics, Trade, OpenTrade
from .domain_client import DomainClient


class MetaStatsClient:
    """metaapi.cloud MetaStats MetaTrader API client"""
    def __init__(self, domain_client: DomainClient):
        """Inits MetaTrader API client instance.

        Args:
            domain_client: HTTP client.
        """
        self._domainClient = domain_client

    async def get_metrics(self, account_id: str, include_open_positions: bool = False) -> Metrics:
        """Returns metrics of MetaApi account. This API call is billable
        https://metaapi.cloud/docs/metastats/restApi/api/calculateMetrics/

        Args:
            account_id: MetaApi account id.
            include_open_positions: Indicates whether open positions will be included in the metrics, default false.

        Returns:
            Account metrics.
        """
        def get_opts(host: str, id: str):
            return {
                'url': host + f'/users/current/accounts/{id}/metrics',
                'method': 'GET',
                'params': {
                    'includeOpenPositions': include_open_positions
                },
                'headers': {
                    'auth-token': self._domainClient.token
                }
            }

        response = await self._domainClient.request_metastats(get_opts, account_id)
        return response['metrics']

    async def get_account_trades(self, account_id: str, start_time: str, end_time: str, update_history: bool = True,
                                 limit: int = 1000, offset: int = 0) -> Trade:
        """Returns historical trades of MetaApi account.
        https://metaapi.cloud/docs/metastats/restApi/api/getHistoricalTrades/

        Args:
            account_id: MetaApi account id.
            start_time: Start of time range, inclusive.
            end_time: End of time range, exclusive.
            update_history: update historical trades before returning results. If set to true, the API call will be
            counted towards billable MetaStats API calls. If set to false, the API call is not billable.
            Default is true
            limit: Pagination limit.
            offset: Pagination offset.

        Returns:
            Account historical trades.
        """
        def get_opts(host: str, id: str):
            return {
                'url': host + f'/users/current/accounts/{id}/historical-trades/{start_time}/{end_time}',
                'method': 'GET',
                'params': {
                    'updateHistory': update_history,
                    'limit': limit,
                    'offset': offset
                },
                'headers': {
                    'auth-token': self._domainClient.token
                }
            }
        response = await self._domainClient.request_metastats(get_opts, account_id)
        return response['trades']

    async def get_account_open_trades(self, account_id: str) -> OpenTrade:
        """Returns open trades of MetaApi account. This API call is not billable.
        https://metaapi.cloud/docs/metastats/restApi/api/getOpenTrades/

        Args:
            account_id: MetaApi account id.

        Returns:
            Account historical trades.
        """
        def get_opts(host: str, id: str):
            return {
                'url': host + f'/users/current/accounts/{id}/open-trades',
                'method': 'GET',
                'headers': {
                    'auth-token': self._domainClient.token
                }
            }
        response = await self._domainClient.request_metastats(get_opts, account_id)
        return response['openTrades']
