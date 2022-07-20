from ...metaApi.models import MetatraderPosition, MetatraderAccountInformation, MetatraderOrder, \
    MetatraderDeal, MetatraderSymbolSpecification, MetatraderSymbolPrice, MetatraderCandle, MetatraderTick,\
    MetatraderBook, MarketDataSubscription, MarketDataUnsubscription
from abc import ABC
from typing import List, Optional
from typing_extensions import TypedDict


class HealthStatus(TypedDict, total=False):
    """Server-side application health status."""
    restApiHealthy: Optional[bool]
    """Flag indicating that REST API is healthy."""
    copyFactorySubscriberHealthy: Optional[bool]
    """Flag indicating that CopyFactory subscriber is healthy."""
    copyFactoryProviderHealthy: Optional[bool]
    """Flag indicating that CopyFactory provider is healthy."""


class SynchronizationListener(ABC):
    """Defines interface for a synchronization listener class."""

    def get_instance_number(self, instance_index: str = None) -> int:
        """Returns instance number of instance index.

        Args:
            instance_index: Instance index
        """
        return int(instance_index.split(':')[0]) if isinstance(instance_index, str) else None

    def get_host_name(self, instance_index: str = None) -> str:
        """Returns host name of instance index.

        Args:
            instance_index:
        """
        return instance_index.split(':')[1] if isinstance(instance_index, str) else None

    async def on_connected(self, instance_index: str, replicas: int):
        """Invoked when connection to MetaTrader terminal established.

        Args:
            instance_index: Index of an account instance connected.
            replicas: Number of account replicas launched.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_health_status(self, instance_index: str, status: HealthStatus):
        """Invoked when a server-side application health status is received from MetaApi.

        Args:
            instance_index: Index of an account instance connected.
            status: Server-side application health status.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_disconnected(self, instance_index: str):
        """Invoked when connection to MetaTrader terminal terminated.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
             A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_broker_connection_status_changed(self, instance_index: str, connected: bool):
        """Invoked when broker connection status have changed.

        Args:
            instance_index: Index of an account instance connected.
            connected: Is MetaTrader terminal is connected to broker.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

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
        pass

    async def on_account_information_updated(self, instance_index: str,
                                             account_information: MetatraderAccountInformation):
        """Invoked when MetaTrader position is updated.

        Args:
            instance_index: Index of an account instance connected.
            account_information: Updated MetaTrader position.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_positions_replaced(self, instance_index: str, positions: List[MetatraderPosition]):
        """Invoked when the positions are replaced as a result of initial terminal state synchronization. This method
        will be invoked only if server thinks the data was updated, otherwise invocation can be skipped.

        Args:
            instance_index: Index of an account instance connected.
            positions: Updated array of positions.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_positions_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when position synchronization finished to indicate progress of an initial terminal state
        synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.
        """
        pass

    async def on_position_updated(self, instance_index: str, position: MetatraderPosition):
        """Invoked when MetaTrader position is updated.

        Args:
            instance_index: Index of an account instance connected.
            position: Updated MetaTrader position.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_position_removed(self, instance_index: str, position_id: str):
        """Invoked when MetaTrader position is removed.

        Args:
            instance_index: Index of an account instance connected.
            position_id: Removed MetaTrader position id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_pending_orders_replaced(self, instance_index: str, orders: List[MetatraderOrder]):
        """Invoked when the pending orders are replaced as a result of initial terminal state synchronization.
        This method will be invoked only if server thinks the data was updated, otherwise invocation can be skipped.

        Args:
            instance_index: Index of an account instance connected.
            orders: Updated array of pending orders.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_pending_order_updated(self, instance_index: str, order: MetatraderOrder):
        """Invoked when MetaTrader pending order is updated.

        Args:
            instance_index: Index of an account instance connected.
            order: Updated MetaTrader pending order.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_pending_order_completed(self, instance_index: str, order_id: str):
        """Invoked when MetaTrader pending order is completed (executed or canceled).

        Args:
            instance_index: Index of an account instance connected.
            order_id: Completed MetaTrader order id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_pending_orders_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when pending order synchronization finished to indicate progress of an initial terminal state
        synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_history_order_added(self, instance_index: str, history_order: MetatraderOrder):
        """Invoked when a new MetaTrader history order is added.

        Args:
            instance_index: Index of an account instance connected.
            history_order: New MetaTrader history order.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_history_orders_synchronized(self, instance_index: str, synchronization_id: str):
        """Invoked when a synchronization of history orders on a MetaTrader account have finished to indicate progress
        of an initial terminal state synchronization.

        Args:
            instance_index: Index of an account instance connected.
            synchronization_id: Synchronization request id.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

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
        pass

    async def on_symbol_specification_updated(self, instance_index: str, specification: MetatraderSymbolSpecification):
        """Invoked when a symbol specification was updated

        Args:
            instance_index: Index of an account instance connected.
            specification: Updated MetaTrader symbol specification.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_symbol_specification_removed(self, instance_index: str, symbol: str):
        """Invoked when a symbol specification was removed.

        Args:
            instance_index: Index of an account instance connected.
            symbol: Removed symbol.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

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
        pass

    async def on_symbol_price_updated(self, instance_index: str, price: MetatraderSymbolPrice):
        """Invoked when a symbol price was updated.

        Args:
            instance_index: Index of an account instance connected.
            price: Updated MetaTrader symbol price.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

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
        pass

    async def on_candles_updated(self, instance_index: str, candles: List[MetatraderCandle], equity: float = None,
                                 margin: float = None, free_margin: float = None, margin_level: float = None,
                                 account_currency_exchange_rate: float = None):
        """Invoked when symbol candles were updated.

        Args:
            instance_index: Index of an account instance connected.
            candles: Updated MetaTrader symbol candles.
            equity: Account liquidation value.
            margin: Margin used.
            free_margin: Free margin.
            margin_level: Margin level calculated as % of equity/margin.
            account_currency_exchange_rate: Current exchange rate of account currency into USD.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_ticks_updated(self, instance_index: str, ticks: List[MetatraderTick], equity: float = None,
                               margin: float = None, free_margin: float = None, margin_level: float = None,
                               account_currency_exchange_rate: float = None):
        """Invoked when symbol candles were updated.

        Args:
            instance_index: Index of an account instance connected.
            ticks: Updated MetaTrader symbol ticks.
            equity: Account liquidation value.
            margin: Margin used.
            free_margin: Free margin.
            margin_level: Margin level calculated as % of equity/margin.
            account_currency_exchange_rate: Current exchange rate of account currency into USD.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

    async def on_books_updated(self, instance_index: str, books: List[MetatraderBook], equity: float = None,
                               margin: float = None, free_margin: float = None, margin_level: float = None,
                               account_currency_exchange_rate: float = None):
        """Invoked when symbol candles were updated.

        Args:
            instance_index: Index of an account instance connected.
            books: Updated MetaTrader order books.
            equity: Account liquidation value.
            margin: Margin used.
            free_margin: Free margin.
            margin_level: Margin level calculated as % of equity/margin.
            account_currency_exchange_rate: Current exchange rate of account currency into USD.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass

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
        pass

    async def on_stream_closed(self, instance_index: str):
        """Invoked when a stream for an instance index is closed.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass
