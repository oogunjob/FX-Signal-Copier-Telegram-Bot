from ..metaApi_client import MetaApiClient
from ...models import random_id, convert_iso_time_to_date, format_request
from .copyFactory_models import StrategyId, CopyFactoryStrategyUpdate, CopyFactorySubscriberUpdate, \
    CopyFactorySubscriber, CopyFactoryStrategy, CopyFactoryPortfolioStrategy, \
    CopyFactoryPortfolioStrategyUpdate, CopyFactoryCloseInstructions
from typing import List
from ..domain_client import DomainClient
from copy import deepcopy


class ConfigurationClient(MetaApiClient):
    """metaapi.cloud CopyFactory configuration API (trade copying configuration API) client (see
    https://metaapi.cloud/docs/copyfactory/)"""

    def __init__(self, domain_client: DomainClient):
        """Inits CopyFactory configuration API client instance.

        Args:
            domain_client: Domain client.
        """
        super().__init__(domain_client)
        self._domainClient = domain_client

    async def generate_strategy_id(self) -> StrategyId:
        """Retrieves new unused strategy id. Method is accessible only with API access token. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/generateStrategyId/

        Returns:
            A coroutine resolving with strategy id generated.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('generate_strategy_id')
        opts = {
            'url': f"/users/current/configuration/unused-strategy-id",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._domainClient.request_copyfactory(opts)

    @staticmethod
    def generate_account_id() -> str:
        """Generates random account id.

        Returns:
            Account id.
        """
        return random_id(64)

    async def get_strategies(self, include_removed: bool = None, limit: int = None,
                             offset: int = None) -> 'List[CopyFactoryStrategy]':
        """Retrieves CopyFactory copy trading strategies. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/getStrategies/

        Args:
            include_removed: Flag instructing to include removed strategies in results.
            limit: Pagination limit.
            offset: Pagination offset.

        Returns:
            A coroutine resolving with CopyFactory strategies found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_strategies')
        qs = {}
        if include_removed is not None:
            qs['includeRemoved'] = include_removed
        if limit is not None:
            qs['limit'] = limit
        if offset is not None:
            qs['offset'] = offset
        opts = {
            'url': f"/users/current/configuration/strategies",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            },
            'params': qs
        }
        result = await self._domainClient.request_copyfactory(opts, True)
        convert_iso_time_to_date(result)
        return result

    async def get_strategy(self, strategy_id: str) -> CopyFactoryStrategy:
        """Retrieves CopyFactory copy trading strategy by id. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/getStrategy/

        Args:
            strategy_id: Trading strategy id.

        Returns:
            A coroutine resolving with CopyFactory strategy found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_strategy')
        opts = {
            'url': f"/users/current/configuration/strategies/{strategy_id}",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        strategy = await self._domainClient.request_copyfactory(opts)
        convert_iso_time_to_date(strategy)
        return strategy

    async def update_strategy(self, strategy_id: str, strategy: CopyFactoryStrategyUpdate):
        """Updates a CopyFactory strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/updateStrategy/

        Args:
            strategy_id: Copy trading strategy id.
            strategy: Trading strategy update.

        Returns:
            A coroutine resolving when strategy is updated.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('update_strategy')
        payload = deepcopy(strategy)
        format_request(payload)
        opts = {
            'url': f"/users/current/configuration/strategies/{strategy_id}",
            'method': 'PUT',
            'headers': {
                'auth-token': self._token
            },
            'body': payload
        }
        return await self._domainClient.request_copyfactory(opts)

    async def remove_strategy(self, strategy_id: str, close_instructions: CopyFactoryCloseInstructions = None):
        """Deletes a CopyFactory strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/removeStrategy/

        Args:
            strategy_id: Copy trading strategy id.
            close_instructions: Strategy close instructions.

        Returns:
            A coroutine resolving when strategy is removed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('remove_strategy')
        opts = {
            'url': f"/users/current/configuration/strategies/{strategy_id}",
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        if close_instructions is not None:
            format_request(close_instructions)
            opts['body'] = close_instructions
        return await self._domainClient.request_copyfactory(opts)

    async def get_portfolio_strategies(self, include_removed: bool = None, limit: int = None,
                                       offset: int = None) -> 'List[CopyFactoryPortfolioStrategy]':
        """Retrieves CopyFactory copy portfolio strategies. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/getPortfolioStrategies/

        Args:
            include_removed: Flag instructing to include removed portfolio strategies in results.
            limit: Pagination limit.
            offset: Pagination offset.

        Returns:
            A coroutine resolving with CopyFactory portfolio strategies found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_portfolio_strategies')
        qs = {}
        if include_removed is not None:
            qs['includeRemoved'] = include_removed
        if limit is not None:
            qs['limit'] = limit
        if offset is not None:
            qs['offset'] = offset
        opts = {
            'url': f"/users/current/configuration/portfolio-strategies",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            },
            'params': qs
        }
        result = await self._domainClient.request_copyfactory(opts, True)
        convert_iso_time_to_date(result)
        return result

    async def get_portfolio_strategy(self, portfolio_id: str) -> CopyFactoryPortfolioStrategy:
        """Retrieves a CopyFactory copy portfolio strategy by id. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/getPortfolioStrategy/

        Args:
            portfolio_id: Portfolio strategy id.

        Returns:
            A coroutine resolving with CopyFactory portfolio strategy found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_portfolio_strategy')
        opts = {
            'url': f"/users/current/configuration/portfolio-strategies/{portfolio_id}",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        strategy = await self._domainClient.request_copyfactory(opts)
        convert_iso_time_to_date(strategy)
        return strategy

    async def update_portfolio_strategy(self, portfolio_id: str, portfolio: CopyFactoryPortfolioStrategyUpdate):
        """Updates a CopyFactory portfolio strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/updatePortfolioStrategy/

        Args:
            portfolio_id: Copy trading portfolio strategy id.
            portfolio: Portfolio strategy update.

        Returns:
            A coroutine resolving when portfolio strategy is updated.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('update_portfolio_strategy')
        payload = deepcopy(portfolio)
        format_request(payload)
        opts = {
            'url': f"/users/current/configuration/portfolio-strategies/{portfolio_id}",
            'method': 'PUT',
            'headers': {
                'auth-token': self._token
            },
            'body': payload
        }
        return await self._domainClient.request_copyfactory(opts)

    async def remove_portfolio_strategy(self, portfolio_id: str,
                                        close_instructions: CopyFactoryCloseInstructions = None):
        """Deletes a CopyFactory portfolio strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/removePortfolioStrategy/

        Args:
            portfolio_id: Portfolio strategy id.
            close_instructions: Portfolio close instructions.

        Returns:
            A coroutine resolving when portfolio strategy is removed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('remove_portfolio_strategy')
        opts = {
            'url': f"/users/current/configuration/portfolio-strategies/{portfolio_id}",
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        if close_instructions is not None:
            format_request(close_instructions)
            opts['body'] = close_instructions
        return await self._domainClient.request_copyfactory(opts)

    async def remove_portfolio_strategy_member(self, portfolio_id: str, strategy_id: str,
                                               close_instructions: CopyFactoryCloseInstructions = None):
        """Deletes a portfolio strategy member. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/removePortfolioStrategyMember/

        Args:
            portfolio_id: Portfolio strategy id.
            strategy_id: Id of the strategy to delete member for.
            close_instructions: Portfolio close instructions.

        Returns:
            A coroutine resolving when portfolio strategy member is removed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('remove_portfolio_strategy_member')
        opts = {
            'url': f"/users/current/configuration/portfolio-strategies/{portfolio_id}"
                   f"/members/{strategy_id}",
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        if close_instructions is not None:
            format_request(close_instructions)
            opts['body'] = close_instructions
        return await self._domainClient.request_copyfactory(opts)

    async def get_subscribers(self, include_removed: bool = None, limit: int = None,
                              offset: int = None) -> 'List[CopyFactorySubscriber]':
        """Returns CopyFactory subscribers the user has configured. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/getSubscribers/

        Args:
            include_removed: Flag instructing to include removed subscribers in results.
            limit: Pagination limit.
            offset: Pagination offset.

        Returns:
            A coroutine resolving with subscribers found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_subscribers')
        qs = {}
        if include_removed is not None:
            qs['includeRemoved'] = include_removed
        if limit is not None:
            qs['limit'] = limit
        if offset is not None:
            qs['offset'] = offset
        opts = {
            'url': f"/users/current/configuration/subscribers",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            },
            'params': qs
        }
        result = await self._domainClient.request_copyfactory(opts, True)
        convert_iso_time_to_date(result)
        return result

    async def get_subscriber(self, subscriber_id: str) -> CopyFactorySubscriber:
        """Returns CopyFactory subscriber by id. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/getSubscriber/

        Args:
            subscriber_id: Subscriber id.

        Returns:
            A coroutine resolving with subscriber configuration found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_subscriber')
        opts = {
            'url': f"/users/current/configuration/subscribers/{subscriber_id}",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        subscriber = await self._domainClient.request_copyfactory(opts)
        convert_iso_time_to_date(subscriber)
        return subscriber

    async def update_subscriber(self, subscriber_id: str, subscriber: CopyFactorySubscriberUpdate):
        """Updates CopyFactory subscriber configuration. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/updateSubscriber/

        Args:
            subscriber_id: Subscriber id.
            subscriber: Subscriber update.

        Returns:
            A coroutine resolving when subscriber configuration is updated.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('update_subscriber')
        payload = deepcopy(subscriber)
        format_request(payload)
        opts = {
            'url': f"/users/current/configuration/subscribers/{subscriber_id}",
            'method': 'PUT',
            'headers': {
                'auth-token': self._token
            },
            'body': payload
        }
        return await self._domainClient.request_copyfactory(opts)

    async def remove_subscriber(self, subscriber_id: str, close_instructions: CopyFactoryCloseInstructions = None):
        """Deletes subscriber configuration. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/removeSubscriber/

        Args:
            subscriber_id: Subscriber id.
            close_instructions: Subscriber close instructions.

        Returns:
            A coroutine resolving when subscriber configuration is removed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('remove_subscriber')
        opts = {
            'url': f"/users/current/configuration/subscribers/{subscriber_id}",
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        if close_instructions is not None:
            format_request(close_instructions)
            opts['body'] = close_instructions
        return await self._domainClient.request_copyfactory(opts)

    async def remove_subscription(self, subscriber_id: str, strategy_id: str,
                                  close_instructions: CopyFactoryCloseInstructions = None):
        """Deletes a subscription of subscriber to a strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/configuration/removeSubscription/

        Args:
            subscriber_id: Subscriber id.
            strategy_id: Strategy id.
            close_instructions: Subscriber close instructions.

        Returns:
            A coroutine resolving when subscription is removed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('remove_subscription')
        opts = {
            'url': f"/users/current/configuration/subscribers/{subscriber_id}/subscriptions/{strategy_id}",
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        if close_instructions is not None:
            format_request(close_instructions)
            opts['body'] = close_instructions
        return await self._domainClient.request_copyfactory(opts)
