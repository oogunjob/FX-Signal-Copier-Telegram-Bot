from ..timeoutException import TimeoutException
from .tradeException import TradeException
from ..errorHandler import ValidationException, NotFoundException, InternalException, UnauthorizedException, \
    TooManyRequestsException
from ..optionsValidator import OptionsValidator
from .notSynchronizedException import NotSynchronizedException
from .notConnectedException import NotConnectedException
from .synchronizationListener import SynchronizationListener
from .reconnectListener import ReconnectListener
from ...metaApi.models import MetatraderHistoryOrders, MetatraderDeals, date, random_id, \
    MetatraderSymbolSpecification, MetatraderTradeResponse, MetatraderSymbolPrice, MetatraderAccountInformation, \
    MetatraderPosition, MetatraderOrder, format_date, MarketDataSubscription, MarketDataUnsubscription, \
    MetatraderCandle, MetatraderTick, MetatraderBook, ServerTime, string_format_error, format_error, promise_any, \
    Margin, MarginOrder
from .latencyListener import LatencyListener
from .packetOrderer import PacketOrderer
from .packetLogger import PacketLogger
from .synchronizationThrottler import SynchronizationThrottler
from .subscriptionManager import SubscriptionManager
import socketio
import asyncio
import re
from random import random
from datetime import datetime, timedelta
from typing import Coroutine, List, Dict, Callable
from collections import deque
from copy import copy
import json
import math
from ...logger import LoggerManager


class MetaApiWebsocketClient:
    """MetaApi websocket API client (see https://metaapi.cloud/docs/client/websocket/overview/)"""

    def __init__(self, http_client, token: str, opts: Dict = None):
        """Inits MetaApi websocket API client instance.

        Args:
            http_client: HTTP client.
            token: Authorization token.
            opts: Websocket client options.
        """
        validator = OptionsValidator()
        opts = opts or {}
        opts['packetOrderingTimeout'] = validator.validate_non_zero(
            opts['packetOrderingTimeout'] if 'packetOrderingTimeout' in opts else None, 60, 'packetOrderingTimeout')
        opts['synchronizationThrottler'] = opts['synchronizationThrottler'] if 'synchronizationThrottler' in \
                                                                               opts else {}
        self._httpClient = http_client
        self._application = opts['application'] if 'application' in opts else 'MetaApi'
        self._domain = opts['domain'] if 'domain' in opts else 'agiliumtrade.agiliumtrade.ai'
        self._region = opts['region'] if 'region' in opts else None
        self._hostname = 'mt-client-api-v1'
        self._url = None
        self._request_timeout = validator.validate_non_zero(
            opts['requestTimeout'] if 'requestTimeout' in opts else None, 60, 'requestTimeout')
        self._connect_timeout = validator.validate_non_zero(
            opts['connectTimeout'] if 'connectTimeout' in opts else None, 60, 'connectTimeout')
        retry_opts = opts['retryOpts'] if 'retryOpts' in opts else {}
        self._retries = validator.validate_number(
            retry_opts['retries'] if 'retries' in retry_opts else None, 5, 'retries')
        self._minRetryDelayInSeconds = validator.validate_non_zero(
            retry_opts['minDelayInSeconds'] if 'minDelayInSeconds' in retry_opts else None, 1, 'minDelayInSeconds')
        self._maxRetryDelayInSeconds = validator.validate_non_zero(
            retry_opts['maxDelayInSeconds'] if 'maxDelayInSeconds' in retry_opts else None, 30, 'maxDelayInSeconds')
        self._maxAccountsPerInstance = 100
        self._subscribeCooldownInSeconds = validator.validate_non_zero(
            retry_opts['subscribeCooldownInSeconds'] if 'subscribeCooldownInSeconds' in retry_opts else None, 600,
            'subscribeCooldownInSeconds')
        self._sequentialEventProcessing = True
        self._useSharedClientApi = validator.validate_boolean(
            opts['useSharedClientApi'] if 'useSharedClientApi' in opts else None, False, 'useSharedClientApi')
        self._enableSocketioDebugger = validator.validate_boolean(
            opts['enableSocketioDebugger'] if 'enableSocketioDebugger' in opts else None, False,
            'enableSocketioDebugger')
        self._unsubscribeThrottlingInterval = validator.validate_non_zero(
            opts['unsubscribeThrottlingIntervalInSeconds'] if 'unsubscribeThrottlingIntervalInSeconds' in opts else
            None, 10, 'unsubscribeThrottlingIntervalInSeconds')
        self._socketMinimumReconnectTimeout = 0.5
        self._token = token
        self._synchronizationListeners = {}
        self._latencyListeners = []
        self._reconnectListeners = []
        self._connectedHosts = {}
        self._socketInstances = {}
        self._socketInstancesByAccounts = {}
        self._regionsByAccounts = {}
        self._synchronizationThrottlerOpts = opts['synchronizationThrottler']
        self._subscriptionManager = SubscriptionManager(self)
        self._packetOrderer = PacketOrderer(self, opts['packetOrderingTimeout'])
        self._status_timers = {}
        self._eventQueues = {}
        self._synchronizationFlags = {}
        self._synchronizationIdByInstance = {}
        self._subscribeLock = None
        self._firstConnect = True
        self._lastRequestsTime = {}
        self._logger = LoggerManager.get_logger('MetaApiWebsocketClient')
        if 'packetLogger' in opts and 'enabled' in opts['packetLogger'] and opts['packetLogger']['enabled']:
            self._packetLogger = PacketLogger(opts['packetLogger'])
            self._packetLogger.start()
        else:
            self._packetLogger = None

        async def clear_regions_task():
            while True:
                await asyncio.sleep(30 * 60)
                self._clear_regions_job()

        asyncio.create_task(clear_regions_task())

    async def on_out_of_order_packet(self, account_id: str, instance_index: int, expected_sequence_number: int,
                                     actual_sequence_number: int, packet: Dict, received_at: datetime):
        """Restarts the account synchronization process on an out of order packet.

        Args:
            account_id: Account id.
            instance_index: Instance index.
            expected_sequence_number: Expected s/n.
            actual_sequence_number: Actual s/n.
            packet: Packet data.
            received_at: Time the packet was received at.
        """
        if self._subscriptionManager.is_subscription_active(account_id):
            self._logger.error(f'MetaApi websocket client received an out of order packet '
                               f'type {packet["type"]} for account id {account_id}:{instance_index}. Expected s/n '
                               f'{expected_sequence_number} does not match the actual of {actual_sequence_number}')
            self.ensure_subscribe(account_id, instance_index)

    def set_url(self, url: str):
        """Patch server URL for use in unit tests

        Args:
            url: Patched server URL.
        """
        self._url = url

    @property
    def region(self):
        """Websocket client predefined region.

        Returns:
            Predefined region.
        """
        return self._region

    @property
    def socket_instances(self):
        """Returns the list of socket instance dictionaries."""
        return self._socketInstances

    @property
    def socket_instances_by_accounts(self):
        """Returns the dictionary of socket instances by account ids"""
        return self._socketInstancesByAccounts

    def subscribed_account_ids(self, instance_number: int, socket_instance_index: int = None,
                               region: str = None) -> List[str]:
        """Returns the list of subscribed account ids.

        Args:
            instance_number: Instance index number.
            socket_instance_index: Socket instance index.
            region: Server region.
        """
        connected_ids = []
        if instance_number in self._socketInstancesByAccounts:
            for instance_id in self._connectedHosts.keys():
                account_id = instance_id.split(':')[0]
                account_region = self.get_account_region(account_id)
                if account_id not in connected_ids and account_id in self._socketInstancesByAccounts[instance_number] \
                    and (self._socketInstancesByAccounts[instance_number][account_id] == socket_instance_index or
                         socket_instance_index is None) and account_region == region:
                    connected_ids.append(account_id)
        return connected_ids

    def connected(self, instance_number: int, socket_instance_index: int, region: str) -> bool:
        """Returns websocket client connection status.

        Args:
            instance_number: Instance index number.
            socket_instance_index: Socket instance index.
            region: Server region.
        """
        instance = self._socketInstances[region][instance_number][socket_instance_index] if \
            region in self._socketInstances and instance_number in self._socketInstances[region] and \
            len(self._socketInstances[region][instance_number]) > socket_instance_index else None
        return instance['socket'].connected if instance else False

    def get_assigned_accounts(self, instance_number: int, socket_instance_index: int, region: str):
        """Returns list of accounts assigned to instance.

        Args:
            instance_number: Instance index number.
            socket_instance_index: Socket instance index.
            region: Server region.
        """
        account_ids = []
        for key in self._socketInstancesByAccounts[instance_number].keys():
            account_region = self.get_account_region(key)
            if account_region == region and \
                    self._socketInstancesByAccounts[instance_number][key] == socket_instance_index:
                account_ids.append(key)
        return account_ids

    def get_account_region(self, account_id: str) -> str or None:
        """Returns account region by id.

        Args:
            account_id: Account id.

        Returns:
            Account region
        """
        return self._regionsByAccounts[account_id]['region'] if account_id in self._regionsByAccounts else None

    def add_account_region(self, account_id: str, region: str):
        """Adds account region info.

        Args:
            account_id: Account id.
            region: Account region.
        """
        if account_id not in self._regionsByAccounts:
            self._regionsByAccounts[account_id] = {
                'region': region,
                'connections': 1,
                'lastUsed': datetime.now().timestamp()
            }
        else:
            self._regionsByAccounts[account_id]['connections'] += 1

    def remove_account_region(self, account_id: str):
        """Removes account region info.

        Args:
            account_id: Account id.
        """
        if account_id in self._regionsByAccounts:
            if self._regionsByAccounts[account_id]['connections'] > 0:
                self._regionsByAccounts[account_id]['connections'] -= 1

    async def lock_socket_instance(self, instance_number: int, socket_instance_index: int, region: str,
                                   metadata: Dict):
        """Locks subscription for a socket instance based on TooManyRequestsException metadata.

        Args:
            instance_number: Instance index number.
            socket_instance_index: Socket instance index.
            region: Server region.
            metadata: TooManyRequestsException metadata.
        """
        if metadata['type'] == 'LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_USER':
            self._subscribeLock = {
                'recommendedRetryTime': metadata['recommendedRetryTime'],
                'lockedAtAccounts': len(self.subscribed_account_ids(instance_number, None, region)),
                'lockedAtTime': datetime.now().timestamp()
            }
        else:
            subscribed_accounts = self.subscribed_account_ids(instance_number, socket_instance_index, region)
            if len(subscribed_accounts) == 0:
                await self._reconnect(instance_number, socket_instance_index, region)
            else:
                instance = self.socket_instances[region][instance_number][socket_instance_index]
                instance['subscribeLock'] = {
                    'recommendedRetryTime': metadata['recommendedRetryTime'],
                    'type': metadata['type'],
                    'lockedAtAccounts': len(subscribed_accounts)
                }

    async def connect(self, instance_number: int, region: str) -> asyncio.Future:
        """Connects to MetaApi server via socket.io protocol

        Args:
            instance_number: Instance index number.
            region: Server region.

        Returns:
            A coroutine which resolves when connection is established.
        """
        socket_instance_index = len(self._socketInstances[region][instance_number])
        instance = {
            'id': socket_instance_index,
            'reconnectWaitTime': self._socketMinimumReconnectTimeout,
            'connected': False,
            'requestResolves': {},
            'resolved': False,
            'connectResult': asyncio.Future(),
            'sessionId': random_id(),
            'isReconnecting': False,
            'socket': socketio.AsyncClient(reconnection=False, request_timeout=self._request_timeout,
                                           engineio_logger=self._enableSocketioDebugger),
            'synchronizationThrottler': SynchronizationThrottler(self, socket_instance_index, instance_number, region,
                                                                 self._synchronizationThrottlerOpts),
            'subscribeLock': None,
            'instanceNumber': instance_number
        }
        instance['synchronizationThrottler'].start()
        socket_instance = instance['socket']
        self._socketInstances[region][instance_number].append(instance)
        instance['connected'] = True
        if len(self._socketInstances[region][instance_number]) == 1:
            self._packetOrderer.start()

        @socket_instance.on('connect')
        async def on_connect():
            self._logger.info('MetaApi websocket client connected to the MetaApi server')
            instance['reconnectWaitTime'] = self._socketMinimumReconnectTimeout
            if not instance['resolved']:
                instance['resolved'] = True
                instance['connectResult'].set_result(None)

            if not instance['connected']:
                await instance['socket'].disconnect()

        @socket_instance.on('connect_error')
        def on_connect_error(err):
            self._logger.error('MetaApi websocket client connection error ' + string_format_error(err))
            if not instance['resolved']:
                instance['resolved'] = True
                instance['connectResult'].set_exception(Exception(err))

        @socket_instance.on('connect_timeout')
        def on_connect_timeout(timeout):
            self._logger.error('MetaApi websocket client connection timeout')
            if not instance['resolved']:
                instance['resolved'] = True
                instance['connectResult'].set_exception(TimeoutException(
                    'MetaApi websocket client connection timed out'))

        @socket_instance.on('disconnect')
        async def on_disconnect():
            instance['synchronizationThrottler'].on_disconnect()
            self._logger.info('MetaApi websocket client disconnected from the MetaApi server')
            await self._reconnect(instance_number, instance['id'], region)

        @socket_instance.on('error')
        async def on_error(err):
            self._logger.error('MetaApi websocket client error ' + string_format_error(err))
            await self._reconnect(instance_number, instance['id'], region)

        @socket_instance.on('response')
        async def on_response(data):
            if isinstance(data, str):
                data = json.loads(data)
            self._logger.debug(f"{data['accountId']}: Response received: " +
                               json.dumps({'requestId': data['requestId'],
                                           'timestamps': data['timestamps'] if 'timestamps' in data else None}))
            if data['requestId'] in instance['requestResolves']:
                request_resolve = instance['requestResolves'][data['requestId']]
                del instance['requestResolves'][data['requestId']]
            else:
                request_resolve = asyncio.Future()
            self._convert_iso_time_to_date(data)
            if not request_resolve.done():
                request_resolve.set_result(data)
            if 'timestamps' in data and hasattr(request_resolve, 'type'):
                data['timestamps']['clientProcessingFinished'] = datetime.now()
                for listener in self._latencyListeners:
                    try:
                        if request_resolve.type == 'trade':
                            await listener.on_trade(data['accountId'], data['timestamps'])
                        else:
                            await listener.on_response(data['accountId'], request_resolve.type, data['timestamps'])
                    except Exception as error:
                        self._logger.error(f"Failed to process on_response event for account {data['accountId']}, "
                                           f"request type {request_resolve.type} {string_format_error(error)}")

        @socket_instance.on('processingError')
        def on_processing_error(data):
            if data['requestId'] in instance['requestResolves']:
                request_resolve = instance['requestResolves'][data['requestId']]
                del instance['requestResolves'][data['requestId']]
                if not request_resolve.done():
                    request_resolve.set_exception(self._convert_error(data))

        @socket_instance.on('synchronization')
        async def on_synchronization(data):
            if isinstance(data, str):
                data = json.loads(data)
            packet_info = {
                'type': data['type'],
                'sequenceNumber': data['sequenceNumber'] if 'sequenceNumber' in data else None,
                'sequenceTimestamp': data['sequenceTimestamp'] if 'sequenceTimestamp' in data else None,
                'synchronizationId': data['synchronizationId'] if 'synchronizationId' in data else None,
                'application': data['application'] if 'application' in data else None,
                'host': data['host'] if 'host' in data else None,
                'specificationsUpdated': data['specificationsUpdated'] if 'specificationsUpdated' in data else None,
                'positionsUpdated': data['positionsUpdated'] if 'positionsUpdated' in data else None,
                'ordersUpdated': data['ordersUpdated'] if 'ordersUpdated' in data else None,
                'specifications': len(data['specifications']) if 'specifications' in data else None
            }
            if 'instanceIndex' in data and data['instanceIndex'] != instance_number:
                self._logger.debug(f'{data["accountId"]}:{data["instanceIndex"]}: received packet with wrong ' +
                                   f'instance index via a socket with instance number of {instance_number}, data' +
                                   f'{json.dumps(packet_info)}')
                return
            if data['accountId'] not in self._regionsByAccounts:
                self._regionsByAccounts[data['accountId']] = {
                    'region': region,
                    'connections': 0,
                    'lastUsed': datetime.now().timestamp()
                }
            self._logger.debug(
                f"{data['accountId']}:{data['instanceIndex'] if 'instanceIndex' in data else 0}: "
                f"Sync packet received: " + json.dumps(packet_info) + ', active listeners: ' +
                str(len(self._synchronizationListeners[data['accountId']]) if data['accountId'] in
                    self._synchronizationListeners else 0))
            active_synchronization_ids = instance['synchronizationThrottler'].active_synchronization_ids
            if ('synchronizationId' not in data) or (data['synchronizationId'] in active_synchronization_ids):
                if self._packetLogger:
                    self._packetLogger.log_packet(data)
                self._convert_iso_time_to_date(data)
                if not self._subscriptionManager.is_subscription_active(data['accountId']) and \
                        data['type'] != 'disconnected':
                    self._logger.debug(f'{data["accountId"]}: Packet arrived to inactive connection, attempting '
                                       f'unsubscribe')
                    if self._throttle_request('unsubscribe', data['accountId'], instance_number,
                                              self._unsubscribeThrottlingInterval):
                        async def unsubscribe():
                            try:
                                await self.unsubscribe(data['accountId'])
                            except Exception as err:
                                self._logger.warn(f'{data["accountId"]}:'
                                                  f'{data["instanceIndex"] if "instanceIndex" in data else 0}: '
                                                  'failed to unsubscribe', format_error(err))
                        asyncio.create_task(unsubscribe())
                    return
            else:
                data['type'] = 'noop'
            self.queue_packet(data)

        while not socket_instance.connected:
            try:
                client_id = "{:01.10f}".format(random())
                server_url = await self._get_server_url(instance_number, socket_instance_index, region)
                url = f'{server_url}?auth-token={self._token}&clientId={client_id}&protocol=3'
                instance['sessionId'] = random_id()
                await asyncio.wait_for(socket_instance.connect(url, socketio_path='ws',
                                                               headers={'Client-Id': client_id}),
                                       timeout=self._connect_timeout)
            except Exception:
                pass

        return instance['connectResult']

    async def close(self):
        """Closes connection to MetaApi server"""
        for region in self._socketInstances:
            for instance_number in self._socketInstances[region]:
                for instance in self._socketInstances[region][instance_number]:
                    if instance['connected']:
                        instance['connected'] = False
                        await instance['socket'].disconnect()
                        for request_resolve in instance['requestResolves']:
                            if not instance['requestResolves'][request_resolve].done():
                                instance['requestResolves'][request_resolve] \
                                    .set_exception(Exception('MetaApi connection closed'))
                        instance['requestResolves'] = {}

                    self._socketInstancesByAccounts[instance_number] = {}
                    self._socketInstances[region][instance_number] = []

        self._synchronizationListeners = {}
        self._latencyListeners = []
        self._packetOrderer.stop()

    async def get_account_information(self, account_id: str) -> 'asyncio.Future[MetatraderAccountInformation]':
        """Returns account information for a specified MetaTrader account
        (see https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readAccountInformation/).

        Args:
            account_id: Id of the MetaTrader account to return information for.

        Returns:
            A coroutine resolving with account information.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getAccountInformation'})
        return response['accountInformation']

    async def get_positions(self, account_id: str) -> 'asyncio.Future[List[MetatraderPosition]]':
        """Returns positions for a specified MetaTrader account
        (see https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readPositions/).

        Args:
            account_id: Id of the MetaTrader account to return information for.

        Returns:
            A coroutine resolving with array of open positions.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getPositions'})
        return response['positions']

    async def get_position(self, account_id: str, position_id: str) -> 'asyncio.Future[MetatraderPosition]':
        """Returns specific position for a MetaTrader account
        (see https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readPosition/).

        Args:
            account_id: Id of the MetaTrader account to return information for.
            position_id: Position id.

        Returns:
            A coroutine resolving with MetaTrader position found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getPosition',
                                                       'positionId': position_id})
        return response['position']

    async def get_orders(self, account_id: str) -> 'asyncio.Future[List[MetatraderOrder]]':
        """Returns open orders for a specified MetaTrader account
        (see https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readOrders/).

        Args:
            account_id: Id of the MetaTrader account to return information for.

        Returns:
            A coroutine resolving with open MetaTrader orders.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getOrders'})
        return response['orders']

    async def get_order(self, account_id: str, order_id: str) -> 'asyncio.Future[MetatraderOrder]':
        """Returns specific open order for a MetaTrader account
        (see https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readOrder/).

        Args:
            account_id: Id of the MetaTrader account to return information for.
            order_id: Order id (ticket number).

        Returns:
            A coroutine resolving with metatrader order found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getOrder', 'orderId': order_id})
        return response['order']

    async def get_history_orders_by_ticket(self, account_id: str, ticket: str) -> MetatraderHistoryOrders:
        """Returns the history of completed orders for a specific ticket number
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readHistoryOrdersByTicket/).

        Args:
            account_id: Id of the MetaTrader account to return information for.
            ticket: Ticket number (order id).

        Returns:
            A coroutine resolving with request results containing history orders found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getHistoryOrdersByTicket',
                                                       'ticket': ticket})
        return {
            'historyOrders': response['historyOrders'],
            'synchronizing': response['synchronizing']
        }

    async def get_history_orders_by_position(self, account_id: str, position_id: str) -> MetatraderHistoryOrders:
        """Returns the history of completed orders for a specific position id
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readHistoryOrdersByPosition/)

        Args:
            account_id: Id of the MetaTrader account to return information for.
            position_id: Position id.

        Returns:
            A coroutine resolving with request results containing history orders found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getHistoryOrdersByPosition',
                                                       'positionId': position_id})
        return {
            'historyOrders': response['historyOrders'],
            'synchronizing': response['synchronizing']
        }

    async def get_history_orders_by_time_range(self, account_id: str, start_time: datetime, end_time: datetime,
                                               offset=0, limit=1000) -> MetatraderHistoryOrders:
        """Returns the history of completed orders for a specific time range
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readHistoryOrdersByTimeRange/)

        Args:
            account_id: Id of the MetaTrader account to return information for.
            start_time: Start of time range, inclusive.
            end_time: End of time range, exclusive.
            offset: Pagination offset, default is 0.
            limit: Pagination limit, default is 1000.

        Returns:
            A coroutine resolving with request results containing history orders found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getHistoryOrdersByTimeRange',
                                                       'startTime': format_date(start_time),
                                                       'endTime': format_date(end_time),
                                                       'offset': offset, 'limit': limit})
        return {
            'historyOrders': response['historyOrders'],
            'synchronizing': response['synchronizing']
        }

    async def get_deals_by_ticket(self, account_id: str, ticket: str) -> MetatraderDeals:
        """Returns history deals with a specific ticket number
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readDealsByTicket/).

        Args:
            account_id: Id of the MetaTrader account to return information for.
            ticket: Ticket number (deal id for MT5 or order id for MT4).

        Returns:
            A coroutine resolving with request results containing deals found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getDealsByTicket',
                                                       'ticket': ticket})
        return {
            'deals': response['deals'],
            'synchronizing': response['synchronizing']
        }

    async def get_deals_by_position(self, account_id: str, position_id: str) -> MetatraderDeals:
        """Returns history deals for a specific position id
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readDealsByPosition/).

        Args:
            account_id: Id of the MetaTrader account to return information for.
            position_id: Position id.

        Returns:
            A coroutine resolving with request results containing deals found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getDealsByPosition',
                                                       'positionId': position_id})
        return {
            'deals': response['deals'],
            'synchronizing': response['synchronizing']
        }

    async def get_deals_by_time_range(self, account_id: str, start_time: datetime, end_time: datetime, offset: int = 0,
                                      limit: int = 1000) -> MetatraderDeals:
        """Returns history deals with for a specific time range
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveHistoricalData/readDealsByTimeRange/).

        Args:
            account_id: Id of the MetaTrader account to return information for.
            start_time: Start of time range, inclusive.
            end_time: End of time range, exclusive.
            offset: Pagination offset, default is 0.
            limit: Pagination limit, default is 1000.

        Returns:
            A coroutine resolving with request results containing deals found.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getDealsByTimeRange',
                                                       'startTime': format_date(start_time),
                                                       'endTime': format_date(end_time),
                                                       'offset': offset, 'limit': limit})
        return {
            'deals': response['deals'],
            'synchronizing': response['synchronizing']
        }

    def remove_application(self, account_id: str) -> Coroutine:
        """Clears the order and transaction history of a specified application and removes the application
        (see https://metaapi.cloud/docs/client/websocket/api/removeApplication/).

        Args:
            account_id: Id of the MetaTrader account to remove history and application for.

        Returns:
            A coroutine resolving when the history is cleared.
        """
        return self.rpc_request(account_id, {'type': 'removeApplication'})

    async def trade(self, account_id: str, trade, application: str = None, reliability: str = None) -> \
            'asyncio.Future[MetatraderTradeResponse]':
        """Execute a trade on a connected MetaTrader account
        (see https://metaapi.cloud/docs/client/websocket/api/trade/).

        Args:
            account_id: Id of the MetaTrader account to execute trade for.
            trade: Trade to execute (see docs for possible trade types).
            application: Application to use.
            reliability: Account reliability.

        Returns:
            A coroutine resolving with trade result.

        Raises:
            TradeException: On trade error, check error properties for error code details.
        """
        self._format_request(trade)
        if application == 'RPC':
            response = await self.rpc_request(account_id, {'type': 'trade', 'trade': trade,
                                                           'application': application})
        else:
            response = await self.rpc_request_all_instances(account_id, {
                'type': 'trade', 'trade': trade, 'application': application or self._application,
                'requestId': random_id(32)}, reliability)
        if 'response' not in response:
            response['response'] = {}
        if 'stringCode' not in response['response']:
            response['response']['stringCode'] = response['response']['description']
        if 'numericCode' not in response['response']:
            response['response']['numericCode'] = response['response']['error']
        if response['response']['stringCode'] in ['ERR_NO_ERROR', 'TRADE_RETCODE_PLACED', 'TRADE_RETCODE_DONE',
                                                  'TRADE_RETCODE_DONE_PARTIAL', 'TRADE_RETCODE_NO_CHANGES']:
            return response['response']
        else:
            raise TradeException(response['response']['message'], response['response']['numericCode'],
                                 response['response']['stringCode'])

    def ensure_subscribe(self, account_id: str, instance_number: int = None):
        """Creates a subscription manager task to send subscription requests until cancelled.

        Args:
            account_id: Account id to subscribe.
            instance_number: Instance index number.
        """
        asyncio.create_task(self._subscriptionManager.schedule_subscribe(account_id, instance_number))

    def subscribe(self, account_id: str, instance_number: int = None):
        """Subscribes to the Metatrader terminal events
        (see https://metaapi.cloud/docs/client/websocket/api/subscribe/).

        Args:
            account_id: Id of the MetaTrader account to subscribe to.
            instance_number: Instance index number.

        Returns:
            A coroutine which resolves when subscription started.
        """
        return self._subscriptionManager.subscribe(account_id, instance_number)

    def synchronize(self, account_id: str, instance_number: int, host: str, synchronization_id: str,
                    starting_history_order_time: datetime, starting_deal_time: datetime,
                    get_hashes) -> Coroutine:
        """Requests the terminal to start synchronization process.
        (see https://metaapi.cloud/docs/client/websocket/synchronizing/synchronize/).

        Args:
            account_id: Id of the MetaTrader account to synchronize.
            instance_number: Instance index number.
            host: Name of host to synchronize with.
            synchronization_id: Synchronization request id.
            starting_history_order_time: From what date to start synchronizing history orders from. If not specified,
            the entire order history will be downloaded.
            starting_deal_time: From what date to start deal synchronization from. If not specified, then all
            history deals will be downloaded.
            get_hashes: function to get terminal state hashes.

        Returns:
            A coroutine which resolves when synchronization is started.
        """
        sync_throttler = self._get_socket_instance_by_account(account_id, instance_number)['synchronizationThrottler']
        return sync_throttler.schedule_synchronize(account_id, {
            'requestId': synchronization_id, 'type': 'synchronize',
            'startingHistoryOrderTime': format_date(starting_history_order_time),
            'startingDealTime': format_date(starting_deal_time),
            'instanceIndex': instance_number, 'host': host
        }, get_hashes)

    def wait_synchronized(self, account_id: str, instance_number: int, application_pattern: str,
                          timeout_in_seconds: float, application: str = None):
        """Waits for server-side terminal state synchronization to complete.
        (see https://metaapi.cloud/docs/client/websocket/synchronizing/waitSynchronized/).

        Args:
            account_id: Id of the MetaTrader account to synchronize.
            instance_number: Instance index number.
            application_pattern: MetaApi application regular expression pattern, default is .*
            timeout_in_seconds: Timeout in seconds, default is 300 seconds.
            application: Application to synchronize with.
        """
        return self.rpc_request(account_id, {'type': 'waitSynchronized', 'applicationPattern': application_pattern,
                                             'timeoutInSeconds': timeout_in_seconds, 'instanceIndex': instance_number,
                                             'application': application or self._application},
                                timeout_in_seconds + 1)

    def subscribe_to_market_data(self, account_id: str, symbol: str,
                                 subscriptions: List[MarketDataSubscription] = None,
                                 reliability: str = None) -> Coroutine:
        """Subscribes on market data of specified symbol
        (see https://metaapi.cloud/docs/client/websocket/marketDataStreaming/subscribeToMarketData/).

        Args:
            account_id: Id of the MetaTrader account.
            symbol: Symbol (e.g. currency pair or an index).
            subscriptions: Array of market data subscription to create or update.
            reliability: Account reliability.

        Returns:
            A coroutine which resolves when subscription request was processed.
        """
        packet = {'type': 'subscribeToMarketData', 'symbol': symbol}
        if subscriptions is not None:
            packet['subscriptions'] = subscriptions
        return self.rpc_request_all_instances(account_id, packet, reliability)

    def refresh_market_data_subscriptions(self, account_id: str, instance_number: int, subscriptions: List[dict]) \
            -> Coroutine:
        """Refreshes market data subscriptions on the server to prevent them from expiring.

        Args:
            account_id: Id of the MetaTrader account.
            instance_number: Instance index number.
            subscriptions: Array of subscriptions to refresh.

        Returns:
            A coroutine which resolves when refresh request was processed.
        """
        return self.rpc_request(account_id, {'type': 'refreshMarketDataSubscriptions', 'subscriptions': subscriptions,
                                             'instanceIndex': instance_number})

    def unsubscribe_from_market_data(self, account_id: str, symbol: str,
                                     subscriptions: List[MarketDataUnsubscription] = None,
                                     reliability: str = None) -> Coroutine:
        """Unsubscribes from market data of specified symbol
        (see https://metaapi.cloud/docs/client/websocket/marketDataStreaming/unsubscribeFromMarketData/).

        Args:
            account_id: Id of the MetaTrader account.
            symbol: Symbol (e.g. currency pair or an index).
            subscriptions: Array of subscriptions to cancel.
            reliability: Account reliability.

        Returns:
            A coroutine which resolves when unsubscription request was processed.
        """
        packet = {'type': 'unsubscribeFromMarketData', 'symbol': symbol}
        if subscriptions is not None:
            packet['subscriptions'] = subscriptions
        return self.rpc_request_all_instances(account_id, packet, reliability)

    async def get_symbols(self, account_id: str) -> 'asyncio.Future[List[str]]':
        """Retrieves symbols available on an account (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readSymbols/).

        Args:
            account_id: Id of the MetaTrader account to retrieve symbols for.

        Returns:
            A coroutine which resolves when symbols are retrieved.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getSymbols'})
        return response['symbols']

    async def get_symbol_specification(self, account_id: str, symbol: str) -> \
            'asyncio.Future[MetatraderSymbolSpecification]':
        """Retrieves specification for a symbol
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readSymbolSpecification/).

        Args:
            account_id: Id of the MetaTrader account to retrieve symbol specification for.
            symbol: Symbol to retrieve specification for.

        Returns:
            A coroutine which resolves when specification is retrieved.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getSymbolSpecification',
                                                       'symbol': symbol})
        return response['specification']

    async def get_symbol_price(self, account_id: str, symbol: str, keep_subscription: bool = False) -> \
            'asyncio.Future[MetatraderSymbolPrice]':
        """Retrieves price for a symbol
        (see https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readSymbolPrice/).

        Args:
            account_id: Id of the MetaTrader account to retrieve symbol price for.
            symbol: Symbol to retrieve price for.
            keep_subscription: If set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when price is retrieved.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getSymbolPrice',
                                                       'symbol': symbol, 'keepSubscription': keep_subscription})
        return response['price']

    async def get_candle(self, account_id: str, symbol: str, timeframe: str, keep_subscription: bool = False) -> \
            'asyncio.Future[MetatraderCandle]':
        """Retrieves price for a symbol (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readCandle/).

        Args:
            account_id: Id of the MetaTrader account to retrieve candle for.
            symbol: Symbol to retrieve candle for.
            timeframe: Defines the timeframe according to which the candle must be generated. Allowed values for
            MT5 are 1m, 2m, 3m, 4m, 5m, 6m, 10m, 12m, 15m, 20m, 30m, 1h, 2h, 3h, 4h, 6h, 8h, 12h, 1d, 1w, 1mn.
            Allowed values for MT4 are 1m, 5m, 15m 30m, 1h, 4h, 1d, 1w, 1mn.
            keep_subscription: If set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when candle is retrieved.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getCandle',
                                                       'symbol': symbol, 'timeframe': timeframe,
                                                       'keepSubscription': keep_subscription})
        return response['candle']

    async def get_tick(self, account_id: str, symbol: str, keep_subscription: bool = False) -> \
            'asyncio.Future[MetatraderTick]':
        """Retrieves latest tick for a symbol. MT4 G1 accounts do not support this API (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readTick/).

        Args:
            account_id: Id of the MetaTrader account to retrieve symbol tick for.
            symbol: Symbol to retrieve tick for.
            keep_subscription: If set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when tick is retrieved.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getTick',
                                                       'symbol': symbol, 'keepSubscription': keep_subscription})
        return response['tick']

    async def get_book(self, account_id: str, symbol: str, keep_subscription: bool = False) -> \
            'asyncio.Future[MetatraderBook]':
        """Retrieves latest order book for a symbol. MT4 accounts do not support this API (see
        https://metaapi.cloud/docs/client/websocket/api/retrieveMarketData/readBook/).

        Args:
            account_id: Id of the MetaTrader account to retrieve symbol order book for.
            symbol: Symbol to retrieve order book for.
            keep_subscription: If set to true, the account will get a long-term subscription to symbol market data.
            Long-term subscription means that on subsequent calls you will get updated value faster. If set to false or
            not set, the subscription will be set to expire in 12 minutes.

        Returns:
            A coroutine which resolves when order book is retrieved.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getBook',
                                                       'symbol': symbol, 'keepSubscription': keep_subscription})
        return response['book']

    def save_uptime(self, account_id: str, uptime: Dict):
        """Sends client uptime stats to the server.

        Args:
            account_id: Id of the MetaTrader account to save uptime.
            uptime: Uptime statistics to send to the server.

        Returns:
            A coroutine which resolves when uptime statistics is submitted.
        """
        return self.rpc_request(account_id, {'type': 'saveUptime', 'uptime': uptime})

    async def unsubscribe(self, account_id: str):
        """Unsubscribe from account (see https://metaapi.cloud/docs/client/websocket/api/synchronizing/unsubscribe).

        Args:
            account_id: Id of the MetaTrader account to unsubscribe.

        Returns:
            A coroutine which resolves when socket is unsubscribed."""
        try:
            region = self.get_account_region(account_id)

            async def unsubscribe_job(instance_number):
                await self._subscriptionManager.unsubscribe(account_id, int(instance_number))
                if instance_number in self._socketInstancesByAccounts and \
                        account_id in self._socketInstancesByAccounts[instance_number]:
                    del self._socketInstancesByAccounts[instance_number]

            await asyncio.gather(
                *list(map(lambda instance_number: asyncio.create_task(unsubscribe_job(instance_number)),
                          self._socketInstances[region].keys())))
        except (NotFoundException, TimeoutException):
            pass

    async def get_server_time(self, account_id: str) -> ServerTime:
        """Returns server time for a specified MetaTrader account (see
        https://metaapi.cloud/docs/client/websocket/api/readTradingTerminalState/readServerTime/).

        Args:
            account_id: Id of the MetaTrader account to return server time for.

        Returns:
            A coroutine resolving with server time.
        """
        response = await self.rpc_request(account_id, {'application': 'RPC', 'type': 'getServerTime'})
        return response['serverTime']

    async def calculate_margin(self, account_id: str, application: str, reliability: str, order: MarginOrder) \
            -> Margin:
        """Calculates margin required to open a trade on the specified trading account (see
        https://metaapi.cloud/docs/client/websocket/api/calculateMargin/).

        Args:
            account_id: Id of the trading account to calculate margin for.
            application: Application to send the request to.
            reliability: Account reliability.
            order: Order to calculate margin for.

        Returns:
            A coroutine resolving with margin calculation result.
        """
        if application == 'RPC':
            response = await self.rpc_request(account_id, {'application': application, 'type': 'calculateMargin',
                                                           'order': order})
        else:
            response = await self.rpc_request_all_instances(
                account_id, {'application': application, 'type': 'calculateMargin', 'order': order}, reliability)
        return response['margin']

    def add_synchronization_listener(self, account_id: str, listener: SynchronizationListener):
        """Adds synchronization listener for specific account.

        Args:
            account_id: Account id.
            listener: Synchronization listener to add.
        """
        self._logger.debug(f'{account_id}: Added synchronization listener')
        if account_id in self._synchronizationListeners:
            listeners = self._synchronizationListeners[account_id]
        else:
            listeners = []
            self._synchronizationListeners[account_id] = listeners
        listeners.append(listener)

    def remove_synchronization_listener(self, account_id: str, listener: SynchronizationListener):
        """Removes synchronization listener for specific account.

        Args:
            account_id: Account id.
            listener: Synchronization listener to remove.
        """
        self._logger.debug(f'{account_id}: Removed synchronization listener')
        listeners = self._synchronizationListeners[account_id]

        if not listeners:
            listeners = []
        elif listeners.__contains__(listener):
            listeners.remove(listener)
        self._synchronizationListeners[account_id] = listeners

    def add_latency_listener(self, listener: LatencyListener):
        """Adds latency listener.

        Args:
            listener: Latency listener to add."""
        self._latencyListeners.append(listener)

    def remove_latency_listener(self, listener: LatencyListener):
        """Removes latency listener.

        Args:
            listener: Latency listener to remove."""
        self._latencyListeners = list(filter(lambda l: l != listener, self._latencyListeners))

    def add_reconnect_listener(self, listener: ReconnectListener, account_id: str):
        """Adds reconnect listener.

        Args:
            listener: Reconnect listener to add.
            account_id: Account id of listener.
        """

        self._reconnectListeners.append({'accountId': account_id, 'listener': listener})

    def remove_reconnect_listener(self, listener: ReconnectListener):
        """Removes reconnect listener.

        Args:
            listener: Listener to remove.
        """
        for i in range(len(self._reconnectListeners)):
            if self._reconnectListeners[i]['listener'] == listener:
                self._reconnectListeners.remove(self._reconnectListeners[i])
                break

    def remove_all_listeners(self):
        """Removes all listeners. Intended for use in unit tests."""

        self._synchronizationListeners = {}
        self._reconnectListeners = []

    def queue_packet(self, packet: dict):
        """Queues an account packet for processing.

        Args:
            packet: Packet to process.
        """
        account_id = packet['accountId']
        packets = self._packetOrderer.restore_order(packet)
        packets = list(filter(lambda e: e['type'] != 'noop', packets))
        if self._sequentialEventProcessing and 'sequenceNumber' in packet:
            events = list(map(lambda packet: lambda: self._process_synchronization_packet(packet), packets))
            if account_id not in self._eventQueues:
                self._eventQueues[account_id] = deque(events)
                asyncio.create_task(self._call_account_events(account_id))
            else:
                self._eventQueues[account_id] += events
        else:
            for packet in packets:
                asyncio.create_task(self._process_synchronization_packet(packet))

    def queue_event(self, account_id: str, name: str, callable_: Callable):
        """Queues an account event for processing.

        Args:
            account_id: Account id.
            name: Event label name.
            callable_: Async function to execute.
        """
        async def event():
            return await self._process_event(callable_, f'{account_id}:{name}')

        if self._sequentialEventProcessing:
            if account_id not in self._eventQueues:
                self._eventQueues[account_id] = deque([event])
                asyncio.create_task(self._call_account_events(account_id))
            else:
                self._eventQueues[account_id].append(event)
        else:
            asyncio.create_task(event)

    async def _call_account_events(self, account_id):
        if account_id in self._eventQueues:
            while len(self._eventQueues[account_id]):
                await self._eventQueues[account_id][0]()
                self._eventQueues[account_id].popleft()
            del self._eventQueues[account_id]

    async def _reconnect(self, instance_number: int, socket_instance_index: int, region: str):
        reconnected = False
        instance = self._socketInstances[region][instance_number][socket_instance_index]
        if not instance['isReconnecting']:
            instance['isReconnecting'] = True
            while instance['connected'] and not reconnected:
                instance['reconnectWaitTime'] = min(instance['reconnectWaitTime'] * 2, 30)
                await asyncio.sleep(instance['reconnectWaitTime'])
                try:
                    await instance['socket'].disconnect()
                    client_id = "{:01.10f}".format(random())
                    instance['connectResult'] = asyncio.Future()
                    instance['resolved'] = False
                    instance['sessionId'] = random_id()
                    server_url = await self._get_server_url(instance_number, socket_instance_index, region)
                    url = f'{server_url}?auth-token={self._token}&clientId={client_id}&protocol=2'
                    await asyncio.wait_for(instance['socket'].connect(url, socketio_path='ws',
                                                                      headers={'Client-Id': client_id}),
                                           timeout=self._connect_timeout)
                    await asyncio.wait_for(instance['connectResult'], self._connect_timeout)
                    reconnected = True
                    instance['isReconnecting'] = False
                    await self._fire_reconnected(instance_number, socket_instance_index, region)
                    await instance['socket'].wait()
                except Exception as err:
                    instance['connectResult'].cancel()
                    instance['connectResult'] = None

    async def rpc_request_all_instances(self, account_id: str, request: dict, reliability=None,
                                        timeout_in_seconds=None):
        """Simultaneously sends RPC requests to all synchronized instances.

        Args:
            account_id: Metatrader account id.
            request: Base request data
            reliability: Account reliability.
            timeout_in_seconds: Request timeout in seconds.
        """
        if reliability == 'high':
            async def generate_rpc_request(instance_number):
                req = copy(request)
                req['instanceIndex'] = instance_number
                return await self.rpc_request(account_id, req, timeout_in_seconds)
            return await promise_any([
                asyncio.create_task(generate_rpc_request(0)),
                asyncio.create_task(generate_rpc_request(1))
            ])
        else:
            return await self.rpc_request(account_id, request, timeout_in_seconds)

    async def rpc_request(self, account_id: str, request: dict, timeout_in_seconds: float = None) -> Coroutine:
        """Makes a RPC request.

        Args:
            account_id: Metatrader account id.
            request: Base request data.
            timeout_in_seconds: Request timeout in seconds.
        """
        socket_instance_index = None
        instance_number = 0
        region = self.get_account_region(account_id)
        self._refresh_account_region(account_id)
        if 'instanceIndex' in request and request['instanceIndex'] is not None:
            instance_number = request['instanceIndex']
        else:
            instance = next((i for i in self._connectedHosts.keys() if (i.startswith(account_id))), None)
            if instance:
                instance_number = int(instance.split(':')[1])

            if 'application' not in request or request['application'] != 'RPC':
                request = copy(request)
                request['instanceIndex'] = instance_number

        if instance_number not in self._socketInstancesByAccounts:
            self._socketInstancesByAccounts[instance_number] = {}

        if region not in self._socketInstances:
            self._socketInstances[region] = {}

        if instance_number not in self._socketInstances[region]:
            self._socketInstances[region][instance_number] = []

        if account_id in self._socketInstancesByAccounts[instance_number]:
            socket_instance_index = self._socketInstancesByAccounts[instance_number][account_id]
        else:
            while self._subscribeLock and \
                ((date(self._subscribeLock['recommendedRetryTime']).timestamp() > datetime.now().timestamp() and
                  len(self.subscribed_account_ids(instance_number, None, region)) <
                  self._subscribeLock['lockedAtAccounts']) or
                 (date(self._subscribeLock['lockedAtTime']).timestamp() + self._subscribeCooldownInSeconds >
                  datetime.now().timestamp() and
                  len(self.subscribed_account_ids(instance_number, None, region)) >=
                  self._subscribeLock['lockedAtAccounts'])):
                await asyncio.sleep(1)
            for index in range(len(self._socketInstances[region][instance_number])):
                account_counter = len(self.get_assigned_accounts(instance_number, index, region))
                instance = self.socket_instances[region][instance_number][index]
                if instance['subscribeLock']:
                    if instance['subscribeLock']['type'] == 'LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_USER_PER_SERVER' and \
                            (date(instance['subscribeLock']['recommendedRetryTime']).timestamp() >
                             datetime.now().timestamp() or
                             len(self.subscribed_account_ids(instance_number, index, region)) >=
                             instance['subscribeLock']['lockedAtAccounts']):
                        continue
                    if instance['subscribeLock']['type'] == 'LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_SERVER' and \
                            (date(instance['subscribeLock']['recommendedRetryTime']).timestamp() >
                             datetime.now().timestamp() and
                             len(self.subscribed_account_ids(instance_number, index, region)) >=
                             instance['subscribeLock']['lockedAtAccounts']):
                        continue
                if account_counter < self._maxAccountsPerInstance:
                    socket_instance_index = index
                    break
            if socket_instance_index is None:
                socket_instance_index = len(self._socketInstances[region][instance_number])
                await self.connect(instance_number, region)
            self._socketInstancesByAccounts[instance_number][account_id] = socket_instance_index
        instance = self._socketInstances[region][instance_number][socket_instance_index]
        start_time = datetime.now()
        while not instance['resolved'] and (start_time + timedelta(seconds=self._connect_timeout) > datetime.now()):
            await asyncio.sleep(1)
        if not instance['resolved']:
            raise TimeoutException(f"MetaApi websocket client request of account {account_id} timed out because "
                                   "socket client failed to connect to the server.")
        if request['type'] == 'subscribe':
            request['sessionId'] = instance['sessionId']
        if request['type'] in ['trade', 'subscribe']:
            return await self._make_request(account_id, instance_number, request, timeout_in_seconds)
        retry_counter = 0
        while True:
            try:
                return await self._make_request(account_id, instance_number, request, timeout_in_seconds)
            except TooManyRequestsException as err:
                calc_retry_counter = retry_counter
                calc_request_time = 0
                while calc_retry_counter < self._retries:
                    calc_retry_counter += 1
                    calc_request_time += min(pow(2, calc_retry_counter) * self._minRetryDelayInSeconds,
                                             self._maxRetryDelayInSeconds)

                retry_time = date(err.metadata['recommendedRetryTime']).timestamp()
                if (datetime.now().timestamp() + calc_request_time) > retry_time and retry_counter < \
                        self._retries:
                    if datetime.now().timestamp() < retry_time:
                        await asyncio.sleep(retry_time - datetime.now().timestamp())
                    retry_counter += 1
                else:
                    raise err
                if account_id not in self._socketInstancesByAccounts[instance_number]:
                    raise err
            except Exception as err:
                if err.__class__.__name__ in ['NotSynchronizedException', 'TimeoutException',
                                              'NotAuthenticatedException', 'InternalException'] and retry_counter < \
                        self._retries:
                    await asyncio.sleep(min(pow(2, retry_counter) * self._minRetryDelayInSeconds,
                                            self._maxRetryDelayInSeconds))
                    retry_counter += 1
                else:
                    raise err
                if instance_number not in self._socketInstancesByAccounts or \
                        account_id not in self._socketInstancesByAccounts[instance_number]:
                    raise err

    async def _make_request(self, account_id: str, instance_number: int, request: dict,
                            timeout_in_seconds: float = None):
        socket_instance = self._get_socket_instance_by_account(account_id, instance_number)
        if 'requestId' in request:
            request_id = request['requestId']
        else:
            request_id = random_id()
            request['requestId'] = request_id
        request['timestamps'] = {'clientProcessingStarted': format_date(datetime.now())}
        socket_instance['requestResolves'][request_id] = asyncio.Future()
        socket_instance['requestResolves'][request_id].type = request['type']
        request['accountId'] = account_id
        request['application'] = request['application'] if 'application' in request else self._application

        resolve = None
        if request['type'] == 'unsubscribe' or request['application'] == 'RPC' or (
                'instanceIndex' in request and request['instanceIndex'] == socket_instance['instanceNumber']):
            self._logger.debug(f'{account_id}: Sending request: {json.dumps(request)}')
            await socket_instance['socket'].emit('request', request)
            try:
                resolve = await asyncio.wait_for(socket_instance['requestResolves'][request_id],
                                                 timeout=timeout_in_seconds or self._request_timeout)
            except asyncio.TimeoutError:
                if request_id in socket_instance['requestResolves']:
                    del socket_instance['requestResolves'][request_id]
                raise TimeoutException(f"MetaApi websocket client request {request['requestId']} of type "
                                       f"{request['type']} timed out. Please make sure your account is connected "
                                       f"to broker before retrying your request.")
        else:
            self._logger.debug(f'{account_id}:{request["instanceIndex"]}: skipping request because it is being sent ' +
                               f'to the socket of the wrong instance index, request={json.dumps(request)}')
        return resolve

    def _convert_error(self, data) -> Exception:
        if data['error'] == 'ValidationError':
            return ValidationException(data['message'], data['details'] if 'details' in data else None)
        elif data['error'] == 'NotFoundError':
            return NotFoundException(data['message'])
        elif data['error'] == 'NotSynchronizedError':
            return NotSynchronizedException(data['message'])
        elif data['error'] == 'TimeoutError':
            return TimeoutException(data['message'])
        elif data['error'] == 'NotAuthenticatedError':
            return NotConnectedException(data['message'])
        elif data['error'] == 'TradeError':
            return TradeException(data['message'], data['numericCode'], data['stringCode'])
        elif data['error'] == 'UnauthorizedError':
            self.close()
            return UnauthorizedException(data['message'])
        elif data['error'] == 'TooManyRequestsError':
            return TooManyRequestsException(data['message'], data['metadata'])
        else:
            return InternalException(data['message'])

    def _format_request(self, packet: dict or list):
        if not isinstance(packet, str):
            for field in packet:
                value = packet[field]
                if isinstance(value, datetime):
                    packet[field] = format_date(value)
                elif isinstance(value, list):
                    for item in value:
                        self._format_request(item)
                elif isinstance(value, dict):
                    self._format_request(value)

    def _convert_iso_time_to_date(self, packet):
        if not isinstance(packet, str):
            for field in packet:
                value = packet[field]
                if isinstance(value, str) and re.search('time|Time', field) and not \
                        re.search('brokerTime|BrokerTime|timeframe', field):
                    packet[field] = date(value)
                if isinstance(value, list):
                    for item in value:
                        self._convert_iso_time_to_date(item)
                if isinstance(value, dict):
                    self._convert_iso_time_to_date(value)
            if packet and 'timestamps' in packet:
                for field in packet['timestamps']:
                    packet['timestamps'][field] = date(packet['timestamps'][field])
            if packet and 'type' in packet and packet['type'] == 'prices':
                if 'prices' in packet:
                    for price in packet['prices']:
                        if 'timestamps' in price:
                            for field in price['timestamps']:
                                if isinstance(price['timestamps'][field], str):
                                    price['timestamps'][field] = date(price['timestamps'][field])

    async def _process_synchronization_packet(self, data):
        try:
            instance_number = data['instanceIndex'] if 'instanceIndex' in data else 0
            socket_instance = self._get_socket_instance_by_account(data['accountId'], instance_number)
            if 'synchronizationId' in data and socket_instance:
                socket_instance['synchronizationThrottler'].update_synchronization_id(data['synchronizationId'])
            instance_id = data['accountId'] + ':' + str(instance_number) + ':' + \
                (data['host'] if 'host' in data else '0')
            instance_index = str(instance_number) + ':' + (data['host'] if 'host' in data else '0')

            def is_only_active_instance():
                active_instance_ids = list(
                    filter(lambda instance: instance.startswith(
                        data['accountId'] + ':' + str(instance_number)), self._connectedHosts.keys()))
                return len(active_instance_ids) == 1 and active_instance_ids[0] == instance_id

            def cancel_disconnect_timer():
                if instance_id in self._status_timers:
                    self._status_timers[instance_id].cancel()

            def reset_disconnect_timer():
                async def disconnect():
                    await asyncio.sleep(60)
                    if is_only_active_instance():
                        self._subscriptionManager.on_timeout(data["accountId"], instance_number)
                    self.queue_event(data["accountId"], f'{instance_index}:onDisconnected',
                                     lambda: on_disconnected(True))

                cancel_disconnect_timer()
                self._status_timers[instance_id] = asyncio.create_task(disconnect())

            async def on_disconnected(is_timeout: bool = False):
                if instance_id in self._connectedHosts:
                    if is_only_active_instance():
                        on_disconnected_tasks: List[Coroutine] = []
                        if not is_timeout:
                            on_disconnected_tasks.append(
                                self._subscriptionManager.on_disconnected(data['accountId'], instance_number))

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_disconnected(listener: SynchronizationListener):
                                    return lambda: listener.on_disconnected(instance_index)

                                on_disconnected_tasks.append(self._process_event(run_on_disconnected(listener),
                                                             f'{data["accountId"]}:{instance_index}:on_disconnected'))
                        if len(on_disconnected_tasks) > 0:
                            await asyncio.gather(*on_disconnected_tasks)

                    on_stream_closed_tasks: List[Coroutine] = []
                    self._packetOrderer.on_stream_closed(instance_id)
                    if socket_instance:
                        socket_instance['synchronizationThrottler'].remove_id_by_parameters(
                            data['accountId'], instance_number, data['host'] if 'host' in data else None)

                    if data['accountId'] in self._synchronizationListeners:
                        for listener in self._synchronizationListeners[data['accountId']]:
                            def run_on_stream_closed(listener: SynchronizationListener):
                                return lambda: listener.on_stream_closed(instance_index)

                            on_stream_closed_tasks.append(self._process_event(
                                run_on_stream_closed(listener),
                                f'{data["accountId"]}:{instance_index}:on_stream_closed'))
                    if len(on_stream_closed_tasks) > 0:
                        await asyncio.gather(*on_stream_closed_tasks)
                    if instance_id in self._connectedHosts:
                        del self._connectedHosts[instance_id]

            if data['type'] == 'authenticated':
                reset_disconnect_timer()
                if 'sessionId' not in data or socket_instance and data['sessionId'] == socket_instance['sessionId']:
                    if 'host' in data:
                        self._connectedHosts[instance_id] = data['host']

                    on_connected_tasks: List[Coroutine] = []

                    if data['accountId'] in self._synchronizationListeners:
                        for listener in self._synchronizationListeners[data['accountId']]:

                            def run_on_connected(listener):
                                return lambda: listener.on_connected(instance_index, data['replicas'])

                            on_connected_tasks.append(self._process_event(
                                run_on_connected(listener),
                                f'{data["accountId"]}:{instance_index}:on_connected'))
                        self._subscriptionManager.cancel_subscribe(data['accountId'] + ':' + str(instance_number))
                    if data['replicas'] == 1:
                        self._subscriptionManager.cancel_account(data['accountId'])
                    else:
                        self._subscriptionManager.cancel_subscribe(data['accountId'] + ':' + str(instance_number))
                    if len(on_connected_tasks) > 0:
                        await asyncio.gather(*on_connected_tasks)
            elif data['type'] == 'disconnected':
                cancel_disconnect_timer()
                await on_disconnected()
            elif data['type'] == 'synchronizationStarted':
                on_sync_started_tasks: List[Coroutine] = []
                self._synchronizationFlags[data['synchronizationId']] = {
                    'accountId': data['accountId'],
                    'instanceNumber': instance_number,
                    'positionsUpdated': data['positionsUpdated'] if 'positionsUpdated' in data else True,
                    'ordersUpdated': data['ordersUpdated'] if 'ordersUpdated' in data else True
                }
                self._synchronizationIdByInstance[instance_id] = data['synchronizationId']

                if data['accountId'] in self._synchronizationListeners:
                    for listener in self._synchronizationListeners[data['accountId']]:
                        def run_on_sync_started(listener: SynchronizationListener):
                            return lambda: listener.on_synchronization_started(
                                instance_index, specifications_updated=data['specificationsUpdated'] if
                                'specificationsUpdated' in data else True, positions_updated=data['positionsUpdated']
                                if 'positionsUpdated' in data else True, orders_updated=data['ordersUpdated'] if
                                'ordersUpdated' in data else True, synchronization_id=data['synchronizationId'])

                        on_sync_started_tasks.append(
                            self._process_event(run_on_sync_started(listener),
                                                f'{data["accountId"]}:{instance_index}:on_synchronization_started'))
                if len(on_sync_started_tasks) > 0:
                    await asyncio.gather(*on_sync_started_tasks)
            elif data['type'] == 'accountInformation':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                if data['accountInformation'] and (data['accountId'] in self._synchronizationListeners):
                    on_account_information_updated_tasks: List[asyncio.Task] = []

                    async def run_on_account_info(listener: SynchronizationListener):
                        try:
                            await self._process_event(lambda: listener.on_account_information_updated(
                                instance_index, data['accountInformation']),
                                f'{data["accountId"]}:{instance_index}:on_account_information_updated', True)
                            if 'synchronizationId' in data and data['synchronizationId'] in \
                                    self._synchronizationFlags and \
                                    not self._synchronizationFlags[data['synchronizationId']]['positionsUpdated']:
                                await self._process_event(lambda: listener.on_positions_synchronized(
                                    instance_index, data['synchronizationId']),
                                    f'{data["accountId"]}:{instance_index}:on_positions_synchronized', True)
                                if not self._synchronizationFlags[data['synchronizationId']]['ordersUpdated']:
                                    await self._process_event(lambda: listener.on_pending_orders_synchronized(
                                            instance_index, data['synchronizationId']),
                                            f'{data["accountId"]}:{instance_index}:on_pending_orders_synchronized',
                                            True)
                        except Exception as err:
                            self._logger.error(f'{data["accountId"]}:{instance_index}: Failed to notify listener '
                                               f'about accountInformation event ' + string_format_error(err))

                    for listener in self._synchronizationListeners[data['accountId']]:
                        on_account_information_updated_tasks.append(
                            asyncio.create_task(run_on_account_info(listener)))
                    if len(on_account_information_updated_tasks) > 0:
                        await asyncio.gather(*on_account_information_updated_tasks)
                    if 'synchronizationId' in data and data['synchronizationId'] in self._synchronizationFlags and \
                            not self._synchronizationFlags[data['synchronizationId']]['positionsUpdated'] and \
                            not self._synchronizationFlags[data['synchronizationId']]['ordersUpdated']:
                        del self._synchronizationFlags[data['synchronizationId']]
            elif data['type'] == 'deals':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                if 'deals' in data:
                    for deal in data['deals']:
                        on_deal_added_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_deal_added(listener: SynchronizationListener):
                                    return lambda: listener.on_deal_added(instance_index, deal)

                                on_deal_added_tasks.append(self._process_event(
                                    run_on_deal_added(listener),
                                    f'{data["accountId"]}:{instance_index}:on_deal_added'))
                        if len(on_deal_added_tasks) > 0:
                            await asyncio.gather(*on_deal_added_tasks)
            elif data['type'] == 'orders':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                on_order_updated_tasks: List[asyncio.Task] = []

                async def run_on_pending_orders_replaced(listener: SynchronizationListener):
                    try:
                        if 'orders' in data:
                            await self._process_event(
                                lambda: listener.on_pending_orders_replaced(instance_index, data['orders']),
                                f'{data["accountId"]}:{instance_index}:on_pending_orders_replaced', True)
                        await self._process_event(
                            lambda: listener.on_pending_orders_synchronized(instance_index, data['synchronizationId']),
                            f'{data["accountId"]}:{instance_index}:on_pending_orders_synchronized', True)
                    except Exception as err:
                        self._logger.error(f'{data["accountId"]}:{instance_index}: Failed to notify listener about '
                                           f'orders event ' + string_format_error(err))

                if data['accountId'] in self._synchronizationListeners:
                    for listener in self._synchronizationListeners[data['accountId']]:
                        on_order_updated_tasks.append(asyncio.create_task(run_on_pending_orders_replaced(listener)))
                if len(on_order_updated_tasks) > 0:
                    await asyncio.gather(*on_order_updated_tasks)
                if data['synchronizationId'] in self._synchronizationFlags:
                    del self._synchronizationFlags[data['synchronizationId']]
            elif data['type'] == 'historyOrders':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                if 'historyOrders' in data:
                    for historyOrder in data['historyOrders']:
                        on_history_order_added_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_order_added(listener: SynchronizationListener):
                                    return lambda: listener.on_history_order_added(instance_index, historyOrder)

                                on_history_order_added_tasks.append(
                                    self._process_event(
                                        run_on_order_added(listener),
                                        f'{data["accountId"]}:{instance_index}:on_history_order_added'))
                        if len(on_history_order_added_tasks) > 0:
                            await asyncio.gather(*on_history_order_added_tasks)
            elif data['type'] == 'positions':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                on_positions_replaced_tasks: List[asyncio.Task] = []

                async def run_on_positions_replaced(listener: SynchronizationListener):
                    try:
                        if 'positions' in data:
                            await self._process_event(
                                lambda: listener.on_positions_replaced(instance_index, data['positions']),
                                f'{data["accountId"]}:{instance_index}:on_positions_replaced', True)
                        await self._process_event(
                            lambda: listener.on_positions_synchronized(instance_index, data['synchronizationId']),
                            f'{data["accountId"]}:{instance_index}:on_positions_synchronized', True)
                        if data['synchronizationId'] in self._synchronizationFlags and \
                                not self._synchronizationFlags[data['synchronizationId']]['ordersUpdated']:
                            await self._process_event(
                                lambda: listener.on_pending_orders_synchronized(
                                    instance_index, data['synchronizationId']),
                                f'{data["accountId"]}:{instance_index}:on_pending_orders_synchronized', True)
                    except Exception as err:
                        self._logger.error(f'{data["accountId"]}:{instance_index}: Failed to notify listener about '
                                           f'positions event ' + string_format_error(err))

                if data['accountId'] in self._synchronizationListeners:
                    for listener in self._synchronizationListeners[data['accountId']]:
                        on_positions_replaced_tasks.append(asyncio.create_task(run_on_positions_replaced(listener)))
                if len(on_positions_replaced_tasks) > 0:
                    await asyncio.gather(*on_positions_replaced_tasks)
                if data['synchronizationId'] in self._synchronizationFlags and \
                        not self._synchronizationFlags[data['synchronizationId']]['ordersUpdated']:
                    del self._synchronizationFlags[data['synchronizationId']]
            elif data['type'] == 'update':
                if 'accountInformation' in data and (data['accountId'] in self._synchronizationListeners):
                    on_account_information_updated_tasks: List[Coroutine] = []

                    for listener in self._synchronizationListeners[data['accountId']]:
                        def run_on_account_information_updated(listener: SynchronizationListener):
                            return lambda: listener.on_account_information_updated(instance_index,
                                                                                   data['accountInformation'])

                        on_account_information_updated_tasks.append(
                            self._process_event(run_on_account_information_updated(listener),
                                                f'{data["accountId"]}:{instance_index}:on_account_information_updated'))
                    if len(on_account_information_updated_tasks) > 0:
                        await asyncio.gather(*on_account_information_updated_tasks)
                if 'updatedPositions' in data:
                    for position in data['updatedPositions']:
                        on_position_updated_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_position_updated(listener: SynchronizationListener):
                                    return lambda: listener.on_position_updated(instance_index, position)

                                on_position_updated_tasks.append(
                                    self._process_event(run_on_position_updated(listener),
                                                        f'{data["accountId"]}:{instance_index}:on_position_updated'))
                        if len(on_position_updated_tasks) > 0:
                            await asyncio.gather(*on_position_updated_tasks)
                if 'removedPositionIds' in data:
                    for positionId in data['removedPositionIds']:
                        on_position_removed_tasks: List[asyncio.create_task] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_position_removed(listener: SynchronizationListener):
                                    return lambda: listener.on_position_removed(instance_index, positionId)

                                on_position_removed_tasks.append(
                                    self._process_event(run_on_position_removed(listener),
                                                        f'{data["accountId"]}:{instance_index}:on_position_removed'))
                        if len(on_position_removed_tasks) > 0:
                            await asyncio.gather(*on_position_removed_tasks)
                if 'updatedOrders' in data:
                    for order in data['updatedOrders']:
                        on_order_updated_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_pending_order_updated(listener: SynchronizationListener):
                                    return lambda: listener.on_pending_order_updated(instance_index, order)

                                on_order_updated_tasks.append(
                                    self._process_event(
                                        run_on_pending_order_updated(listener),
                                        f'{data["accountId"]}:{instance_index}:on_pending_order_updated'))
                        if len(on_order_updated_tasks) > 0:
                            await asyncio.gather(*on_order_updated_tasks)
                if 'completedOrderIds' in data:
                    for orderId in data['completedOrderIds']:
                        on_order_completed_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_pending_order_completed(listener: SynchronizationListener):
                                    return lambda: listener.on_pending_order_completed(instance_index, orderId)

                                on_order_completed_tasks.append(
                                    self._process_event(
                                        run_on_pending_order_completed(listener),
                                        f'{data["accountId"]}:{instance_index}:on_pending_order_completed'))
                        if len(on_order_completed_tasks) > 0:
                            await asyncio.gather(*on_order_completed_tasks)
                if 'historyOrders' in data:
                    for historyOrder in data['historyOrders']:
                        on_history_order_added_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_history_order_added(listener: SynchronizationListener):
                                    return lambda: listener.on_history_order_added(instance_index, historyOrder)

                                on_history_order_added_tasks.append(
                                    self._process_event(
                                        run_on_history_order_added(listener),
                                        f'{data["accountId"]}:{instance_index}:on_history_order_added'))
                        if len(on_history_order_added_tasks) > 0:
                            await asyncio.gather(*on_history_order_added_tasks)
                if 'deals' in data:
                    for deal in data['deals']:
                        on_deal_added_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_deal_added(listener: SynchronizationListener):
                                    return lambda: listener.on_deal_added(instance_index, deal)

                                on_deal_added_tasks.append(
                                    self._process_event(run_on_deal_added(listener),
                                                        f'{data["accountId"]}:{instance_index}:on_deal_added'))
                        if len(on_deal_added_tasks) > 0:
                            await asyncio.gather(*on_deal_added_tasks)
                if 'timestamps' in data:
                    data['timestamps']['clientProcessingFinished'] = datetime.now()
                    on_update_tasks: List[Coroutine] = []

                    for listener in self._latencyListeners:
                        def run_on_update(listener: LatencyListener):
                            return lambda: listener.on_update(data['accountId'], data['timestamps'])

                        on_update_tasks.append(self._process_event(run_on_update(listener),
                                                                   f'{data["accountId"]}:{instance_index}:on_update'))

                    if len(on_update_tasks) > 0:
                        await asyncio.gather(*on_update_tasks)
            elif data['type'] == 'dealSynchronizationFinished':
                if 'synchronizationId' in data and \
                        data['synchronizationId'] != self._synchronizationIdByInstance[instance_id]:
                    del self._synchronizationIdByInstance[instance_id]
                    return
                if data['accountId'] in self._synchronizationListeners:
                    on_deal_synchronization_finished_tasks: List[Coroutine] = []
                    if socket_instance:
                        socket_instance['synchronizationThrottler'] \
                            .remove_synchronization_id(data['synchronizationId'])

                    def run_on_deals_synchronized(listener: SynchronizationListener):
                        return lambda: listener.on_deals_synchronized(instance_index, data['synchronizationId'])

                    for listener in self._synchronizationListeners[data['accountId']]:
                        on_deal_synchronization_finished_tasks.append(
                            self._process_event(run_on_deals_synchronized(listener),
                                                f'{data["accountId"]}:{instance_index}:on_deals_synchronized'))
                    if len(on_deal_synchronization_finished_tasks) > 0:
                        await asyncio.gather(*on_deal_synchronization_finished_tasks)
            elif data['type'] == 'orderSynchronizationFinished':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                if data['accountId'] in self._synchronizationListeners:
                    on_order_synchronization_finished_tasks: List[Coroutine] = []

                    for listener in self._synchronizationListeners[data['accountId']]:
                        def run_on_history_orders_synchronized(listener: SynchronizationListener):
                            return lambda: listener.on_history_orders_synchronized(instance_index,
                                                                                   data['synchronizationId'])

                        on_order_synchronization_finished_tasks.append(
                            self._process_event(
                                run_on_history_orders_synchronized(listener),
                                f'{data["accountId"]}:{instance_index}:on_history_orders_synchronized'))
                    if len(on_order_synchronization_finished_tasks) > 0:
                        await asyncio.gather(*on_order_synchronization_finished_tasks)
            elif data['type'] == 'status':
                if instance_id not in self._connectedHosts:
                    if instance_id in self._status_timers and 'authenticated' in data and data['authenticated'] \
                            and (self._subscriptionManager.is_disconnected_retry_mode(
                            data['accountId'], instance_number) or not
                            self._subscriptionManager.is_account_subscribing(data['accountId'], instance_number)):
                        self._subscriptionManager.cancel_subscribe(data['accountId'] + ':' + str(instance_number))
                        await asyncio.sleep(0.01)
                        self._logger.info(f'it seems like we are not connected to a ' +
                                          'running API server yet, retrying subscription for account ' + instance_id)
                        self.ensure_subscribe(data['accountId'], instance_number)
                else:
                    reset_disconnect_timer()
                    on_broker_connection_status_changed_tasks: List[Coroutine] = []

                    for listener in self._synchronizationListeners[data['accountId']]:
                        def run_on_broker_connection_status_changed(listener: SynchronizationListener):
                            return lambda: listener.on_broker_connection_status_changed(instance_index,
                                                                                        bool(data['connected']))

                        on_broker_connection_status_changed_tasks.append(
                            self._process_event(
                                run_on_broker_connection_status_changed(listener),
                                f'{data["accountId"]}:{instance_index}:on_broker_connection_status_changed'))
                    if len(on_broker_connection_status_changed_tasks) > 0:
                        await asyncio.gather(*on_broker_connection_status_changed_tasks)
                    if 'healthStatus' in data:
                        on_health_status_tasks: List[Coroutine] = []

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                def run_on_health_status(listener: SynchronizationListener):
                                    return lambda: listener.on_health_status(instance_index, data['healthStatus'])

                                on_health_status_tasks.append(
                                    self._process_event(run_on_health_status(listener),
                                                        f'{data["accountId"]}:{instance_index}:on_health_status'))
                            if len(on_health_status_tasks) > 0:
                                await asyncio.gather(*on_health_status_tasks)
            elif data['type'] == 'downgradeSubscription':
                self._logger.info(
                    f'{data["accountId"]}:{instance_index}: Market data subscriptions for symbol {data["symbol"]}'
                    f' were downgraded by the server due to rate limits. Updated subscriptions: '
                    f'{json.dumps(data["updates"]) if "updates" in data else ""}, removed subscriptions: '
                    f'{json.dumps(data["unsubscriptions"]) if "unsubscriptions" in data else ""}. Please read '
                    'https://metaapi.cloud/docs/client/rateLimiting/ for more details.')

                on_subscription_downgrade_tasks = []

                if data['accountId'] in self._synchronizationListeners:
                    for listener in self._synchronizationListeners[data['accountId']]:
                        def run_on_subscription_downgraded(listener: SynchronizationListener):
                            return lambda: listener.on_subscription_downgraded(
                                instance_index, data['symbol'], data['updates'] if 'updates' in data else None,
                                data['unsubscriptions'] if 'unsubscriptions' in data else None)

                        on_subscription_downgrade_tasks.append(
                            self._process_event(run_on_subscription_downgraded(listener),
                                                f'{data["accountId"]}:{instance_index}:on_subscription_downgraded'))
                    if len(on_subscription_downgrade_tasks) > 0:
                        await asyncio.gather(*on_subscription_downgrade_tasks)
            elif data['type'] == 'specifications':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                on_symbol_specifications_updated_tasks: List[Coroutine] = []

                def run_on_symbol_specifications_updated(listener: SynchronizationListener):
                    return lambda: listener.on_symbol_specifications_updated(
                        instance_index, data['specifications'] if 'specifications' in data else [],
                        data['removedSymbols'] if 'removedSymbols' in data else [])

                if data['accountId'] in self._synchronizationListeners:
                    for listener in self._synchronizationListeners[data['accountId']]:
                        on_symbol_specifications_updated_tasks.append(
                            self._process_event(
                                run_on_symbol_specifications_updated(listener),
                                f'{data["accountId"]}:{instance_index}:on_symbol_specifications_updated'))
                    if len(on_symbol_specifications_updated_tasks) > 0:
                        await asyncio.gather(*on_symbol_specifications_updated_tasks)

                if 'specifications' in data:
                    for specification in data['specifications']:
                        on_symbol_specification_updated_tasks: List[Coroutine] = []

                        def run_on_symbol_specification_updated(listener: SynchronizationListener):
                            return lambda: listener.on_symbol_specification_updated(instance_index, specification)

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                on_symbol_specification_updated_tasks.append(
                                    self._process_event(
                                        run_on_symbol_specification_updated(listener),
                                        f'{data["accountId"]}:{instance_index}:on_symbol_specification_updated'))
                            if len(on_symbol_specification_updated_tasks) > 0:
                                await asyncio.gather(*on_symbol_specification_updated_tasks)

                if 'removedSymbols' in data:
                    for removed_symbol in data['removedSymbols']:
                        on_symbol_specification_removed_tasks = []

                        def run_on_symbol_specification_removed(listener: SynchronizationListener):
                            return lambda: listener.on_symbol_specification_removed(instance_index, removed_symbol)

                        if data['accountId'] in self._synchronizationListeners:
                            for listener in self._synchronizationListeners[data['accountId']]:
                                on_symbol_specification_removed_tasks.append(
                                    self._process_event(
                                        run_on_symbol_specification_removed(listener),
                                        f'{data["accountId"]}:{instance_index}:on_symbol_specification_removed'))
                            if len(on_symbol_specification_removed_tasks) > 0:
                                await asyncio.gather(*on_symbol_specification_removed_tasks)
            elif data['type'] == 'prices':
                if 'synchronizationId' in data and (
                        instance_id not in self._synchronizationIdByInstance or data['synchronizationId'] !=
                        self._synchronizationIdByInstance[instance_id]):
                    return
                prices = data['prices'] if 'prices' in data else []
                candles = data['candles'] if 'candles' in data else []
                ticks = data['ticks'] if 'ticks' in data else []
                books = data['books'] if 'books' in data else []
                on_symbol_prices_updated_tasks: List[Coroutine] = []
                if data['accountId'] in self._synchronizationListeners:
                    equity = data['equity'] if 'equity' in data else None
                    margin = data['margin'] if 'margin' in data else None
                    free_margin = data['freeMargin'] if 'freeMargin' in data else None
                    margin_level = data['marginLevel'] if 'marginLevel' in data else None
                    account_currency_exchange_rate = data['accountCurrencyExchangeRate'] if \
                        'accountCurrencyExchangeRate' in data else None

                    for listener in self._synchronizationListeners[data['accountId']]:
                        if len(prices):
                            def run_on_symbol_prices_updated(listener: SynchronizationListener):
                                return lambda: listener.on_symbol_prices_updated(
                                    instance_index, prices, equity, margin, free_margin, margin_level,
                                    account_currency_exchange_rate)

                            on_symbol_prices_updated_tasks.append(
                                self._process_event(run_on_symbol_prices_updated(listener),
                                                    f'{data["accountId"]}:{instance_index}:on_symbol_prices_updated'))

                        if len(candles):
                            def run_on_candles_updated(listener: SynchronizationListener):
                                return lambda: listener.on_candles_updated(
                                    instance_index, candles, equity, margin, free_margin, margin_level,
                                    account_currency_exchange_rate)

                            on_symbol_prices_updated_tasks.append(
                                self._process_event(run_on_candles_updated(listener),
                                                    f'{data["accountId"]}:{instance_index}:on_candles_updated'))

                        if len(ticks):
                            def run_on_ticks_updated(listener: SynchronizationListener):
                                return lambda: listener.on_ticks_updated(
                                    instance_index, ticks, equity, margin, free_margin, margin_level,
                                    account_currency_exchange_rate)

                            on_symbol_prices_updated_tasks.append(
                                self._process_event(run_on_ticks_updated(listener),
                                                    f'{data["accountId"]}:{instance_index}:on_ticks_updated'))

                        if len(books):
                            def run_on_books_updated(listener: SynchronizationListener):
                                return lambda: listener.on_books_updated(
                                    instance_index, books, equity, margin, free_margin, margin_level,
                                    account_currency_exchange_rate)

                            on_symbol_prices_updated_tasks.append(
                                self._process_event(run_on_books_updated(listener),
                                                    f'{data["accountId"]}:{instance_index}:on_books_updated'))

                    if len(on_symbol_prices_updated_tasks) > 0:
                        await asyncio.gather(*on_symbol_prices_updated_tasks)

                for price in prices:
                    on_symbol_price_updated_tasks: List[Coroutine] = []

                    if data['accountId'] in self._synchronizationListeners:
                        for listener in self._synchronizationListeners[data['accountId']]:
                            def run_on_symbol_price_updated(listener: SynchronizationListener):
                                return lambda: listener.on_symbol_price_updated(instance_index, price)

                            on_symbol_price_updated_tasks.append(
                                self._process_event(run_on_symbol_price_updated(listener),
                                                    f'{data["accountId"]}:{instance_index}:on_symbol_price_updated'))
                        if len(on_symbol_price_updated_tasks) > 0:
                            await asyncio.gather(*on_symbol_price_updated_tasks)

                for price in prices:
                    if 'timestamps' in price:
                        price['timestamps']['clientProcessingFinished'] = datetime.now()
                        on_symbol_price_tasks: List[Coroutine] = []

                        for listener in self._latencyListeners:
                            def run_on_symbol_price(listener: LatencyListener):
                                return lambda: listener.on_symbol_price(data['accountId'], price['symbol'],
                                                                        price['timestamps'])

                            on_symbol_price_tasks.append(
                                self._process_event(run_on_symbol_price(listener),
                                                    f'{data["accountId"]}:{instance_index}:on_symbol_price'))
                        if len(on_symbol_price_tasks) > 0:
                            await asyncio.gather(*on_symbol_price_tasks)
        except Exception as err:
            self._logger.error('Failed to process incoming synchronization packet ' + string_format_error(err))

    async def _process_event(self, callable, label: str, throw_error: bool = False):
        start_time = datetime.now().timestamp()
        is_long_event = False
        is_event_done = False

        async def check_long_event():
            await asyncio.sleep(1)
            if not is_event_done:
                nonlocal is_long_event
                is_long_event = True
                self._logger.warn(f'{label}: event is taking more than 1 second to process')

        asyncio.create_task(check_long_event())
        try:
            await callable()
        except Exception as err:
            if throw_error:
                raise err

            self._logger.error(f'{label}: event failed with error ' + string_format_error(err))
        is_event_done = True
        if is_long_event:
            self._logger.warn(f'{label}: finished in {math.floor(datetime.now().timestamp() - start_time)} seconds')

    async def _fire_reconnected(self, instance_number: int, socket_instance_index: int, region: str):
        reconnect_listeners = []
        for listener in self._reconnectListeners:
            if listener['accountId'] in self._socketInstancesByAccounts[instance_number] and \
                    self._socketInstancesByAccounts[instance_number][listener['accountId']] == \
                    socket_instance_index and self.get_account_region(listener['accountId']) == region:
                reconnect_listeners.append(listener)

        for synchronization_id in list(self._synchronizationFlags.keys()):
            account_id = self._synchronizationFlags[synchronization_id]['accountId']
            if account_id in self._socketInstancesByAccounts[instance_number] and \
                    self._socketInstancesByAccounts[instance_number][account_id] == socket_instance_index and \
                    self._synchronizationFlags[synchronization_id]['instanceNumber'] == instance_number and \
                    account_id in self._regionsByAccounts and self._regionsByAccounts[account_id]['region'] == region:
                del self._synchronizationFlags[synchronization_id]

        try:
            reconnect_account_ids = list(map(lambda listener: listener['accountId'], reconnect_listeners))
            self._subscriptionManager.on_reconnected(instance_number, socket_instance_index, reconnect_account_ids)
            self._packetOrderer.on_reconnected(reconnect_account_ids)

            for listener in reconnect_listeners:
                async def on_reconnected_task(listener):
                    try:
                        await listener['listener'].on_reconnected()
                    except Exception as err:
                        self._logger.error(f'Failed to notify reconnect listener ' + string_format_error(err))

                asyncio.create_task(on_reconnected_task(listener))
        except Exception as err:
            self._logger.error(f'Failed to process reconnected event ' + string_format_error(err))

    def _get_socket_instance_by_account(self, account_id: str, instance_number: int):
        region = self.get_account_region(account_id)
        if instance_number in self._socketInstancesByAccounts and account_id in \
                self._socketInstancesByAccounts[instance_number]:
            return self._socketInstances[region][instance_number][
                        self._socketInstancesByAccounts[instance_number][account_id]]
        else:
            return None

    async def _get_server_url(self, instance_number: int, socket_instance_index: int, region: str):
        if self._url:
            return self._url

        while self.socket_instances[region][instance_number][socket_instance_index]['connected']:
            try:
                url_settings = await self._httpClient.request({
                    'url': f'https://mt-provisioning-api-v1.{self._domain}/users/current/servers/mt-client-api',
                    'method': 'GET',
                    'headers': {
                        'auth-token': self._token
                    },
                })

                def get_url(hostname):
                    return f'https://{hostname}.{region}-{chr(97 + int(instance_number))}.{url_settings["domain"]}'

                if self._useSharedClientApi:
                    url = get_url(self._hostname)
                else:
                    url = get_url(url_settings['hostname'])

                is_shared_client_api = url == get_url(self._hostname)
                log_message = 'Connecting MetaApi websocket client to the MetaApi server ' + \
                    f'via {url} {"shared" if is_shared_client_api else "dedicated"} server.'
                if self._firstConnect and not is_shared_client_api:
                    log_message += ' Please note that it can take up to 3 minutes for your dedicated server to ' + \
                        'start for the first time. During this time it is OK if you see some connection errors.'
                self._logger.info(log_message)
                return url
            except Exception as err:
                self._logger.error(string_format_error(err))
                await asyncio.sleep(1)

    def _throttle_request(self, type, account_id, instance_number, time_in_ms):
        self._lastRequestsTime[instance_number] = self._lastRequestsTime[instance_number] if \
            instance_number in self._lastRequestsTime else {}
        self._lastRequestsTime[instance_number][type] = \
            self._lastRequestsTime[instance_number][type] if type in self._lastRequestsTime[instance_number] else {}
        last_time = self._lastRequestsTime[instance_number][type][account_id] if \
            account_id in self._lastRequestsTime[instance_number][type] else None
        if last_time is None or last_time < datetime.now().timestamp() - time_in_ms / 1000:
            self._lastRequestsTime[instance_number][type][account_id] = datetime.now().timestamp()
            return last_time is not None
        return False

    def _refresh_account_region(self, account_id: str):
        if account_id in self._regionsByAccounts:
            self._regionsByAccounts[account_id]['lastUsed'] = datetime.now().timestamp()

    def _clear_regions_job(self):
        try:
            date = datetime.now().timestamp()
            for account_id in list(self._regionsByAccounts.keys()):
                data = self._regionsByAccounts[account_id]
                if data['connections'] == 0 and date - data['lastUsed'] > 2 * 60 * 60:
                    del self._regionsByAccounts[account_id]
        except Exception as err:
            self._logger.error(f'Failed to process clear regions job ' + string_format_error(err))
