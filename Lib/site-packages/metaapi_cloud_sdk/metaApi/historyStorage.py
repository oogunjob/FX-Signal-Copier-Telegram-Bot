from ..clients.metaApi.synchronizationListener import SynchronizationListener
from .models import MetatraderOrder, MetatraderDeal
from datetime import datetime
from abc import abstractmethod, ABC
from typing import List


class HistoryStorage(SynchronizationListener, ABC):
    """ Abstract class which defines MetaTrader history storage interface."""

    def __init__(self):
        """Inits the history storage"""
        super().__init__()
        self._orderSynchronizationFinished = {}
        self._dealSynchronizationFinished = {}
        self._accountId = None
        self._application = None

    async def initialize(self, account_id: str, application: str):
        """Initializes the storage and loads required data from a persistent storage.

        Args:
            account_id: Account id.
            application: Application.

        Returns:
            A coroutine resolving when history storage is initialized.
        """
        self._accountId = account_id
        self._application = application

    @property
    def order_synchronization_finished(self) -> bool:
        """Returns flag indicating whether order history synchronization has finished.

        Returns:
            A flag indicating whether order history synchronization has finished.
        """
        return True in list(self._orderSynchronizationFinished.values())

    @property
    def deal_synchronization_finished(self) -> bool:
        """Returns flag indicating whether deal history synchronization has finished.

        Returns:
            A flag indicating whether order history synchronization has finished.
        """
        return True in list(self._dealSynchronizationFinished.values())

    @abstractmethod
    async def clear(self):
        """Clears the storage and deletes persistent data.

        Returns:
            A coroutine resolving when history storage is cleared
        """
        pass

    @abstractmethod
    async def last_history_order_time(self, instance_index: str = None) -> datetime:
        """Returns the time of the last history order record stored in the history storage.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
            The time of the last history order record stored in the history storage.
        """
        pass

    @abstractmethod
    async def last_deal_time(self, instance_index: str = None) -> datetime:
        """Returns the time of the last history deal record stored in the history storage.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
            The time of the last history deal record stored in the history storage.
        """
        pass

    @abstractmethod
    async def on_history_order_added(self, instance_index: str, history_order: MetatraderOrder):
        """Invoked when a new MetaTrader history order is added.

        Args:
            instance_index: Index of an account instance connected.
            history_order: New MetaTrader history order.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    @abstractmethod
    async def on_deal_added(self, instance_index: str, deal: MetatraderDeal):
        """Invoked when a new MetaTrader history deal is added.

        Args:
            instance_index: Index of an account instance connected.
            deal: New MetaTrader history deal.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_deals_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when a synchronization of history deals on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance = str(self.get_instance_number(instance_index))
        self._dealSynchronizationFinished[instance] = True

    async def on_history_orders_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when a synchronization of history orders on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance = str(self.get_instance_number(instance_index))
        self._orderSynchronizationFinished[instance] = True

    async def on_connected(self, instance_index: str, replicas: int):
        """Invoked when connection to MetaTrader terminal established.

        Args:
            instance_index: Index of an account instance connected.
            replicas: Number of account replicas launched.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        instance = str(self.get_instance_number(instance_index))
        self._orderSynchronizationFinished[instance] = False
        self._dealSynchronizationFinished[instance] = False

    @property
    @abstractmethod
    def deals(self) -> List[MetatraderDeal]:
        """Returns all deals.

        Returns:
            All deals.
        """
        pass

    @abstractmethod
    def get_deals_by_ticket(self, id: str) -> List[MetatraderDeal]:
        """Returns deals by ticket id.

        Args:
            id: Ticket id.

        Returns:
            Deals found.
        """
        pass

    @abstractmethod
    def get_deals_by_position(self, position_id: str) -> List[MetatraderDeal]:
        """Returns deals by position id.

        Args:
            position_id: Position id.

        Returns:
            Deals found.
        """
        pass

    @abstractmethod
    def get_deals_by_time_range(self, start_time: datetime, end_time: datetime) -> List[MetatraderDeal]:
        """Returns deals by time range.

        Args:
            start_time: Start time, inclusive.
            end_time: End time, inclusive.

        Returns:
            Deals found.
        """
        pass

    @property
    @abstractmethod
    def history_orders(self):
        """Returns all history orders.

        Returns:
            All history orders.
        """
        pass

    @abstractmethod
    def get_history_orders_by_ticket(self, id: str) -> List[MetatraderOrder]:
        """Returns history orders by ticket id.

        Args:
            id: Ticket id.

        Returns:
            History orders found.
        """
        pass

    @abstractmethod
    def get_history_orders_by_position(self, position_id: str) -> List[MetatraderOrder]:
        """Returns history orders by position id.

        Args:
            position_id: Position id.

        Returns:
            History orders found.
        """
        pass

    @abstractmethod
    def get_history_orders_by_time_range(self, start_time: datetime, end_time: datetime) -> List[MetatraderOrder]:
        """Returns history orders by time range.

        Args:
            start_time: Start time, inclusive.
            end_time: End time, inclusive.

        Returns:
            History orders found.
        """
        pass
