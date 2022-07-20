from ..clients.metaApi.metatraderAccount_client import MetatraderAccountClient, MetatraderAccountDto, \
    MetatraderAccountUpdateDto, AccountConnection
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from ..clients.timeoutException import TimeoutException
from .streamingMetaApiConnection import StreamingMetaApiConnection
from .metatraderAccountModel import MetatraderAccountModel
from ..metaApi.filesystemHistoryDatabase import FilesystemHistoryDatabase
from .historyStorage import HistoryStorage
from .connectionRegistryModel import ConnectionRegistryModel
from .expertAdvisor import ExpertAdvisorClient, ExpertAdvisor, NewExpertAdvisorDto
from ..clients.metaApi.historicalMarketData_client import HistoricalMarketDataClient
from ..clients.errorHandler import ValidationException
from .models import MetatraderCandle, MetatraderTick
from datetime import datetime, timedelta
from typing import List, Dict
from .rpcMetaApiConnection import RpcMetaApiConnection
import asyncio


class MetatraderAccount(MetatraderAccountModel):
    """Implements a MetaTrader account entity"""

    def __init__(self, data: MetatraderAccountDto, metatrader_account_client: MetatraderAccountClient,
                 meta_api_websocket_client: MetaApiWebsocketClient, connection_registry: ConnectionRegistryModel,
                 expert_advisor_client: ExpertAdvisorClient, historical_market_data_client: HistoricalMarketDataClient,
                 application: str):
        """Inits a MetaTrader account entity.

        Args:
            data: MetaTrader account data.
            metatrader_account_client: MetaTrader account REST API client.
            meta_api_websocket_client: MetaApi websocket client.
            connection_registry: Metatrader account connection registry.
            expert_advisor_client: Expert advisor REST API client.
            historical_market_data_client: Historical market data HTTP API client.
            application: Application name.
        """
        self._data = data
        self._metatraderAccountClient = metatrader_account_client
        self._metaApiWebsocketClient = meta_api_websocket_client
        self._connectionRegistry = connection_registry
        self._expertAdvisorClient = expert_advisor_client
        self._historicalMarketDataClient = historical_market_data_client
        self._application = application

    @property
    def id(self) -> str:
        """Returns account id.

        Returns:
            Account id.
        """
        return self._data['_id']

    @property
    def name(self) -> str:
        """Returns account name.

        Returns:
            Account name.
        """
        return self._data['name']

    @property
    def type(self) -> str:
        """Returns account type. Possible values are cloud, cloud-g1, cloud-g2, and self-hosted.

        Returns:
            Account type.
        """
        return self._data['type']

    @property
    def login(self) -> str:
        """Returns account login.

        Returns:
            Account login.
        """
        return self._data['login']

    @property
    def server(self) -> str:
        """Returns MetaTrader server which hosts the account.

        Returns:
            MetaTrader server which hosts the account.
        """
        return self._data['server']

    @property
    def provisioning_profile_id(self) -> str:
        """Returns id of the account's provisioning profile.

        Returns:
            Id of the account's provisioning profile.
        """
        return self._data['provisioningProfileId'] if 'provisioningProfileId' in self._data else None

    @property
    def application(self) -> str:
        """Returns application name to connect the account to. Currently allowed values are MetaApi and AgiliumTrade.

        Returns:
            Application name to connect the account to.
        """
        return self._data['application']

    @property
    def magic(self) -> int:
        """Returns MetaTrader magic to place trades using.

        Returns:
            MetaTrader magic to place trades using.
        """
        return self._data['magic']

    @property
    def state(self) -> str:
        """Returns account deployment state. One of CREATED, DEPLOYING, DEPLOYED, UNDEPLOYING, UNDEPLOYED, DELETING

        Returns:
            Account deployment state.
        """
        return self._data['state']

    @property
    def connection_status(self) -> str:
        """Returns terminal & broker connection status, one of CONNECTED, DISCONNECTED, DISCONNECTED_FROM_BROKER

        Returns:
            Terminal & broker connection status.
        """
        return self._data['connectionStatus']

    @property
    def access_token(self) -> str:
        """Returns authorization access token to be used for accessing single account data.
        Intended to be used in browser API.

        Returns:
            Authorization token.
        """
        return self._data['accessToken']

    @property
    def manual_trades(self) -> bool:
        """Returns flag indicating if trades should be placed as manual trades on this account.

        Returns:
            Flag indicating if trades should be placed as manual trades on this account.
        """
        return 'manualTrades' in self._data and self._data['manualTrades']

    @property
    def metadata(self) -> Dict:
        """Returns extra information which can be stored together with your account.

        Returns:
            Extra information which can be stored together with your account.
        """
        return self._data['metadata'] if 'metadata' in self._data else None

    @property
    def tags(self) -> List[str]:
        """Returns user-defined account tags.

        Returns:
            User-defined account tag.
        """
        return self._data['tags'] if 'tags' in self._data else None

    @property
    def copy_factory_roles(self) -> List[str]:
        """Returns account roles for CopyFactory2 application.

        Returns:
            Account roles for CopyFactory2 application.
        """
        return self._data['copyFactoryRoles'] if 'copyFactoryRoles' in self._data else None

    @property
    def resource_slots(self) -> int:
        """Returns number of resource slots to allocate to account. Allocating extra resource slots
        results in better account performance under load which is useful for some applications. E.g. if you have many
        accounts copying the same strategy via CooyFactory API, then you can increase resourceSlots to get a lower
        trade copying latency. Please note that allocating extra resource slots is a paid option. Please note that high
        reliability accounts use redundant infrastructure, so that each resource slot for a high reliability account
        is billed as 2 standard resource slots. Default is 1.

        Returns:
            Number of resource slots to allocate to account.
        """
        return self._data['resourceSlots'] if 'resourceSlots' in self._data else None

    @property
    def copyfactory_resource_slots(self) -> int:
        """Returns the number of CopyFactory 2 resource slots to allocate to account. Allocating extra resource slots
        results in lower trade copying latency. Please note that allocating extra resource slots is a paid option.
        Please also note that CopyFactory 2 uses redundant infrastructure so that each CopyFactory resource slot is
        billed as 2 standard resource slots. You will be billed for CopyFactory 2 resource slots only if you have
        added your account to CopyFactory 2 by specifying copyFactoryRoles field. Default is 1.

        Returns:
            Number of CopyFactory 2 resource slots to allocate to account.
        """
        return self._data['copyFactoryResourceSlots'] if 'copyFactoryResourceSlots' in self._data else None

    @property
    def base_currency(self) -> str:
        """Returns 3-character ISO currency code of the account base currency. Default value is USD. The setting is to
        be used for copy trading accounts which use national currencies only, such as some Brazilian brokers. You
        should not alter this setting unless you understand what you are doing.

        Returns:
            3-character ISO currency code of the account base currency.
        """
        return self._data['baseCurrency'] if 'baseCurrency' in self._data else None

    @property
    def reliability(self) -> str:
        """Returns reliability value. Possible values are regular and high.

        Returns:
            Reliability value.
        """
        return self._data['reliability']

    @property
    def version(self) -> int:
        """Returns version value. Possible values are 4 and 5.

        Returns:
            Account version value.
        """
        return self._data['version']

    @property
    def region(self) -> str:
        """Returns account region.

        Returns:
            Account region value.
        """
        return self._data['region']

    @property
    def connections(self) -> List[AccountConnection]:
        """Returns active account connections.

        Returns:
            Active account connections.
        """
        return self._data['connections']

    @property
    def risk_management_api_enabled(self) -> bool:
        """Returns flag indicating that risk management API is enabled on account. Default is false.

        Returns:
            Flag indicating that risk management API is enabled on account.
        """
        return self._data['riskManagementApiEnabled']

    @property
    def user_id(self) -> str:
        """Returns user id.

        Returns:
            User id.
        """
        return self._data['userId']

    async def reload(self):
        """Reloads MetaTrader account from API.

        Returns:
            A coroutine resolving when MetaTrader account is updated.
        """
        self._data = await self._metatraderAccountClient.get_account(self.id)

    async def remove(self):
        """Removes MetaTrader account. Cloud account transitions to DELETING state.
        It takes some time for an account to be eventually deleted. Self-hosted account is deleted immediately.

        Returns:
            A coroutine resolving when account is scheduled for deletion.
        """
        self._connectionRegistry.remove(self.id)
        await self._metatraderAccountClient.delete_account(self.id)
        file_manager = FilesystemHistoryDatabase.get_instance()
        await file_manager.clear(self.id, self._application)
        if self.type != 'self-hosted':
            try:
                await self.reload()
            except Exception as err:
                if err.__class__.__name__ != 'NotFoundException':
                    raise err

    async def deploy(self):
        """Schedules account for deployment. It takes some time for API server to be started and account to reach the
        DEPLOYED state.

        Returns:
            A coroutine resolving when account is scheduled for deployment.
        """
        await self._metatraderAccountClient.deploy_account(self.id)
        await self.reload()

    async def undeploy(self):
        """Schedules account for undeployment. It takes some time for API server to be stopped and account to reach the
        UNDEPLOYED state.

        Returns:
            A coroutine resolving when account is scheduled for undeployment.
        """
        self._connectionRegistry.remove(self.id)
        await self._metatraderAccountClient.undeploy_account(self.id)
        await self.reload()

    async def redeploy(self):
        """Schedules account for redeployment. It takes some time for API server to be restarted and account to reach
        the DEPLOYED state.

        Returns:
            A coroutine resolving when account is scheduled for redeployment.
        """
        await self._metatraderAccountClient.redeploy_account(self.id)
        await self.reload()

    async def increase_reliability(self):
        """Increases MetaTrader account reliability. The account will be temporary stopped to perform this action.

        Returns:
            A coroutine resolving when account reliability is increased.
        """
        await self._metatraderAccountClient.increase_reliability(self.id)
        await self.reload()

    async def wait_deployed(self, timeout_in_seconds=300, interval_in_milliseconds=1000):
        """Waits until API server has finished deployment and account reached the DEPLOYED state.

        Args:
            timeout_in_seconds: Wait timeout in seconds, default is 5m.
            interval_in_milliseconds: Interval between account reloads while waiting for a change, default is 1s.

        Returns:
            A coroutine which resolves when account is deployed.

        Raises:
            TimeoutException: If account has not reached the DEPLOYED state within timeout allowed.
        """
        start_time = datetime.now()
        await self.reload()
        while self.state != 'DEPLOYED' and (start_time + timedelta(seconds=timeout_in_seconds) > datetime.now()):
            await self._delay(interval_in_milliseconds)
            await self.reload()
        if self.state != 'DEPLOYED':
            raise TimeoutException('Timed out waiting for account ' + self.id + ' to be deployed')

    async def wait_undeployed(self, timeout_in_seconds=300, interval_in_milliseconds=1000):
        """Waits until API server has finished undeployment and account reached the UNDEPLOYED state.

        Args:
            timeout_in_seconds: Wait timeout in seconds, default is 5m.
            interval_in_milliseconds: Interval between account reloads while waiting for a change, default is 1s.

        Returns:
            A coroutine which resolves when account is undeployed.

        Raises:
            TimeoutException: If account have not reached the UNDEPLOYED state within timeout allowed.
        """
        start_time = datetime.now()
        await self.reload()
        while self.state != 'UNDEPLOYED' and (start_time + timedelta(seconds=timeout_in_seconds) > datetime.now()):
            await self._delay(interval_in_milliseconds)
            await self.reload()
        if self.state != 'UNDEPLOYED':
            raise TimeoutException('Timed out waiting for account ' + self.id + ' to be undeployed')

    async def wait_removed(self, timeout_in_seconds=300, interval_in_milliseconds=1000):
        """Waits until account has been deleted.

        Args:
            timeout_in_seconds: Wait timeout in seconds, default is 5m.
            interval_in_milliseconds: Interval between account reloads while waiting for a change, default is 1s.

        Returns:
            A coroutine which resolves when account is deleted.

        Raises:
            TimeoutException: If account was not deleted within timeout allowed.
        """
        start_time = datetime.now()
        try:
            await self.reload()
            while (start_time + timedelta(seconds=timeout_in_seconds)) > datetime.now():
                await self._delay(interval_in_milliseconds)
                await self.reload()
            raise TimeoutException('Timed out waiting for account ' + self.id + ' to be deleted')
        except Exception as err:
            if err.__class__.__name__ == 'NotFoundException':
                return
            else:
                raise err

    async def wait_connected(self, timeout_in_seconds=300, interval_in_milliseconds=1000):
        """Waits until API server has connected to the terminal and terminal has connected to the broker.

        Args:
            timeout_in_seconds: Wait timeout in seconds, default is 5m
            interval_in_milliseconds: Interval between account reloads while waiting for a change, default is 1s.

        Returns:
            A coroutine which resolves when API server is connected to the broker.

        Raises:
            TimeoutException: If account has not connected to the broker within timeout allowed.
        """
        start_time = datetime.now()
        await self.reload()
        while self.connection_status != 'CONNECTED' and (start_time +
                                                         timedelta(seconds=timeout_in_seconds)) > datetime.now():
            await self._delay(interval_in_milliseconds)
            await self.reload()
        if self.connection_status != 'CONNECTED':
            raise TimeoutException('Timed out waiting for account ' + self.id + ' to connect to the broker')

    def get_streaming_connection(self, history_storage: HistoryStorage = None,
                                 history_start_time: datetime = None) -> StreamingMetaApiConnection:
        """Connects to MetaApi via streaming connection.

        Args:
            history_storage: Optional history storage.
            history_start_time: History start time. Used for tests.

        Returns:
            MetaApi connection.
        """
        if self._metaApiWebsocketClient.region and self._metaApiWebsocketClient.region != self.region:
            raise ValidationException(f'Account {self.id} is not on specified region '
                                      f'{self._metaApiWebsocketClient.region}')
        return self._connectionRegistry.connect(self, history_storage, history_start_time)

    def get_rpc_connection(self) -> RpcMetaApiConnection:
        """Connects to MetaApi via RPC connection.

        Returns:
            MetaApi connection.
        """
        if self._metaApiWebsocketClient.region and self._metaApiWebsocketClient.region != self.region:
            raise ValidationException(f'Account {self.id} is not on specified region '
                                      f'{self._metaApiWebsocketClient.region}')
        return RpcMetaApiConnection(self._metaApiWebsocketClient, self)

    async def update(self, account: MetatraderAccountUpdateDto):
        """Updates MetaTrader account data.

        Args:
            account: MetaTrader account update.

        Returns:
            A coroutine resolving when account is updated.
        """
        await self._metatraderAccountClient.update_account(self.id, account)
        await self.reload()

    async def get_expert_advisors(self) -> List[ExpertAdvisor]:
        """Retrieves expert advisors of current account.

        Returns:
            A coroutine resolving with an array of expert advisor entities.
        """
        self._check_expert_advisor_allowed()
        expert_advisors = await self._expertAdvisorClient.get_expert_advisors(self.id)
        return list(map(lambda e: ExpertAdvisor(e, self.id, self._expertAdvisorClient), expert_advisors))

    async def get_expert_advisor(self, expert_id: str) -> ExpertAdvisor:
        """Retrieves a expert advisor of current account by id.

        Args:
            expert_id: Expert advisor id.

        Returns:
            A coroutine resolving with expert advisor entity.
        """
        self._check_expert_advisor_allowed()
        expert_advisor = await self._expertAdvisorClient.get_expert_advisor(self.id, expert_id)
        return ExpertAdvisor(expert_advisor, self.id, self._expertAdvisorClient)

    async def create_expert_advisor(self, expert_id: str, expert: NewExpertAdvisorDto) -> ExpertAdvisor:
        """Creates an expert advisor.

        Args:
            expert_id: Expert advisor id.
            expert: Expert advisor data.

        Returns:
            A coroutine resolving with expert advisor entity.
        """
        self._check_expert_advisor_allowed()
        await self._expertAdvisorClient.update_expert_advisor(self.id, expert_id, expert)
        return await self.get_expert_advisor(expert_id)

    async def get_historical_candles(self, symbol: str, timeframe: str, start_time: datetime = None,
                                     limit: int = None) -> List[MetatraderCandle]:
        """Returns historical candles for a specific symbol and timeframe from a MetaTrader account.
        See https://metaapi.cloud/docs/client/restApi/api/retrieveMarketData/readHistoricalCandles/

        Args:
            symbol: Symbol to retrieve candles for (e.g. a currency pair or an index).
            timeframe: Defines the timeframe according to which the candles must be generated. Allowed values
            for MT5 are 1m, 2m, 3m, 4m, 5m, 6m, 10m, 12m, 15m, 20m, 30m, 1h, 2h, 3h, 4h, 6h, 8h, 12h, 1d, 1w, 1mn.
            Allowed values for MT4 are 1m, 5m, 15m 30m, 1h, 4h, 1d, 1w, 1mn.
            start_time: Time to start loading candles from. Note that candles are loaded in backwards direction, so
            this should be the latest time. Leave empty to request latest candles.
            limit: Maximum number of candles to retrieve. Must be less or equal to 1000.

        Returns:
            A coroutine resolving with historical candles downloaded.
        """
        return await self._historicalMarketDataClient.get_historical_candles(self.id, self.region, symbol, timeframe,
                                                                             start_time, limit)

    async def get_historical_ticks(self, symbol: str, start_time: datetime = None, offset: int = None,
                                   limit: int = None) -> List[MetatraderTick]:
        """Returns historical ticks for a specific symbol from a MetaTrader account.
        See https://metaapi.cloud/docs/client/restApi/api/retrieveMarketData/readHistoricalTicks/

        Args:
            symbol: Symbol to retrieve ticks for (e.g. a currency pair or an index).
            start_time: Time to start loading ticks from. Note that ticks are loaded in backwards direction, so
            this should be the latest time. Leave empty to request latest ticks.
            offset: Number of ticks to skip (you can use it to avoid requesting ticks from previous request twice)
            limit: Maximum number of ticks to retrieve. Must be less or equal to 1000.

        Returns:
            A coroutine resolving with historical ticks downloaded.
        """
        return await self._historicalMarketDataClient.get_historical_ticks(self.id, self.region, symbol, start_time,
                                                                           offset, limit)

    def _check_expert_advisor_allowed(self):
        if self.version != 4 or self.type != 'cloud-g1':
            raise ValidationException('Custom expert advisor is available only for MT4 G1 accounts')

    async def _delay(self, timeout_in_milliseconds):
        await asyncio.sleep(timeout_in_milliseconds / 1000)
