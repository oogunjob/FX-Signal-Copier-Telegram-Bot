from abc import ABC, abstractmethod


class ReconnectListener(ABC):
    """Defines interface for a websocket reconnect listener class."""

    @abstractmethod
    async def on_reconnected(self):
        """Invoked when connection to MetaTrader terminal re-established.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        pass
