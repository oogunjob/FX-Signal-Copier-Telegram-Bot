from ..clients.metaApi.metatraderAccount_client import MetatraderAccountUpdateDto
from .historyStorage import HistoryStorage
from typing import Dict, List
from .expertAdvisor import ExpertAdvisor, NewExpertAdvisorDto
from .models import MetatraderCandle, MetatraderTick
from abc import ABC, abstractmethod
from datetime import datetime


class MetatraderAccountModel(ABC):
    """Defines interface for a MetaTrader account class."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Returns account id.

        Returns:
            Account id.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns account name.

        Returns:
            Account name.
        """

    @property
    @abstractmethod
    def type(self) -> str:
        """Returns account type. Possible values are cloud and self-hosted.

        Returns:
            Account type.
        """

    @property
    @abstractmethod
    def login(self) -> str:
        """Returns account login.

        Returns:
            Account login.
        """

    @property
    @abstractmethod
    def server(self) -> str:
        """Returns MetaTrader server which hosts the account.

        Returns:
            MetaTrader server which hosts the account.
        """

    @property
    @abstractmethod
    def provisioning_profile_id(self):
        """Returns id of the account's provisioning profile.

        Returns:
            Id of the account's provisioning profile.
        """

    @property
    @abstractmethod
    def application(self):
        """Returns application name to connect the account to. Currently allowed values are MetaApi and AgiliumTrade.

        Returns:
            Application name to connect the account to.
        """

    @property
    @abstractmethod
    def magic(self):
        """Returns MetaTrader magic to place trades using.

        Returns:
            MetaTrader magic to place trades using.
        """

    @property
    @abstractmethod
    def state(self):
        """Returns account deployment state. One of CREATED, DEPLOYING, DEPLOYED, UNDEPLOYING, UNDEPLOYED, DELETING

        Returns:
            Account deployment state.
        """

    @property
    @abstractmethod
    def connection_status(self):
        """Returns terminal & broker connection status, one of CONNECTED, DISCONNECTED, DISCONNECTED_FROM_BROKER

        Returns:
            Terminal & broker connection status.
        """

    @property
    @abstractmethod
    def access_token(self):
        """Returns authorization access token to be used for accessing single account data.
        Intended to be used in browser API.

        Returns:
            Authorization token.
        """

    @property
    @abstractmethod
    def manual_trades(self) -> bool:
        """Returns flag indicating if trades should be placed as manual trades on this account.

        Returns:
            Flag indicating if trades should be placed as manual trades on this account.
        """

    @property
    @abstractmethod
    def metadata(self) -> Dict:
        """Returns extra information which can be stored together with your account.

        Returns:
            Extra information which can be stored together with your account.
        """

    @property
    @abstractmethod
    def tags(self) -> List[str]:
        """Returns user-defined account tags.

        Returns:
            User-defined account tag.
        """

    @property
    @abstractmethod
    def copy_factory_roles(self) -> List[str]:
        """Returns account roles for CopyFactory2 application.

        Returns:
            Account roles for CopyFactory2 application.
        """

    @property
    @abstractmethod
    def resource_slots(self) -> int:
        """Returns number of resource slots to allocate to account. Allocating extra resource slots
        results in better account performance under load which is useful for some applications. E.g. if you have many
        accounts copying the same strategy via CooyFactory API, then you can increase resourceSlots to get a lower
        trade copying latency. Please note that allocating extra resource slots is a paid option. Default is 1

        Returns:
            Number of resource slots to allocate to account.
        """

    @property
    @abstractmethod
    def base_currency(self) -> str:
        """Returns 3-character ISO currency code of the account base currency. Default value is USD. The setting is to
        be used for copy trading accounts which use national currencies only, such as some Brazilian brokers. You
        should not alter this setting unless you understand what you are doing.

        Returns:
            3-character ISO currency code of the account base currency.
        """

    @property
    @abstractmethod
    def reliability(self) -> str:
        """Returns reliability value. Possible values are regular and high.

        Returns:
            Reliability value.
        """

    @property
    @abstractmethod
    def version(self) -> int:
        """Returns version value. Possible values are 4 and 5.

        Returns:
            Account version value.
        """

    @property
    @abstractmethod
    def region(self) -> str:
        """Returns account region.

        Returns:
            Account region value.
        """

    @abstractmethod
    async def reload(self):
        """Reloads MetaTrader account from API.

        Returns:
            A coroutine resolving when MetaTrader account is updated.
        """

    @abstractmethod
    async def remove(self):
        """Removes MetaTrader account. Cloud account transitions to DELETING state.
        It takes some time for an account to be eventually deleted. Self-hosted account is deleted immediately.

        Returns:
            A coroutine resolving when account is scheduled for deletion.
        """

    @abstractmethod
    async def deploy(self):
        """Schedules account for deployment. It takes some time for API server to be started and account to reach the
        DEPLOYED state.

        Returns:
            A coroutine resolving when account is scheduled for deployment.
        """

    @abstractmethod
    async def undeploy(self):
        """Schedules account for undeployment. It takes some time for API server to be stopped and account to reach the
        UNDEPLOYED state.

        Returns:
            A coroutine resolving when account is scheduled for undeployment.
        """

    @abstractmethod
    async def redeploy(self):
        """Schedules account for redeployment. It takes some time for API server to be restarted and account to reach
        the DEPLOYED state.

        Returns:
            A coroutine resolving when account is scheduled for redeployment.
        """

    @abstractmethod
    async def increase_reliability(self):
        """Increases MetaTrader account reliability. The account will be temporary stopped to perform this action.

        Returns:
            A coroutine resolving when account reliability is increased.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def wait_connected(self, timeout_in_seconds=300, interval_in_milliseconds=1000):
        """Waits until API server has connected to the terminal and terminal has connected to the broker.

        Args:
            timeout_in_seconds: Wait timeout in seconds, default is 5m.
            interval_in_milliseconds: Interval between account reloads while waiting for a change, default is 1s.

        Returns:
            A coroutine which resolves when API server is connected to the broker.

        Raises:
            TimeoutException: If account has not connected to the broker within timeout allowed.
        """

    @abstractmethod
    async def get_streaming_connection(self, history_storage: HistoryStorage, history_start_time: datetime = None):
        """Connects to MetaApi via streaming connection.

        Args:
            history_storage: Optional history storage.
            history_start_time: History start time. Used for tests.

        Returns:
            MetaApi connection.
        """

    @abstractmethod
    async def get_rpc_connection(self):
        """Connects to MetaApi via RPC connection.

        Returns:
            MetaApi connection.
        """

    @abstractmethod
    async def update(self, account: MetatraderAccountUpdateDto):
        """Updates MetaTrader account data.

        Args:
            account: MetaTrader account update.

        Returns:
            A coroutine resolving when account is updated.
        """

    @abstractmethod
    async def get_expert_advisors(self) -> List[ExpertAdvisor]:
        """Retrieves expert advisors of current account.

        Returns:
            A coroutine resolving with an array of expert advisor entities.
        """

    @abstractmethod
    async def get_expert_advisor(self, expert_id: str) -> ExpertAdvisor:
        """Retrieves a expert advisor of current account by id.

        Args:
            expert_id: Expert advisor id.

        Returns:
            A coroutine resolving with expert advisor entity.
        """

    @abstractmethod
    async def create_expert_advisor(self, expert_id: str, expert: NewExpertAdvisorDto) -> ExpertAdvisor:
        """Creates an expert advisor.

        Args:
            expert_id: Expert advisor id.
            expert: Expert advisor data.

        Returns:
            A coroutine resolving with expert advisor entity.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def _delay(self, timeout_in_milliseconds):
        pass
