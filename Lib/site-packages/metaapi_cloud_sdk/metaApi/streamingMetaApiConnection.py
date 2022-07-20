from .metaApiConnection import MetaApiConnection
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from ..clients.metaApi.clientApi_client import ClientApiClient
from .terminalState import TerminalState
from .connectionHealthMonitor import ConnectionHealthMonitor
from .memoryHistoryStorage import MemoryHistoryStorage
from .metatraderAccountModel import MetatraderAccountModel
from .connectionRegistryModel import ConnectionRegistryModel
from .historyStorage import HistoryStorage
from ..clients.timeoutException import TimeoutException
from .models import random_id, string_format_error, MarketDataSubscription, MarketDataUnsubscription, \
    MetatraderSymbolSpecification
from ..clients.errorHandler import ValidationException
from ..clients.optionsValidator import OptionsValidator
from datetime import datetime, timedelta
from typing import Coroutine, List, Optional, Dict, Union, Callable
from typing_extensions import TypedDict
from functools import reduce
import pytz
import asyncio
from random import uniform
from ..logger import LoggerManager


class MetaApiConnectionDict(TypedDict, total=False):
    instanceIndex: int
    ordersSynchronized: dict
    dealsSynchronized: dict
    shouldSynchronize: Optional[str]
    synchronizationRetryIntervalInSeconds: float
    synchronized: bool
    lastDisconnectedSynchronizationId: Optional[str]
    lastSynchronizationId: Optional[str]
    disconnected: bool
    synchronizationTimeout: Union[asyncio.Task, None]
    ensureSynchronizeTimeout: Union[asyncio.Task, None]


class SynchronizationOptions(TypedDict, total=False):
    instanceIndex: Optional[int]
    """Index of an account instance to ensure synchronization on, default is to wait for the first instance to
    synchronize."""
    applicationPattern: Optional[str]
    """Application regular expression pattern, default is .*"""
    synchronizationId: Optional[str]
    """synchronization id, last synchronization request id will be used by default"""
    timeoutInSeconds: Optional[float]
    """Wait timeout in seconds, default is 5m."""
    intervalInMilliseconds: Optional[float]
    """Interval between account reloads while waiting for a change, default is 1s."""


class StreamingMetaApiConnection(MetaApiConnection):
    """Exposes MetaApi MetaTrader streaming API connection to consumers."""

    def __init__(self, websocket_client: MetaApiWebsocketClient, client_api_client: ClientApiClient,
                 account: MetatraderAccountModel, history_storage: HistoryStorage or None,
                 connection_registry: ConnectionRegistryModel, history_start_time: datetime = None,
                 refresh_subscriptions_opts: dict = None):
        """Inits MetaApi MetaTrader streaming Api connection.

        Args:
            websocket_client: MetaApi websocket client.
            client_api_client: Client api client.
            account: MetaTrader account id to connect to.
            history_storage: Local terminal history storage. By default an instance of MemoryHistoryStorage
            will be used.
            history_start_time: History start sync time.
            refresh_subscriptions_opts: Subscriptions refresh options.
        """
        super().__init__(websocket_client, account)
        if refresh_subscriptions_opts is None:
            refresh_subscriptions_opts = {}
        validator = OptionsValidator()
        self._minSubscriptionRefreshInterval = validator.validate_non_zero(
            refresh_subscriptions_opts['minDelayInSeconds'] if 'minDelayInSeconds' in refresh_subscriptions_opts
            else None, 1, 'refreshSubscriptionsOpts.minDelayInSeconds')
        self._maxSubscriptionRefreshInterval = validator.validate_non_zero(
            refresh_subscriptions_opts['maxDelayInSeconds'] if 'maxDelayInSeconds' in refresh_subscriptions_opts
            else None, 600, 'refreshSubscriptionsOpts.maxDelayInSeconds')
        self._closed = False
        self._opened = False
        self._connection_registry = connection_registry
        self._history_start_time = history_start_time
        self._terminalState = TerminalState(self._account.id, client_api_client)
        self._historyStorage = history_storage or MemoryHistoryStorage()
        self._healthMonitor = ConnectionHealthMonitor(self)
        self._websocketClient.add_synchronization_listener(account.id, self)
        self._websocketClient.add_synchronization_listener(account.id, self._terminalState)
        self._websocketClient.add_synchronization_listener(account.id, self._historyStorage)
        self._websocketClient.add_synchronization_listener(account.id, self._healthMonitor)
        self._websocketClient.add_reconnect_listener(self, account.id)
        self._subscriptions = {}
        self._stateByInstanceIndex = {}
        self._refreshMarketDataSubscriptionSessions = {}
        self._refreshMarketDataSubscriptionTimeouts = {}
        self._synchronizationListeners = []
        self._logger = LoggerManager.get_logger('MetaApiConnection')

    async def connect(self):
        """Opens the connection. Can only be called the first time, next calls will be ignored.

        Returns:
            A coroutine resolving when the connection is opened
        """
        if not self._opened:
            self._logger.debug(f'{self._account.id}: Opening connection')
            self._opened = True
            try:
                await self.initialize()
                await self.subscribe()
            except Exception as err:
                await self.close()
                raise err

    def remove_application(self):
        """Clears the order and transaction history of a specified application and removes application (see
        https://metaapi.cloud/docs/client/websocket/api/removeApplication/).

        Returns:
            A coroutine resolving when the history is cleared and application is removed.
        """
        self._check_is_connection_active()
        asyncio.create_task(self._historyStorage.clear())
        return self._websocketClient.remove_application(self._account.id)

    async def synchronize(self, instance_index: str) -> Coroutine:
        """Requests the terminal to start synchronization process.
        (see https://metaapi.cloud/docs/client/websocket/synchronizing/synchronize/).

        Args:
            instance_index: Instance index.

        Returns:
            A coroutine which resolves when synchronization started.
        """
        self._check_is_connection_active()
        instance = self.get_instance_number(instance_index)
        host = self.get_host_name(instance_index)
        starting_history_order_time = \
            datetime.utcfromtimestamp(max(((self._history_start_time and self._history_start_time.timestamp()) or 0),
                                      (await self._historyStorage.last_history_order_time(instance))
                                          .timestamp())).replace(tzinfo=pytz.UTC)
        starting_deal_time = \
            datetime.utcfromtimestamp(max(((self._history_start_time and self._history_start_time.timestamp()) or 0),
                                      (await self._historyStorage.last_deal_time(instance)).timestamp()))\
            .replace(tzinfo=pytz.UTC)
        synchronization_id = random_id()
        self._get_state(instance_index)['lastSynchronizationId'] = synchronization_id
        self._logger.debug(f'{self._account.id}:{instance_index}: initiating synchronization {synchronization_id}')

        async def get_hashes():
            return await self.terminal_state.get_hashes(self._account.type, instance_index)

        return await self._websocketClient.synchronize(
            self._account.id, instance, host, synchronization_id, starting_history_order_time, starting_deal_time,
            get_hashes)

    async def initialize(self):
        """Initializes meta api connection"""
        self._check_is_connection_active()
        await self._historyStorage.initialize(self._account.id, self._connection_registry.application)
        self._websocketClient.add_account_region(self._account.id, self._account.region)

    async def subscribe(self):
        """Initiates subscription to MetaTrader terminal.

        Returns:
            A coroutine which resolves when subscription is initiated.
        """
        self._check_is_connection_active()
        self._websocketClient.ensure_subscribe(self._account.id, 0)
        self._websocketClient.ensure_subscribe(self._account.id, 1)

    async def subscribe_to_market_data(self, symbol: str, subscriptions: List[MarketDataSubscription] = None,
                                       timeout_in_seconds: float = None) -> Coroutine:
        """Subscribes on market data of specified symbol (see
        https://metaapi.cloud/docs/client/websocket/marketDataStreaming/subscribeToMarketData/).

        Args:
            symbol: Symbol (e.g. currency pair or an index).
            subscriptions: Array of market data subscription to create or update. Please note that this feature is
            not fully implemented on server-side yet.
            timeout_in_seconds: Timeout to wait for prices in seconds, default is 30.

        Returns:
            Promise which resolves when subscription request was processed.
        """
        self._check_is_connection_active()
        if self._terminalState.specification(symbol) is None:
            raise ValidationException(f'Cannot subscribe to market data for symbol {symbol} because symbol '
                                      f'does not exist')
        else:
            subscriptions = subscriptions or [{'type': 'quotes'}]
            if symbol in self._subscriptions:
                prev_subscriptions = self._subscriptions[symbol]['subscriptions'] or []
                for subscription in subscriptions:
                    index = -1
                    for i in range(len(prev_subscriptions)):
                        item = prev_subscriptions[i]
                        if subscription['type'] == 'candles':
                            if item['type'] == subscription['type'] and \
                                    item['timeframe'] == subscription['timeframe']:
                                index = i
                                break
                        elif item['type'] == subscription['type']:
                            index = i
                            break
                    if index == -1:
                        prev_subscriptions.append(subscription)
                    else:
                        prev_subscriptions[index] = subscription
            else:
                self._subscriptions[symbol] = {'subscriptions': subscriptions}
            await self._websocketClient.subscribe_to_market_data(self._account.id, symbol, subscriptions,
                                                                 self._account.reliability)
            return await self.terminal_state.wait_for_price(symbol, timeout_in_seconds)

    def unsubscribe_from_market_data(self, symbol: str, subscriptions: List[MarketDataUnsubscription] = None) \
            -> Coroutine:
        """Unsubscribes from market data of specified symbol (see
        https://metaapi.cloud/docs/client/websocket/marketDataStreaming/subscribeToMarketData/).

        Args:
            symbol: Symbol (e.g. currency pair or an index).
            subscriptions: Array of subscriptions to cancel.

        Returns:
            Promise which resolves when subscription request was processed.
        """
        self._check_is_connection_active()
        if not subscriptions:
            if symbol in self._subscriptions:
                del self._subscriptions[symbol]
        elif symbol in self._subscriptions:
            self._subscriptions[symbol]['subscriptions'] = list(filter(
                lambda s: not next((s2 for s2 in subscriptions if (
                    (s['type'] == s2['type'] and s['timeframe'] == s2['timeframe']) if s['type'] == 'candles' else
                    s['type'] == s2['type'])), None),
                self._subscriptions[symbol]['subscriptions']))
            if not len(self._subscriptions[symbol]['subscriptions']):
                del self._subscriptions[symbol]
        return self._websocketClient.unsubscribe_from_market_data(self._account.id, symbol, subscriptions,
                                                                  self._account.reliability)

    async def on_subscription_downgraded(self, instance_index: str, symbol: str,
                                         updates: List[MarketDataSubscription] or None = None,
                                         unsubscriptions: List[MarketDataUnsubscription] or None = None):
        """Invoked when subscription downgrade has occurred.

        Args:
            instance_index: Index of an account instance connected.
            symbol: Symbol to update subscriptions for.
            updates: Array of market data subscription to update.
            unsubscriptions: Array of subscriptions to cancel.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        subscriptions = self._subscriptions[symbol] if symbol in self._subscriptions else None
        if unsubscriptions and len(unsubscriptions):
            if subscriptions:
                for subscription in unsubscriptions:
                    subscriptions = list(filter(lambda s: s['type'] == subscription['type'], subscriptions))
            asyncio.create_task(self.unsubscribe_from_market_data(symbol, unsubscriptions))
        if updates and len(updates):
            if subscriptions:
                for subscription in updates:
                    for s in list(filter(lambda s: s['type'] == subscription['type'], subscriptions)):
                        s['intervalInMilliiseconds'] = subscription['intervalInMilliseconds']
            asyncio.create_task(self.subscribe_to_market_data(symbol, updates))
        if subscriptions and (not len(subscriptions)):
            del self._subscriptions[symbol]

    @property
    def subscribed_symbols(self) -> List[str]:
        """Returns list of the symbols connection is subscribed to.

        Returns:
            List of the symbols connection is subscribed to.
        """
        return list(self._subscriptions.keys())

    def subscriptions(self, symbol) -> List[MarketDataSubscription]:
        """Returns subscriptions for a symbol.

        Args:
            symbol: Symbol to retrieve subscriptions for.

        Returns:
            List of market data subscriptions for the symbol.
        """
        self._check_is_connection_active()
        return self._subscriptions[symbol]['subscriptions'] if symbol in self._subscriptions else []

    def save_uptime(self, uptime: Dict):
        """Sends client uptime stats to the server.

        Args:
            uptime: Uptime statistics to send to the server.

        Returns:
            A coroutine which resolves when uptime statistics is submitted.
        """
        self._check_is_connection_active()
        return self._websocketClient.save_uptime(self._account.id, uptime)

    @property
    def terminal_state(self) -> TerminalState:
        """Returns local copy of terminal state.

        Returns:
            Local copy of terminal state.
        """
        return self._terminalState

    @property
    def history_storage(self) -> HistoryStorage:
        """Returns local history storage.

        Returns:
            Local history storage.
        """
        return self._historyStorage

    def add_synchronization_listener(self, listener):
        """Adds synchronization listener.

        Args:
            listener: Synchronization listener to add.
        """
        self._synchronizationListeners.append(listener)
        self._websocketClient.add_synchronization_listener(self._account.id, listener)

    def remove_synchronization_listener(self, listener):
        """Removes synchronization listener for specific account.

        Args:
            listener: Synchronization listener to remove.
        """
        self._synchronizationListeners = list(filter(lambda l: l != listener, self._synchronizationListeners))
        self._websocketClient.remove_synchronization_listener(self._account.id, listener)

    async def on_connected(self, instance_index: str, replicas: int):
        """Invoked when connection to MetaTrader terminal established.

        Args:
            instance_index: Index of an account instance connected.
            replicas: Number of account replicas launched.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        key = random_id(32)
        state = self._get_state(instance_index)
        state['shouldSynchronize'] = key
        state['synchronizationRetryIntervalInSeconds'] = 1
        state['synchronized'] = False
        asyncio.create_task(self._ensure_synchronized(instance_index, key))
        indices = []
        for i in range(replicas):
            indices.append(i)
        for key in list(self._stateByInstanceIndex.keys()):
            e = self._stateByInstanceIndex[key]
            if self.get_instance_number(e['instanceIndex']) not in indices:
                del self._stateByInstanceIndex[key]
        self._logger.debug(f'{self._account.id}:{instance_index}: connected to broker')

    async def on_disconnected(self, instance_index: str):
        """Invoked when connection to MetaTrader terminal terminated.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
             A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        state['lastDisconnectedSynchronizationId'] = state['lastSynchronizationId']
        state['lastSynchronizationId'] = None
        state['shouldSynchronize'] = None
        state['synchronized'] = False
        state['disconnected'] = True
        instance = self.get_instance_number(instance_index)
        if instance in self._refreshMarketDataSubscriptionSessions:
            del self._refreshMarketDataSubscriptionSessions[instance]
        if instance in self._refreshMarketDataSubscriptionTimeouts:
            self._refreshMarketDataSubscriptionTimeouts[instance].cancel()
            del self._refreshMarketDataSubscriptionTimeouts[instance]
        if state['synchronizationTimeout']:
            state['synchronizationTimeout'].cancel()
            state['synchronizationTimeout'] = None
        if state['ensureSynchronizeTimeout']:
            state['ensureSynchronizeTimeout'].cancel()
            state['ensureSynchronizeTimeout'] = None
        self._logger.debug(f'{self._account.id}:{instance_index}: disconnected from broker')

    async def on_symbol_specifications_updated(self, instance_index: str,
                                               specifications: List[MetatraderSymbolSpecification],
                                               removed_symbols: List[str]):
        """Invoked when a symbol specifications were updated.

        Args:
            instance_index: Index of account instance connected.
            specifications: Updated specifications.
            removed_symbols: Removed symbols.
        """
        self._schedule_synchronization_timeout(instance_index)

    async def on_positions_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when position synchronization finished to indicate progress of an initial terminal state
        synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.
        """
        self._schedule_synchronization_timeout(instance_index)

    async def on_pending_orders_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when pending order synchronization finished to indicate progress of an initial terminal state
        synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        self._schedule_synchronization_timeout(instance_index)

    async def on_deals_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when a synchronization of history deals on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        state['dealsSynchronized'][synchronization_id] = True
        self._schedule_synchronization_timeout(instance_index)
        self._logger.debug(f'{self._account.id}:{instance_index}: finished synchronization {synchronization_id}')

    async def on_history_orders_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when a synchronization of history orders on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        state['ordersSynchronized'][synchronization_id] = True
        self._schedule_synchronization_timeout(instance_index)

    async def on_reconnected(self):
        """Invoked when connection to MetaApi websocket API restored after a disconnect.

        Returns:
            A coroutine which resolves when connection to MetaApi websocket API restored after a disconnect.
        """
        self._stateByInstanceIndex = {}
        self._refreshMarketDataSubscriptionSessions = {}
        for instance in list(self._refreshMarketDataSubscriptionTimeouts.keys()):
            self._refreshMarketDataSubscriptionTimeouts[instance].cancel()
        self._refreshMarketDataSubscriptionTimeouts = {}

    async def on_stream_closed(self, instance_index: str):
        """Invoked when a stream for an instance index is closed.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        if instance_index in self._stateByInstanceIndex:
            del self._stateByInstanceIndex[instance_index]

    async def on_synchronization_started(self, instance_index: str, specifications_updated: bool = True,
                                         positions_updated: bool = True, orders_updated: bool = True,
                                         synchronization_id: str = None):
        """Invoked when MetaTrader terminal state synchronization is started.

        Args:
            instance_index: Index of an account instance connected.
            specifications_updated: Whether specifications are going to be updated during synchronization.
            positions_updated: Whether positions are going to be updated during synchronization.
            orders_updated: Whether orders are going to be updated during synchronization.
            synchronization_id: Synchronization id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        self._logger.debug(f'{self._account.id}:{instance_index}: starting synchronization ${synchronization_id}')
        instance = self.get_instance_number(instance_index)
        if instance in self._refreshMarketDataSubscriptionSessions:
            del self._refreshMarketDataSubscriptionSessions[instance]
        session_id = random_id(32)
        self._refreshMarketDataSubscriptionSessions[instance] = session_id
        if instance in self._refreshMarketDataSubscriptionTimeouts:
            self._refreshMarketDataSubscriptionTimeouts[instance].cancel()
            del self._refreshMarketDataSubscriptionTimeouts[instance]
        await self._refresh_market_data_subscriptions(instance, session_id)
        self._schedule_synchronization_timeout(instance_index)
        state = self._get_state(instance_index)
        if state and not self._closed:
            state['lastSynchronizationId'] = synchronization_id

    async def is_synchronized(self, instance_index: str, synchronization_id: str = None) -> bool:
        """Returns flag indicating status of state synchronization with MetaTrader terminal.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Optional synchronization request id, last synchronization request id will be used.

        Returns:
            A coroutine resolving with a flag indicating status of state synchronization with MetaTrader terminal.
        """
        def reducer_func(acc, s: MetaApiConnectionDict):
            if instance_index is not None and s['instanceIndex'] != instance_index:
                return acc
            nonlocal synchronization_id
            synchronization_id = synchronization_id or s['lastSynchronizationId']
            synchronized = synchronization_id in s['ordersSynchronized'] and \
                bool(s['ordersSynchronized'][synchronization_id]) and \
                synchronization_id in s['dealsSynchronized'] and \
                bool(s['dealsSynchronized'][synchronization_id])
            return acc or synchronized
        return reduce(reducer_func, self._stateByInstanceIndex.values(), False) if \
            len(self._stateByInstanceIndex.values()) else False

    async def wait_synchronized(self, opts: SynchronizationOptions = None):
        """Waits until synchronization to MetaTrader terminal is completed.

        Args:
            opts: Synchronization options.

        Returns:
            A coroutine which resolves when synchronization to MetaTrader terminal is completed.

        Raises:
            TimeoutException: If application failed to synchronize with the terminal within timeout allowed.
        """
        self._check_is_connection_active()
        start_time = datetime.now()
        opts = opts or {}
        instance_index = opts['instanceIndex'] if 'instanceIndex' in opts else None
        synchronization_id = opts['synchronizationId'] if 'synchronizationId' in opts else None
        timeout_in_seconds = opts['timeoutInSeconds'] if 'timeoutInSeconds' in opts else 300
        interval_in_milliseconds = opts['intervalInMilliseconds'] if 'intervalInMilliseconds' in opts else 1000
        application_pattern = opts['applicationPattern'] if 'applicationPattern' in opts \
            else ('CopyFactory.*|RPC' if self._account.application == 'CopyFactory' else 'RPC')
        synchronized = await self.is_synchronized(instance_index, synchronization_id)
        while not synchronized and (start_time + timedelta(seconds=timeout_in_seconds) > datetime.now()):
            await asyncio.sleep(interval_in_milliseconds / 1000)
            synchronized = await self.is_synchronized(instance_index, synchronization_id)
        state = None
        if instance_index is None:
            for s in self._stateByInstanceIndex.values():
                if await self.is_synchronized(s['instanceIndex'], synchronization_id):
                    state = s
                    instance_index = s['instanceIndex']
        else:
            state = next((s for s in self._stateByInstanceIndex if s['instanceIndex'] == instance_index), None)
        if not synchronized:
            raise TimeoutException('Timed out waiting for MetaApi to synchronize to MetaTrader account ' +
                                   self._account.id + ', synchronization id ' +
                                   (synchronization_id or (bool(state) and state['lastSynchronizationId']) or
                                    (bool(state) and state['lastDisconnectedSynchronizationId']) or 'None'))
        time_left_in_seconds = max(0, timeout_in_seconds - (datetime.now() - start_time).total_seconds())
        await self._websocketClient.wait_synchronized(self._account.id, self.get_instance_number(instance_index),
                                                      application_pattern, time_left_in_seconds)

    def queue_event(self, name: str, callable: Callable):
        """Queues an event for processing among other synchronization events within same account.

        Args:
            name: Event label name.
            callable: Async or regular function to execute.
        """
        self._websocketClient.queue_event(self._account.id, name, callable)

    async def close(self):
        """Closes the connection. The instance of the class should no longer be used after this method is invoked."""
        if not self._closed:
            self._logger.debug(f'{self._account.id}: Closing connection')
            self._stateByInstanceIndex = {}
            self._connection_registry.remove(self._account.id)
            await self._websocketClient.unsubscribe(self._account.id)
            self._websocketClient.remove_synchronization_listener(self._account.id, self)
            self._websocketClient.remove_synchronization_listener(self._account.id, self._terminalState)
            self._websocketClient.remove_synchronization_listener(self._account.id, self._historyStorage)
            self._websocketClient.remove_synchronization_listener(self._account.id, self._healthMonitor)
            for listener in self._synchronizationListeners:
                self._websocketClient.remove_synchronization_listener(self._account.id, listener)
            self._synchronizationListeners = []
            self._websocketClient.remove_reconnect_listener(self)
            self._healthMonitor.stop()
            self._refreshMarketDataSubscriptionSessions = {}
            for instance in list(self._refreshMarketDataSubscriptionTimeouts.keys()):
                self._refreshMarketDataSubscriptionTimeouts[instance].cancel()
            self._refreshMarketDataSubscriptionTimeouts = {}
            self._websocketClient.remove_account_region(self.account.id)
            self._closed = True
            self._logger.debug(f'{self._account.id}: Closed connection')

    @property
    def synchronized(self) -> bool:
        """Returns synchronization status.

        Returns:
            Synchronization status.
        """
        return True in list(map(lambda s: s['synchronized'], self._stateByInstanceIndex.values()))

    @property
    def health_monitor(self) -> ConnectionHealthMonitor:
        """Returns connection health monitor instance.

        Returns:
            Connection health monitor instance.
        """
        return self._healthMonitor

    async def _refresh_market_data_subscriptions(self, instance_number: int, session: str):
        try:
            if instance_number in self._refreshMarketDataSubscriptionSessions and \
                    self._refreshMarketDataSubscriptionSessions[instance_number] == session:
                subscriptions_list = []
                for key in self._subscriptions.keys():
                    subscriptions = self.subscriptions(key)
                    subscriptions_item = {'symbol': key}
                    if subscriptions is not None:
                        subscriptions_item['subscriptions'] = subscriptions
                    subscriptions_list.append(subscriptions_item)
                await self._websocketClient.refresh_market_data_subscriptions(
                    self._account.id, instance_number, subscriptions_list)
        except Exception as err:
            self._logger.error(f'Error refreshing market data subscriptions job for account {self._account.id} '
                               f'{instance_number} ' + string_format_error(err))
        finally:
            async def refresh_market_data_subscriptions_job():
                await asyncio.sleep(uniform(self._minSubscriptionRefreshInterval,
                                            self._maxSubscriptionRefreshInterval))
                await self._refresh_market_data_subscriptions(instance_number, session)

            if instance_number in self._refreshMarketDataSubscriptionSessions and \
                    self._refreshMarketDataSubscriptionSessions[instance_number] == session:
                self._refreshMarketDataSubscriptionTimeouts[instance_number] = \
                    asyncio.create_task(refresh_market_data_subscriptions_job())

    async def _ensure_synchronized(self, instance_index: str, key):
        state = self._get_state(instance_index)
        if state and not self._closed:
            try:
                synchronization_result = await self.synchronize(instance_index)
                if synchronization_result:
                    state['synchronized'] = True
                    state['synchronizationRetryIntervalInSeconds'] = 1
                    state['ensureSynchronizeTimeout'] = None
                self._schedule_synchronization_timeout(instance_index)
            except Exception as err:
                self._logger.error(f'MetaApi websocket client for account {self.account.id}:{str(instance_index)}'
                                   f' failed to synchronize ' + string_format_error(err))
                if state['shouldSynchronize'] == key:
                    if state['ensureSynchronizeTimeout']:
                        state['ensureSynchronizeTimeout'].cancel()

                    async def restart_ensure_sync():
                        await asyncio.sleep(state['synchronizationRetryIntervalInSeconds'])
                        await self._ensure_synchronized(instance_index, key)
                    state['ensureSynchronizeTimeout'] = asyncio.create_task(restart_ensure_sync())
                    state['synchronizationRetryIntervalInSeconds'] = \
                        min(state['synchronizationRetryIntervalInSeconds'] * 2, 300)

    def _get_state(self, instance_index: str) -> MetaApiConnectionDict:
        if instance_index not in self._stateByInstanceIndex:
            self._stateByInstanceIndex[instance_index] = {
                'instanceIndex': instance_index,
                'ordersSynchronized': {},
                'dealsSynchronized': {},
                'shouldSynchronize': None,
                'synchronizationRetryIntervalInSeconds': 1,
                'synchronized': False,
                'lastDisconnectedSynchronizationId': None,
                'lastSynchronizationId': None,
                'disconnected': False,
                'synchronizationTimeout': None,
                'ensureSynchronizeTimeout': None
            }
        return self._stateByInstanceIndex[instance_index]

    def _schedule_synchronization_timeout(self, instance_index: str):
        state = self._get_state(instance_index)
        if state and not self._closed:
            if state['synchronizationTimeout']:
                state['synchronizationTimeout'].cancel()
            synchronization_timeout = 2 * 60

            async def _check_timed_out():
                await asyncio.sleep(synchronization_timeout)
                self._check_synchronization_timed_out(instance_index)

            state['synchronizationTimeout'] = asyncio.create_task(_check_timed_out())

    def _check_synchronization_timed_out(self, instance_index: str):
        state = self._get_state(instance_index)
        if state and not self._closed:
            synchronization_id = state['lastSynchronizationId']
            synchronized = synchronization_id in state['dealsSynchronized'] and \
                state['dealsSynchronized'][synchronization_id]
            if not synchronized and synchronization_id and state['shouldSynchronize']:
                self._logger.warn(f'{self._account.id}:{instance_index}: resynchronized since latest ' +
                                  f'synchronization {synchronization_id} did not finish in time')
                self._ensure_synchronized(instance_index, state['shouldSynchronize'])
