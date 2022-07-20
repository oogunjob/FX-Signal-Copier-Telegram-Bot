from .metatraderAccount import MetatraderAccount
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from ..clients.metaApi.metatraderAccount_client import MetatraderAccountClient, NewMetatraderAccountDto, AccountsFilter
from .connectionRegistryModel import ConnectionRegistryModel
from ..clients.metaApi.expertAdvisor_client import ExpertAdvisorClient
from ..clients.metaApi.historicalMarketData_client import HistoricalMarketDataClient
from typing import List


class MetatraderAccountApi:
    """Exposes MetaTrader account API logic to the consumers."""

    def __init__(self, metatrader_account_client: MetatraderAccountClient,
                 meta_api_websocket_client: MetaApiWebsocketClient, connection_registry: ConnectionRegistryModel,
                 expert_advisor_client: ExpertAdvisorClient, historical_market_data_client: HistoricalMarketDataClient,
                 application: str):
        """Inits a MetaTrader account API instance.

        Args:
            metatrader_account_client: MetaTrader account REST API client.
            meta_api_websocket_client: MetaApi websocket client.
            connection_registry: MetaTrader account connection registry.
            expert_advisor_client: Expert advisor REST API client.
            historical_market_data_client: Historical market data HTTP API client.
            application: Application name.
        """
        self._metatraderAccountClient = metatrader_account_client
        self._metaApiWebsocketClient = meta_api_websocket_client
        self._connectionRegistry = connection_registry
        self._expertAdvisorClient = expert_advisor_client
        self._historicalMarketDataClient = historical_market_data_client
        self._application = application

    async def get_accounts(self, accounts_filter: AccountsFilter = None) -> List[MetatraderAccount]:
        """Retrieves MetaTrader accounts.

        Args:
            accounts_filter: Optional filter.

        Returns:
            A coroutine resolving with an array of MetaTrader account entities.
        """
        accounts = await self._metatraderAccountClient.get_accounts(accounts_filter or {})
        if 'items' in accounts:
            accounts = accounts['items']
        return list(map(lambda account: MetatraderAccount(account, self._metatraderAccountClient,
                                                          self._metaApiWebsocketClient, self._connectionRegistry,
                                                          self._expertAdvisorClient, self._historicalMarketDataClient,
                                                          self._application),
                        accounts))

    async def get_account(self, account_id) -> MetatraderAccount:
        """Retrieves a MetaTrader account by id.

        Args:
            account_id: MetaTrader account id.

        Returns:
            A coroutine resolving with MetaTrader account entity.
        """
        account = await self._metatraderAccountClient.get_account(account_id)
        return MetatraderAccount(account, self._metatraderAccountClient, self._metaApiWebsocketClient,
                                 self._connectionRegistry, self._expertAdvisorClient, self._historicalMarketDataClient,
                                 self._application)

    async def get_account_by_token(self) -> MetatraderAccount:
        """Retrieves a MetaTrader account by token.

        Returns:
            A coroutine resolving with MetaTrader account entity.
        """
        account = await self._metatraderAccountClient.get_account_by_token()
        return MetatraderAccount(account, self._metatraderAccountClient, self._metaApiWebsocketClient,
                                 self._connectionRegistry, self._expertAdvisorClient, self._historicalMarketDataClient,
                                 self._application)

    async def create_account(self, account: NewMetatraderAccountDto) -> MetatraderAccount:
        """Creates a MetaTrader account.

        Args:
            account: MetaTrader account data.

        Returns:
            A coroutine resolving with MetaTrader account entity.
        """
        id = await self._metatraderAccountClient.create_account(account)
        return await self.get_account(id['id'])
