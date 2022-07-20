from typing_extensions import TypedDict
from datetime import datetime


class ResponseTimestamps(TypedDict):
    """Object containing request latency information."""
    clientProcessingStarted: datetime
    """Time when request processing has started on client side."""
    serverProcessingStarted: datetime
    """Time when request processing has started on server side."""
    serverProcessingFinished: datetime
    """Time when request processing has finished on server side."""
    clientProcessingFinished: datetime
    """Time when request processing has finished on client side."""


class SymbolPriceTimestamps(TypedDict):
    """Object containing request latency information."""
    eventGenerated: datetime
    """Time the event was generated on exchange side."""
    serverProcessingStarted: datetime
    """Time when request processing has started on server side."""
    serverProcessingFinished: datetime
    """Time when request processing has finished on server side."""
    clientProcessingFinished: datetime
    """Time when request processing has finished on client side."""


class UpdateTimestamps(TypedDict):
    """Timestamps object containing latency information about update streaming."""
    eventGenerated: datetime
    """Time the event was generated on exchange side."""
    serverProcessingStarted: datetime
    """Time when request processing has started on server side."""
    serverProcessingFinished: datetime
    """Time when request processing has finished on server side."""
    clientProcessingFinished: datetime
    """Time when request processing has finished on client side."""


class TradeTimestamps(TypedDict):
    """Timestamps object containing latency information about update streaming."""
    clientProcessingStarted: datetime
    """Time when request processing has started on client side."""
    serverProcessingStarted: datetime
    """Time when request processing has started on server side."""
    serverProcessingFinished: datetime
    """Time when request processing has finished on server side."""
    clientProcessingFinished: datetime
    """Time when request processing has finished on client side."""
    tradeStarted: datetime
    """Time the trade execution was started on server side."""
    tradeExecuted: datetime
    """Time the trade was executed on exchange side."""


class LatencyListener:
    async def on_response(self, account_id: str, type: str, timestamps: ResponseTimestamps):
        """Invoked with latency information when application receives a response to RPC request.

        Args:
            account_id: Account id.
            type: Request type.
            timestamps: Request timestamps object containing latency information.

        Returns:
            A coroutine which resolves when latency information is processed."""
        pass

    async def on_symbol_price(self, account_id: str, symbol: str, timestamps: SymbolPriceTimestamps):
        """Invoked with latency information when application receives symbol price update event.

        Args:
            account_id: Account id.
            symbol: Price symbol.
            timestamps: Timestamps object containing latency information about price streaming.

        Returns:
            A coroutine which resolves when latency information is processed.
        """
        pass

    async def on_update(self, account_id: str, timestamps: UpdateTimestamps):
        """Invoked with latency information when application receives update event.

        Args:
            account_id: Account id.
            timestamps: Timestamps object containing latency information about update streaming.

        Returns:
            A coroutine which resolves when latency information is processed."""
        pass

    async def on_trade(self, account_id: str, timestamps: TradeTimestamps):
        """Invoked with latency information when application receives trade response.

        Args:
            account_id: Account id.
            timestamps: Timestamps object containing latency information about a trade.

        Returns:
            A coroutine which resolves when latency information is processed."""
        pass
