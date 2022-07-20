from ..clients.metaApi.synchronizationListener import SynchronizationListener
from .models import MetatraderAccountInformation, MetatraderPosition, MetatraderOrder, \
    MetatraderSymbolSpecification, MetatraderSymbolPrice, G1Encoder, G2Encoder, QuoteTime
from ..clients.metaApi.clientApi_client import ClientApiClient
import functools
from typing import List, Dict, Optional, Union
from typing_extensions import TypedDict
import asyncio
from datetime import datetime
from hashlib import md5
from copy import copy, deepcopy
from ..logger import LoggerManager
from operator import itemgetter
import json


class TerminalStateDict(TypedDict, total=False):
    instanceIndex: Union[str, None]
    connected: bool
    connectedToBroker: bool
    accountInformation: Optional[dict]
    positions: List[dict]
    orders: List[dict]
    specificationsBySymbol: dict
    pricesBySymbol: dict
    completedOrders: dict
    removedPositions: dict
    ordersInitialized: bool
    positionsInitialized: bool
    lastUpdateTime: float
    lastSyncUpdateTime: float
    positionsHash: Union[str, None]
    ordersHash: Union[str, None]
    specificationsHash: Union[str, None]
    lastQuoteTime: Union[datetime, None]
    lastQuoteBrokerTime: Union[str, None]


class TerminalStateHashes(TypedDict):
    specificationsMd5: Union[str, None]
    positionsMd5: Union[str, None]
    ordersMd5: Union[str, None]


class TerminalState(SynchronizationListener):
    """Responsible for storing a local copy of remote terminal state."""

    def __init__(self, account_id: str, client_api_client: ClientApiClient):
        """Inits the instance of terminal state class

        Args:
            account_id: Account id.
            client_api_client: Client API client.
        """
        super().__init__()
        self._accountId = account_id
        self._clientApiClient = client_api_client
        self._stateByInstanceIndex = {}
        self._waitForPriceResolves = {}
        self._combinedState = {
            'accountInformation': None,
            'positions': [],
            'orders': [],
            'specificationsBySymbol': {},
            'pricesBySymbol': {},
            'completedOrders': {},
            'removedPositions': {},
            'ordersInitialized': False,
            'positionsInitialized': False,
            'lastUpdateTime': 0,
            'lastQuoteTime': None,
            'lastQuoteBrokerTime': None
        }
        self._logger = LoggerManager.get_logger('TerminalState')

    @property
    def connected(self) -> bool:
        """Returns true if MetaApi has connected to MetaTrader terminal.

        Returns:
            Whether MetaApi has connected to MetaTrader terminal.
        """
        return True in list(map(lambda instance: instance['connected'], self._stateByInstanceIndex.values()))

    @property
    def connected_to_broker(self) -> bool:
        """Returns true if MetaApi has connected to MetaTrader terminal and MetaTrader terminal is connected to broker

        Returns:
             Whether MetaApi has connected to MetaTrader terminal and MetaTrader terminal is connected to broker
        """
        return True in list(map(lambda instance: instance['connectedToBroker'], self._stateByInstanceIndex.values()))

    @property
    def account_information(self) -> MetatraderAccountInformation:
        """Returns a local copy of account information.

        Returns:
            Local copy of account information.
        """
        return self._combinedState['accountInformation']

    @property
    def positions(self) -> List[MetatraderPosition]:
        """Returns a local copy of MetaTrader positions opened.

        Returns:
            A local copy of MetaTrader positions opened.
        """
        return self._combinedState['positions']

    @property
    def orders(self) -> List[MetatraderOrder]:
        """Returns a local copy of MetaTrader orders opened.

        Returns:
            A local copy of MetaTrader orders opened.
        """
        return self._combinedState['orders']

    @property
    def specifications(self) -> List[MetatraderSymbolSpecification]:
        """Returns a local copy of symbol specifications available in MetaTrader trading terminal.

        Returns:
             A local copy of symbol specifications available in MetaTrader trading terminal.
        """
        return list(self._combinedState['specificationsBySymbol'].values())

    async def get_hashes(self, account_type: str, instance_index: str) -> TerminalStateHashes:
        """Returns hashes of terminal state data for incremental synchronization.

        Args:
            account_type: Account type.
            instance_index: Index of instance state to get hashes of.

        Returns:
            A coroutine that resolves with hashes of terminal state data.
        """
        requested_state = self._get_state(instance_index)
        hash_fields = await self._clientApiClient.get_hashing_ignored_field_lists()
        # get latest instance number state
        instance_number = instance_index.split(':')[0]
        instance_number_states = list(filter(
            lambda state_instance_index: state_instance_index.startswith(f'{instance_number}:'),
            self._stateByInstanceIndex.keys()))
        instance_number_states = sorted(
            instance_number_states,
            key=lambda instance_key: itemgetter('lastSyncUpdateTime')(self._stateByInstanceIndex[instance_key]))
        state = self._get_state(instance_number_states[0])

        specifications = copy(list(state['specificationsBySymbol'].values()))
        for i in range(len(specifications)):
            specifications[i] = copy(specifications[i])
        specifications = sorted(specifications, key=lambda s: s['symbol'])
        specification: dict
        for specification in specifications:
            if account_type == 'cloud-g1':
                for field in hash_fields['g1']['specification']:
                    if field in specification:
                        del specification[field]
                for key in list(specification.keys()):
                    if isinstance(specification[key], int) and not isinstance(specification[key], bool) and \
                            key != 'digits':
                        specification[key] = float(specification[key])
            elif account_type == 'cloud-g2':
                for field in hash_fields['g2']['specification']:
                    if field in specification:
                        del specification[field]

        specifications_hash = state['specificationsHash'] or self._get_hash(specifications, account_type) if \
            len(specifications) else None
        state['specificationsHash'] = specifications_hash

        positions = copy(state['positions'])
        for i in range(len(positions)):
            positions[i] = copy(positions[i])
        if account_type == 'cloud-g1':
            positions = sorted(positions, key=lambda p: int(p['id']))
        elif account_type == 'cloud-g2':
            positions = sorted(positions, key=lambda p: p['id'])

        position: dict
        for position in positions:
            if account_type == 'cloud-g1':
                for field in hash_fields['g1']['position']:
                    if field in position:
                        del position[field]
                for key in list(position.keys()):
                    if isinstance(position[key], int) and not isinstance(position[key], bool) and \
                            key != 'magic':
                        position[key] = float(position[key])
            elif account_type == 'cloud-g2':
                for field in hash_fields['g2']['position']:
                    if field in position:
                        del position[field]

        positions_hash = (state['positionsHash'] or self._get_hash(positions, account_type)) if \
            state['positionsInitialized'] else None
        state['positionsHash'] = positions_hash

        orders = copy(state['orders'])
        for i in range(len(orders)):
            orders[i] = copy(orders[i])
        if account_type == 'cloud-g1':
            orders = sorted(orders, key=lambda p: int(p['id']))
        elif account_type == 'cloud-g2':
            orders = sorted(orders, key=lambda p: p['id'])

        order: dict
        for order in orders:
            if account_type == 'cloud-g1':
                for field in hash_fields['g1']['order']:
                    if field in order:
                        del order[field]
                for key in list(order.keys()):
                    if isinstance(order[key], int) and not isinstance(order[key], bool) and \
                            key != 'magic':
                        order[key] = float(order[key])
            elif account_type == 'cloud-g2':
                for field in hash_fields['g2']['order']:
                    if field in order:
                        del order[field]

        orders_hash = (state['ordersHash'] or self._get_hash(orders, account_type)) if \
            state['ordersInitialized'] else None
        state['ordersHash'] = orders_hash

        if requested_state != state:
            requested_state['specificationsBySymbol'] = copy(state['specificationsBySymbol'])
            requested_state['specificationsHash'] = specifications_hash
            requested_state['positions'] = copy(state['positions']) or []
            for i in range(len(requested_state['positions'])):
                requested_state['positions'][i] = copy(requested_state['positions'][i])
            requested_state['positionsHash'] = positions_hash
            requested_state['orders'] = copy(state['orders']) or []
            for i in range(len(requested_state['orders'])):
                requested_state['orders'][i] = copy(requested_state['orders'][i])
            requested_state['ordersHash'] = orders_hash

        return {
            'specificationsMd5': specifications_hash,
            'positionsMd5': positions_hash,
            'ordersMd5': orders_hash
        }

    def specification(self, symbol: str) -> MetatraderSymbolSpecification:
        """Returns MetaTrader symbol specification by symbol.

        Args:
            symbol: Symbol (e.g. currency pair or an index).

        Returns:
            MetatraderSymbolSpecification found or undefined if specification for a symbol is not found.
        """
        return self._combinedState['specificationsBySymbol'][symbol] if \
            (symbol in self._combinedState['specificationsBySymbol']) else None

    def price(self, symbol: str) -> MetatraderSymbolPrice:
        """Returns MetaTrader symbol price by symbol.

        Args:
            symbol: Symbol (e.g. currency pair or an index).

        Returns:
            MetatraderSymbolPrice found or undefined if price for a symbol is not found.
        """
        return self._combinedState['pricesBySymbol'][symbol] if \
            (symbol in self._combinedState['pricesBySymbol']) else None

    @property
    def last_quote_time(self):
        """Returns time of the last received quote.

        Returns:
            Time of the last received quote.
        """
        if self._combinedState['lastQuoteTime']:
            return {
                'time': self._combinedState['lastQuoteTime'],
                'brokerTime': self._combinedState['lastQuoteBrokerTime']
            }
        else:
            return None

    async def wait_for_price(self, symbol: str, timeout_in_seconds: float = 30):
        """Waits for price to be received.

        Args:
            symbol: Symbol (e.g. currency pair or an index).
            timeout_in_seconds: Timeout in seconds, default is 30.

        Returns:
            A coroutine resolving with price or undefined if price has not been received.
        """
        self._waitForPriceResolves[symbol] = self._waitForPriceResolves[symbol] if symbol in \
            self._waitForPriceResolves else []
        if self.price(symbol) is None:
            future = asyncio.Future()
            self._waitForPriceResolves[symbol].append(future)
            await asyncio.wait_for(future, timeout=timeout_in_seconds)

        return self.price(symbol)

    async def on_connected(self, instance_index: str, replicas: int):
        """Invoked when connection to MetaTrader terminal established.

        Args:
            instance_index: Index of an account instance connected.
            replicas: Number of account replicas launched.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        self._get_state(instance_index)['connected'] = True

    async def on_disconnected(self, instance_index: str):
        """Invoked when connection to MetaTrader terminal terminated.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
             A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        state['connected'] = False
        state['connectedToBroker'] = False

    async def on_broker_connection_status_changed(self, instance_index: str, connected: bool):
        """Invoked when broker connection status have changed.

        Args:
            instance_index: Index of an account instance connected.
            connected: Is MetaTrader terminal is connected to broker.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        self._get_state(instance_index)['connectedToBroker'] = connected

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
        unsynchronized_states = list(filter(
            lambda state_index: not self._stateByInstanceIndex[state_index]['ordersInitialized'],
            self._get_state_indices_of_same_instance_number(instance_index)))
        unsynchronized_states = sorted(unsynchronized_states,
                                       key=lambda key: itemgetter('lastSyncUpdateTime')(
                                           self._stateByInstanceIndex[key]),
                                       reverse=True)
        for state_index in unsynchronized_states[1:]:
            if state_index in self._stateByInstanceIndex:
                del self._stateByInstanceIndex[state_index]

        state = self._get_state(instance_index)
        state['lastSyncUpdateTime'] = datetime.now().timestamp()
        state['accountInformation'] = None
        state['pricesBySymbol'] = {}
        if positions_updated:
            state['positions'] = []
            state['removedPositions'] = {}
            state['positionsInitialized'] = False
            state['positionsHash'] = None
        if orders_updated:
            state['orders'] = []
            state['completedOrders'] = {}
            state['ordersInitialized'] = False
            state['ordersHash'] = None
        if specifications_updated:
            self._logger.debug(f'{self._accountId}:{instance_index}:{synchronization_id}: cleared specifications ' +
                               'on synchronization start')
            state['specificationsBySymbol'] = {}
            state['specificationsHash'] = None
        else:
            self._logger.debug(
                f'{self._accountId}:${instance_index}:${synchronization_id}: no need to clear ' +
                'specifications on synchronization start, '
                f'{len(state["specificationsBySymbol"].keys()) if state["specificationsBySymbol"] else 0} ' +
                'specifications reused')

    async def on_account_information_updated(self, instance_index: str,
                                             account_information: MetatraderAccountInformation):
        """Invoked when MetaTrader position is updated.

        Args:
            instance_index: Index of an account instance connected.
            account_information: Updated MetaTrader position.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        state['accountInformation'] = account_information
        if account_information:
            self._combinedState['accountInformation'] = copy(account_information)

    async def on_positions_replaced(self, instance_index: str, positions: List[MetatraderPosition]):
        """Invoked when the positions are replaced as a result of initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            positions: Updated array of positions.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        state['positions'] = positions
        state['positionsHash'] = None

    async def on_positions_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when position synchronization finished to indicate progress of an initial terminal state
        synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.
        """
        state = self._get_state(instance_index)
        state['removedPositions'] = {}
        state['positionsInitialized'] = True

    async def on_position_updated(self, instance_index: str, position: MetatraderPosition):
        """Invoked when MetaTrader position is updated.

        Args:
            instance_index: Index of an account instance connected.
            position: Updated MetaTrader position.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance_state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        instance_state['positionsHash'] = None

        def update_position(state):
            is_exists = False
            for i in range(len(state['positions'])):
                if state['positions'][i]['id'] == position['id']:
                    state['positions'][i] = position
                    is_exists = True
                    break
            if (not is_exists) and (position['id'] not in state['removedPositions']):
                state['positions'].append(position)
        update_position(instance_state)
        update_position(self._combinedState)

    async def on_position_removed(self, instance_index: str, position_id: str):
        """Invoked when MetaTrader position is removed.

        Args:
            instance_index: Index of an account instance connected.
            position_id: Removed MetaTrader position id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance_state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        instance_state['positionsHash'] = None

        def remove_position(state):
            position = next((p for p in state['positions'] if p['id'] == position_id), None)
            if position is None:
                for key in list(state['removedPositions'].keys()):
                    e = state['removedPositions'][key]
                    if e + 5 * 60 < datetime.now().timestamp():
                        del state['removedPositions'][key]
                state['removedPositions'][position_id] = datetime.now().timestamp()
            else:
                state['positions'] = list(filter(lambda p: p['id'] != position_id, state['positions']))
        remove_position(instance_state)
        remove_position(self._combinedState)

    async def on_pending_orders_replaced(self, instance_index: str, orders: List[MetatraderOrder]):
        """Invoked when the pending orders are replaced as a result of initial terminal state synchronization.
        This method will be invoked only if server thinks the data was updated, otherwise invocation can be skipped.

        Args:
            instance_index: Index of an account instance connected.
            orders: Updated array of pending orders.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        state['ordersHash'] = None
        state['orders'] = orders

    async def on_pending_orders_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when pending order synchronization finished to indicate progress of an initial terminal state
        synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        state = self._get_state(instance_index)
        state['completedOrders'] = {}
        state['positionsInitialized'] = True
        state['ordersInitialized'] = True
        self._combinedState['accountInformation'] = copy(state['accountInformation']) if state['accountInformation'] \
            else None

        self._combinedState['positions'] = state['positions'] or []
        for i in range(len(self._combinedState['positions'])):
            self._combinedState['positions'][i] = copy(self._combinedState['positions'][i])

        self._combinedState['orders'] = state['orders'] or []
        for i in range(len(self._combinedState['orders'])):
            self._combinedState['orders'][i] = copy(self._combinedState['orders'][i])

        self._combinedState['specificationsBySymbol'] = copy(state['specificationsBySymbol'])

        self._logger.debug(f'{self._accountId}:${instance_index}:${synchronization_id}: assigned specifications to ' +
                           f'combined state from {instance_index}, ' +
                           f'{len(state["specificationsBySymbol"].keys()) if state["specificationsBySymbol"] else 0}' +
                           'specifications assigned')
        self._combinedState['pricesBySymbol'] = state['pricesBySymbol']
        self._combinedState['positionsInitialized'] = True
        self._combinedState['ordersInitialized'] = True
        self._combinedState['completedOrders'] = {}
        self._combinedState['removedPositions'] = {}
        for state_index in self._get_state_indices_of_same_instance_number(instance_index):
            if not self._stateByInstanceIndex[state_index]['connected']:
                del self._stateByInstanceIndex[state_index]

    async def on_pending_order_updated(self, instance_index: str, order: MetatraderOrder):
        """Invoked when MetaTrader pending order is updated.

        Args:
            instance_index: Index of an account instance connected.
            order: Updated MetaTrader pending order.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance_state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        instance_state['ordersHash'] = None

        def update_pending_order(state):
            is_exists = False
            for i in range(len(state['orders'])):
                if state['orders'][i]['id'] == order['id']:
                    state['orders'][i] = order
                    is_exists = True
                    break
            if (not is_exists) and (order['id'] not in state['completedOrders']):
                state['orders'].append(order)

        update_pending_order(instance_state)
        update_pending_order(self._combinedState)

    async def on_pending_order_completed(self, instance_index: str, order_id: str):
        """Invoked when MetaTrader pending order is completed (executed or canceled).

        Args:
            instance_index: Index of an account instance connected.
            order_id: Completed MetaTrader order id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance_state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        instance_state['ordersHash'] = None

        def complete_order(state):
            order = next((p for p in state['orders'] if p['id'] == order_id), None)
            if order is None:
                for key in list(state['completedOrders'].keys()):
                    e = state['completedOrders'][key]
                    if e + 5 * 60 < datetime.now().timestamp():
                        del state['completedOrders'][key]
                state['completedOrders'][order_id] = datetime.now().timestamp()
            else:
                state['orders'] = list(filter(lambda o: o['id'] != order_id, state['orders']))
        complete_order(instance_state)
        complete_order(self._combinedState)

    async def on_symbol_specifications_updated(self, instance_index: str,
                                               specifications: List[MetatraderSymbolSpecification],
                                               removed_symbols: List[str]):
        """Invoked when a symbol specifications were updated.

        Args:
            instance_index: Index of an account instance connected.
            specifications: Updated MetaTrader symbol specification.
            removed_symbols: Removed symbols.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance_state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)
        instance_state['specificationsHash'] = None

        def update_specifications(state):
            for specification in specifications:
                state['specificationsBySymbol'][specification['symbol']] = specification
            for symbol in removed_symbols:
                if symbol in state['specificationsBySymbol']:
                    del state['specificationsBySymbol'][symbol]

        update_specifications(instance_state)
        update_specifications(self._combinedState)
        self._logger.debug(
            f'{self._accountId}:{instance_index}: updated {len(specifications)} specifications, ' +
            f'removed {len(removed_symbols)} specifications. There are ' +
            f'{len(instance_state["specificationsBySymbol"]) if instance_state["specificationsBySymbol"] else 0} ' +
            'specifications after update')

    async def on_symbol_prices_updated(self, instance_index: str, prices: List[MetatraderSymbolPrice],
                                       equity: float = None, margin: float = None, free_margin: float = None,
                                       margin_level: float = None, account_currency_exchange_rate: float = None):
        """Invoked when prices for several symbols were updated.

        Args:
            instance_index: Index of an account instance connected.
            prices: Updated MetaTrader symbol prices.
            equity: Account liquidation value.
            margin: Margin used.
            free_margin: Free margin.
            margin_level: Margin level calculated as % of equity/margin.
            account_currency_exchange_rate: Current exchange rate of account currency into USD.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance_state = self._get_state(instance_index)
        self._refresh_state_update_time(instance_index)

        def update_symbol_prices(state):
            state['lastUpdateTime'] = max(map(lambda p: p['time'].timestamp(), prices)) if len(prices) else 0
            prices_initialized = False
            price_updated = False
            if prices:
                for price in prices:
                    if price['symbol'] in state['pricesBySymbol']:
                        current_price = state['pricesBySymbol'][price['symbol']]
                        if current_price['time'].timestamp() > price['time'].timestamp():
                            continue
                        else:
                            price_updated = True
                    else:
                        price_updated = True

                    if not state['lastQuoteTime'] or state['lastQuoteTime'].timestamp() < price['time'].timestamp():
                        state['lastQuoteTime'] = price['time']
                        state['lastQuoteBrokerTime'] = price['brokerTime']

                    state['pricesBySymbol'][price['symbol']] = price
                    positions = list(filter(lambda p: p['symbol'] == price['symbol'], state['positions']))
                    other_positions = list(filter(lambda p: p['symbol'] != price['symbol'], state['positions']))
                    orders = list(filter(lambda o: o['symbol'] == price['symbol'], state['orders']))
                    prices_initialized = True
                    for position in other_positions:
                        if position['symbol'] in state['pricesBySymbol']:
                            p = state['pricesBySymbol'][position['symbol']]
                            if 'unrealizedProfit' not in position:
                                self._update_position_profits(position, p)
                        else:
                            prices_initialized = False
                    for position in positions:
                        self._update_position_profits(position, price)
                    for order in orders:
                        order['currentPrice'] = price['ask'] if (order['type'] == 'ORDER_TYPE_BUY' or
                                                                 order['type'] == 'ORDER_TYPE_BUY_LIMIT' or
                                                                 order['type'] == 'ORDER_TYPE_BUY_STOP' or
                                                                 order['type'] == 'ORDER_TYPE_BUY_STOP_LIMIT') else \
                            price['bid']
                    price_resolves = self._waitForPriceResolves[price['symbol']] if price['symbol'] in \
                        self._waitForPriceResolves else []
                    if len(price_resolves):
                        resolve: asyncio.Future
                        for resolve in price_resolves:
                            if not resolve.done():
                                resolve.set_result(True)
                        del self._waitForPriceResolves[price['symbol']]
            if price_updated and state['accountInformation']:
                if state['positionsInitialized'] and prices_initialized:
                    if state['accountInformation']['platform'] == 'mt5':
                        state['accountInformation']['equity'] = equity if equity is not None else \
                            state['accountInformation']['balance'] + \
                            functools.reduce(lambda a, b: a + round((b['unrealizedProfit'] if
                                                                     'unrealizedProfit' in b and
                                                                     b['unrealizedProfit'] is not None
                                                                     else 0) * 100) / 100 +
                                             round((b['swap'] if 'swap' in b and b['swap'] is not None
                                                    else 0) * 100) / 100, state['positions'], 0)
                    else:
                        state['accountInformation']['equity'] = equity if equity is not None else \
                            state['accountInformation']['balance'] + \
                            functools.reduce(
                            lambda a, b: a + round((b['swap'] if 'swap' in b and b['swap'] is not None
                                                    else 0) * 100) / 100 +
                            round((b['commission'] if 'commission' in b and b['commission'] is not None
                                   else 0) * 100) / 100 +
                            round((b['unrealizedProfit'] if 'unrealizedProfit' in b and b['unrealizedProfit'] is
                                                            not None else 0) * 100) / 100, state['positions'], 0)
                    state['accountInformation']['equity'] = round(state['accountInformation']['equity'] * 100) / 100
                else:
                    state['accountInformation']['equity'] = equity if equity else (
                        state['accountInformation']['equity'] if 'equity' in state['accountInformation'] else None)
                state['accountInformation']['margin'] = margin if margin else (
                    state['accountInformation']['margin'] if 'margin' in state['accountInformation'] else None)
                state['accountInformation']['freeMargin'] = free_margin if free_margin else (
                    state['accountInformation']['freeMargin'] if 'freeMargin' in state['accountInformation'] else None)
                state['accountInformation']['marginLevel'] = margin_level if free_margin else (
                    state['accountInformation']['marginLevel'] if 'marginLevel' in state['accountInformation'] else
                    None)
        update_symbol_prices(instance_state)
        update_symbol_prices(self._combinedState)

    async def on_stream_closed(self, instance_index: str):
        """Invoked when a stream for an instance index is closed.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        if instance_index in self._stateByInstanceIndex:
            for state_index in self._get_state_indices_of_same_instance_number(instance_index):
                instance_state = self._stateByInstanceIndex[state_index]
                if not self._stateByInstanceIndex[instance_index]['ordersInitialized'] and \
                        self._stateByInstanceIndex[instance_index]['lastSyncUpdateTime'] <= \
                        instance_state['lastSyncUpdateTime']:
                    del self._stateByInstanceIndex[instance_index]
                    break

                if instance_state['connected'] and instance_state['ordersInitialized']:
                    del self._stateByInstanceIndex[instance_index]
                    break

    def _refresh_state_update_time(self, instance_index: str):
        if instance_index in self._stateByInstanceIndex:
            state = self._stateByInstanceIndex[instance_index]
            if state['ordersInitialized']:
                state['lastSyncUpdateTime'] = datetime.now().timestamp()

    def _get_state_indices_of_same_instance_number(self, instance_index: str):
        instance_number = instance_index.split(':')[0]
        return list(filter(lambda state_instance_index: state_instance_index.startswith(f'{instance_number}:') and
                           instance_index != state_instance_index, self._stateByInstanceIndex.keys()))

    def _update_position_profits(self, position: Dict, price: Dict):
        specification = self.specification(position['symbol'])
        if specification:
            multiplier = pow(10, specification['digits'])
            if 'profit' in position:
                position['profit'] = round(position['profit'] * multiplier) / multiplier
            if 'unrealizedProfit' not in position or 'realizedProfit' not in position:
                position['unrealizedProfit'] = (1 if (position['type'] == 'POSITION_TYPE_BUY') else -1) * \
                                               (position['currentPrice'] - position['openPrice']) * \
                                               position['currentTickValue'] * position['volume'] / \
                                               specification['tickSize']
                position['unrealizedProfit'] = round(position['unrealizedProfit'] * multiplier) / multiplier
                position['realizedProfit'] = position['profit'] - position['unrealizedProfit']
            new_position_price = price['bid'] if (position['type'] == 'POSITION_TYPE_BUY') else price['ask']
            is_profitable = (1 if (position['type'] == 'POSITION_TYPE_BUY') else -1) * (new_position_price -
                                                                                        position['openPrice'])
            current_tick_value = price['profitTickValue'] if (is_profitable > 0) else price['lossTickValue']
            unrealized_profit = (1 if (position['type'] == 'POSITION_TYPE_BUY') else -1) * \
                                (new_position_price - position['openPrice']) * current_tick_value * \
                position['volume'] / specification['tickSize']
            unrealized_profit = round(unrealized_profit * multiplier) / multiplier
            position['unrealizedProfit'] = unrealized_profit
            position['profit'] = position['unrealizedProfit'] + position['realizedProfit']
            position['profit'] = round(position['profit'] * multiplier) / multiplier
            position['currentPrice'] = new_position_price
            position['currentTickValue'] = current_tick_value

    def _get_state(self, instance_index: str) -> TerminalStateDict:
        if str(instance_index) not in self._stateByInstanceIndex:
            self._logger.debug(f'{self._accountId}:{instance_index}: constructed new state')
            self._stateByInstanceIndex[str(instance_index)] = self._construct_terminal_state(instance_index)
        return self._stateByInstanceIndex[str(instance_index)]

    def _construct_terminal_state(self, instance_index: str = None) -> TerminalStateDict:
        return {
            'instanceIndex': instance_index,
            'connected': False,
            'connectedToBroker': False,
            'accountInformation': None,
            'positions': [],
            'orders': [],
            'specificationsBySymbol': {},
            'pricesBySymbol': {},
            'completedOrders': {},
            'removedPositions': {},
            'ordersInitialized': False,
            'positionsInitialized': False,
            'lastUpdateTime': 0,
            'lastSyncUpdateTime': 0,
            'positionsHash': None,
            'ordersHash': None,
            'specificationsHash': None,
            'lastQuoteTime': None,
            'lastQuoteBrokerTime': None
        }

    def _get_hash(self, obj, account_type: str):
        json_item = ''
        if account_type == 'cloud-g1':
            json_item = json.dumps(obj, cls=G1Encoder, ensure_ascii=False)
        elif account_type == 'cloud-g2':
            json_item = json.dumps(obj, cls=G2Encoder, ensure_ascii=False)
        json_item = json_item.encode('utf8')
        return md5(json_item).hexdigest()
