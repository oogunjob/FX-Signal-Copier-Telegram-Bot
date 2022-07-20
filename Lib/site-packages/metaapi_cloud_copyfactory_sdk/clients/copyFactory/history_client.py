from ..metaApi_client import MetaApiClient
from ...models import format_date, convert_iso_time_to_date
from .copyFactory_models import CopyFactoryTransaction
from datetime import datetime
from typing import List
from ..domain_client import DomainClient


class HistoryClient(MetaApiClient):
    """metaapi.cloud CopyFactory history API (trade copying history API) client (see
    https://metaapi.cloud/docs/copyfactory/)"""

    def __init__(self, domain_client: DomainClient):
        """Inits CopyFactory history API client instance.

        Args:
            domain_client: Domain client.
        """
        super().__init__(domain_client)
        self._domainClient = domain_client

    async def get_provided_transactions(self, time_from: datetime, time_till: datetime,
                                        strategy_ids: List[str] = None, subscriber_ids: List[str] = None,
                                        offset: int = None, limit: int = None) -> \
            'List[CopyFactoryTransaction]':
        """Returns list of transactions on the strategies the current user provides to other users. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/history/getProvidedTransactions/

        Args:
            time_from: Time to load transactions from.
            time_till: Time to load transactions till.
            strategy_ids: The list of strategy ids to filter transactions by.
            subscriber_ids: The list of CopyFactory subscriber account ids to filter by.
            offset: Pagination offset. Default value is 0.
            limit: Pagination limit. Default value is 1000.

        Returns:
            A coroutine resolving with transactions found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_provided_transactions')
        qs = {
            'from': format_date(time_from),
            'till': format_date(time_till)
        }
        if strategy_ids:
            qs['strategyId'] = strategy_ids
        if subscriber_ids:
            qs['subscriberId'] = subscriber_ids
        if not (offset is None):
            qs['offset'] = offset
        if limit:
            qs['limit'] = limit
        opts = {
          'url': f'/users/current/provided-transactions',
          'method': 'GET',
          'headers': {
            'auth-token': self._token
          },
          'params': qs
        }
        transactions = await self._domainClient.request_copyfactory(opts, True)
        convert_iso_time_to_date(transactions)
        return transactions

    async def get_subscription_transactions(self, time_from: datetime, time_till: datetime,
                                            strategy_ids: List[str] = None, subscriber_ids: List[str] = None,
                                            offset: int = None, limit: int = None) -> \
            'List[CopyFactoryTransaction]':
        """Returns list of trades on the strategies the current user subscribed to
        https://metaapi.cloud/docs/copyfactory/restApi/api/history/getSubscriptionTransactions/

        Args:
            time_from: Time to load transactions from.
            time_till: Time to load transactions till.
            strategy_ids: The list of strategy ids to filter transactions by.
            subscriber_ids: The list of CopyFactory subscriber account ids to filter by.
            offset: Pagination offset. Default value is 0.
            limit: Pagination limit. Default value is 1000.

        Returns:
            A coroutine resolving with transactions found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_subscription_transactions')
        qs = {
            'from': format_date(time_from),
            'till': format_date(time_till)
        }
        if strategy_ids:
            qs['strategyId'] = strategy_ids
        if subscriber_ids:
            qs['subscriberId'] = subscriber_ids
        if not (offset is None):
            qs['offset'] = offset
        if limit:
            qs['limit'] = limit
        opts = {
          'url': f'/users/current/subscription-transactions',
          'method': 'GET',
          'headers': {
            'auth-token': self._token
          },
          'params': qs
        }
        transactions = await self._domainClient.request_copyfactory(opts, True)
        convert_iso_time_to_date(transactions)
        return transactions
