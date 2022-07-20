from .models import MetatraderDeal, MetatraderOrder
from typing import List
from .memoryHistoryStorageModel import MemoryHistoryStorageModel
from .filesystemHistoryDatabase import FilesystemHistoryDatabase
from datetime import datetime
from .models import date, format_date, string_format_error
from ..logger import LoggerManager
from .historyItemsMemoryStorage import HistoryItemsMemoryStorage
from copy import copy
import asyncio


class MemoryHistoryStorage(MemoryHistoryStorageModel):
    """History storage which stores MetaTrader history in RAM."""

    def __init__(self):
        """Inits the in-memory history store instance"""
        super().__init__()
        self._historyDatabase = FilesystemHistoryDatabase.get_instance()
        self._maxHistoryOrderTime = None
        self._maxDealTime = None
        self._flushPromise = None
        self._flushRunning = None
        self._flushTimeout = None
        self._reset()
        self._logger = LoggerManager.get_logger('MemoryHistoryStorage')

    async def initialize(self, account_id: str, application: str = 'MetaApi'):
        """Initializes the storage and loads required data from a persistent storage."""
        await super(MemoryHistoryStorage, self).initialize(account_id, application)
        history = await self._historyDatabase.load_history(account_id, application)

        for deal in history['deals']:
            await self._add_deal(deal, True)

        for history_order in history['historyOrders']:
            await self._add_history_order(history_order, True)

    async def clear(self):
        """Clears the storage and deletes persistent data."""
        self._reset()
        await self._historyDatabase.clear(self._accountId, self._application)

    async def last_history_order_time(self, instance_number: int = None) -> datetime:
        """Returns the time of the last history order record stored in the history storage.

        Args:
            instance_number: Index of an account instance connected.

        Returns:
            The time of the last history order record stored in the history storage.
        """
        return self._maxHistoryOrderTime

    async def last_deal_time(self, instance_number: int = None) -> datetime:
        """Returns the time of the last history deal record stored in the history storage.

        Args:
            instance_number: Index of an account instance connected.

        Returns:
            The time of the last history deal record stored in the history storage.
        """
        return self._maxDealTime

    async def on_history_order_added(self, instance_index: str, history_order: MetatraderOrder):
        """Invoked when a new MetaTrader history order is added.

        Args:
            instance_index: Index of an account instance connected.
            history_order: New MetaTrader history order.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        await self._add_history_order(history_order)

    async def on_deal_added(self, instance_index: str, deal: MetatraderDeal):
        """Invoked when a new MetaTrader history deal is added.

        Args:
            instance_index: Index of an account instance connected.
            deal: New MetaTrader history deal.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        await self._add_deal(deal)

    @property
    def deals(self) -> List[MetatraderDeal]:
        """Returns all deals stored in history storage.

        Returns:
            All deals stored in history storage.
        """
        return self.get_deals_by_time_range(date(0), date(8640000000))

    def get_deals_by_ticket(self, id: str) -> List[MetatraderDeal]:
        """Returns deals by ticket id.

        Args:
            id: Ticket id.

        Returns:
            Deals found.
        """
        deals = self._dealsByTicket[id].values() if id in self._dealsByTicket else []
        return sorted(deals, key=self._dealsComparator)

    def get_deals_by_position(self, position_id: str) -> List[MetatraderDeal]:
        """Returns deals by position id.

        Args:
            position_id: Position id.

        Returns:
            Deals found.
        """
        deals = self._dealsByPosition[position_id].values() if position_id in self._dealsByPosition else []
        return sorted(deals, key=self._dealsComparator)

    def get_deals_by_time_range(self, start_time: datetime, end_time: datetime) -> List[MetatraderDeal]:
        """Returns deals by time range.

        Args:
            start_time: Start time, inclusive.
            end_time: End time, inclusive.

        Returns:
            Deals found.
        """
        return self._dealsByTime.between_bounds({'time': start_time}, {'time': end_time})

    @property
    def history_orders(self) -> List[MetatraderOrder]:
        """Returns all history orders stored in history storage.

        Returns:
            All history orders stored in history storage.
        """
        return self.get_history_orders_by_time_range(date(0), date(8640000000))

    def get_history_orders_by_ticket(self, id: str) -> List[MetatraderOrder]:
        """Returns history orders by ticket id.

        Args:
            id: Ticket id.

        Returns:
            History orders found.
        """
        history_orders = self._historyOrdersByTicket[id].values() if id in self._historyOrdersByTicket else []
        return sorted(history_orders, key=self._historyOrdersComparator)

    def get_history_orders_by_position(self, position_id: str) -> List[MetatraderOrder]:
        """Returns history orders by position id.

        Args:
            position_id: Position id.

        Returns:
            History orders found.
        """
        history_orders = self._historyOrdersByPosition[position_id].values() if position_id in \
            self._historyOrdersByPosition else []
        return sorted(history_orders, key=self._historyOrdersComparator)

    def get_history_orders_by_time_range(self, start_time: datetime, end_time: datetime) -> List[MetatraderOrder]:
        """Returns history orders by time range.

        Args:
            start_time: Start time, inclusive.
            end_time: End time, inclusive.

        Returns:
            History orders found.
        """
        return self._historyOrdersByTime.between_bounds({'doneTime': start_time}, {'doneTime': end_time})

    async def on_deals_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when a synchronization of history deals on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        await self._flush_database()
        await super().on_deals_synchronized(instance_index, synchronization_id)

    def _reset(self):
        self._orderSynchronizationFinished = {}
        self._dealSynchronizationFinished = {}
        self._dealsByTicket = {}
        self._dealsByPosition = {}
        self._historyOrdersByTicket = {}
        self._historyOrdersByPosition = {}

        def history_orders_comparator(o):
            return o['doneTime'].timestamp() if 'doneTime' in o else 0, int(o['id']), o['type'], o['state']

        self._historyOrdersComparator = history_orders_comparator
        self._historyOrdersByTime = HistoryItemsMemoryStorage(self._historyOrdersComparator)

        def deals_comparator(d):
            return d['time'].timestamp() if 'time' in d else 0, int(d['id']), d['entryType'] if 'entryType' in d else ''

        self._dealsComparator = deals_comparator
        self._dealsByTime = HistoryItemsMemoryStorage(self._dealsComparator)
        self._maxHistoryOrderTime = date(0)
        self._maxDealTime = date(0)
        self._newHistoryOrders = []
        self._newDeals = []
        if self._flushTimeout is not None:
            self._flushTimeout.cancel()
        self._flushTimeout = None

    async def _add_deal(self, deal, existing=False):
        key = self._get_deal_key(deal)
        self._dealsByTicket[deal['id']] = self._dealsByTicket[deal['id']] if deal['id'] in self._dealsByTicket \
            else {}
        new_deal = not existing and key not in self._dealsByTicket[deal['id']]
        self._dealsByTicket[deal['id']][key] = deal
        if 'positionId' in deal:
            self._dealsByPosition[deal['positionId']] = self._dealsByPosition[deal['positionId']] if \
                deal['positionId'] in self._dealsByPosition else {}
            self._dealsByPosition[deal['positionId']][key] = deal

        self._dealsByTime.delete(deal)
        self._dealsByTime.insert(deal, deal)
        if 'time' in deal and (self._maxDealTime is None or self._maxDealTime.timestamp() < deal['time'].timestamp()):
            self._maxDealTime = deal['time']

        if new_deal:
            self._newDeals.append(deal)
            if self._flushTimeout is not None:
                self._flushTimeout.cancel()
            self._flushTimeout = asyncio.create_task(self._flush_database_job(5))

    def _get_deal_key(self, deal):
        return format_date(deal['time'] or datetime.utcfromtimestamp(0)) + ':' + deal['id'] + ':' + (
            deal['entryType'] if 'entryType' in deal else '')

    async def _add_history_order(self, history_order, existing=False):
        key = self._get_history_order_key(history_order)
        self._historyOrdersByTicket[history_order['id']] = self._historyOrdersByTicket[history_order['id']] if \
            history_order['id'] in self._historyOrdersByTicket else {}
        new_history_order = not existing and key not in self._historyOrdersByTicket[history_order['id']]
        self._historyOrdersByTicket[history_order['id']][key] = history_order
        if 'positionId' in history_order:
            self._historyOrdersByPosition[history_order['positionId']] = \
                self._historyOrdersByPosition[history_order['positionId']] if history_order['positionId'] in \
                self._historyOrdersByPosition else {}
            self._historyOrdersByPosition[history_order['positionId']][key] = history_order

        self._historyOrdersByTime.delete(history_order)
        self._historyOrdersByTime.insert(history_order, history_order)
        if 'doneTime' in history_order and (self._maxHistoryOrderTime is None or
                                            self._maxHistoryOrderTime.timestamp() <
                                            history_order['doneTime'].timestamp()):
            self._maxHistoryOrderTime = history_order['doneTime']

        if new_history_order:
            self._newHistoryOrders.append(history_order)
            if self._flushTimeout is not None:
                self._flushTimeout.cancel()
            self._flushTimeout = asyncio.create_task(self._flush_database_job(5))

    def _get_history_order_key(self, history_order):
        return format_date(history_order['doneTime'] if 'doneTime' in history_order else date(0))\
            + ':' + history_order['id'] + ':' + history_order['type'] + ':' + history_order['state']

    async def _flush_database(self):
        if self._flushPromise:
            await self._flushPromise
        if self._flushRunning:
            return
        self._flushRunning = True
        self._flushPromise = asyncio.Future()

        try:
            for i in range(len(self._newHistoryOrders)):
                history_order = copy(self._newHistoryOrders[i])
                history_order['time'] = format_date(history_order['time'])
                if 'doneTime' in history_order:
                    history_order['doneTime'] = format_date(history_order['doneTime'])
                self._newHistoryOrders[i] = history_order
            for i in range(len(self._newDeals)):
                deal = copy(self._newDeals[i])
                deal['time'] = format_date(deal['time'])
                self._newDeals[i] = deal
            await self._historyDatabase.flush(self._accountId, self._application, self._newHistoryOrders,
                                              self._newDeals)
            self._newHistoryOrders = []
            self._newDeals = []
            self._logger.debug(f'{self._accountId}: flushed history db')
        except Exception as err:
            self._logger.warn(f'{self._accountId}: error flushing history db ' + string_format_error(err))
            self._flushTimeout = asyncio.create_task(self._flush_database_job(15))
        finally:
            self._flushPromise.set_result(True)
            self._flushPromise = None
            self._flushRunning = False

    async def _flush_database_job(self, time: float):
        await asyncio.sleep(time)
        await self._flush_database()
