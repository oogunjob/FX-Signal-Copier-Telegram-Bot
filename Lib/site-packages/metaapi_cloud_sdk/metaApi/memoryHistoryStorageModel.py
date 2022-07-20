from .historyStorage import HistoryStorage
from .models import MetatraderDeal, MetatraderOrder
from typing import List
from abc import abstractmethod
from datetime import datetime


class MemoryHistoryStorageModel(HistoryStorage):
    """Abstract class which defines MetaTrader memory history storage interface."""

    async def initialize(self, account_id: str, application: str):
        """Initializes the storage and loads required data from a persistent storage."""
        await super(MemoryHistoryStorageModel, self).initialize(account_id, application)

    @abstractmethod
    async def clear(self):
        """Clears the storage and deletes persistent data."""
        pass

    @abstractmethod
    async def last_history_order_time(self, instance_number: int = None) -> datetime:
        """Returns the time of the last history order record stored in the history storage.

        Args:
            instance_number: Index of an account instance connected.

        Returns:
            The time of the last history order record stored in the history storage.
        """
        pass

    @abstractmethod
    async def last_deal_time(self, instance_number: int = None) -> datetime:
        """Returns the time of the last history deal record stored in the history storage.

        Args:
            instance_number: Index of an account instance connected.

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

    @abstractmethod
    def deals(self) -> List[MetatraderDeal]:
        """Returns all deals stored in history storage.

        Returns:
            All deals stored in history storage.
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
    def history_orders(self) -> List[MetatraderOrder]:
        """Returns all history orders stored in history storage.

        Returns:
            All history orders stored in history storage.
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

    @abstractmethod
    async def on_deals_synchronized(self, instance_index, synchronization_id):
        """Invoked when a synchronization of history deals on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        await super().on_deals_synchronized(instance_index, synchronization_id)
