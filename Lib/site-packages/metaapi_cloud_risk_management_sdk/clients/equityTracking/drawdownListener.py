from abc import abstractmethod


class DrawdownListener:
    """Drawdown listener for handling a stream of drawdown events."""

    @abstractmethod
    async def on_drawdown(self, drawdown_event):
        """Processes drawdown event which occurs when a drawdown limit is exceeded in a drawdown tracker.

        Args:
            drawdown_event: Drawdown event.
        """
        pass
